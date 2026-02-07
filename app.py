from __future__ import annotations

import base64
import calendar
import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional

from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    request,
    session,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SCHEDULE_DIR = os.path.join(DATA_DIR, "schedules")
PASSWORD_ITERATIONS = 260000
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{4,20}$")
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")
ALLOWED_FREQUENCIES = {"none", "daily", "weekly", "monthly", "yearly"}
ALLOWED_END_TYPES = {"never", "until", "count"}
MAX_OCCURRENCES = 200

app = Flask(__name__)
app.secret_key = os.environ.get("CALENDAR_SECRET_KEY", "dev-secret-change-me")
app.config["JSON_SORT_KEYS"] = False


@dataclass
class User:
    username: str
    api_key: str
    password_salt: bytes
    password_hash: bytes
    iterations: int


def _load_users() -> Dict[str, User]:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    users: Dict[str, User] = {}
    for username, payload in raw.items():
        password = payload["password"]
        users[username] = User(
            username=username,
            api_key=payload.get("api_key", ""),
            password_salt=base64.b64decode(password["salt"]),
            password_hash=base64.b64decode(password["hash"]),
            iterations=int(password.get("iterations", PASSWORD_ITERATIONS)),
        )
    return users


def _save_users(users: Dict[str, User]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    payload: Dict[str, Any] = {}
    for username, user in users.items():
        payload[username] = {
            "password": {
                "salt": base64.b64encode(user.password_salt).decode("utf-8"),
                "iterations": user.iterations,
                "hash": base64.b64encode(user.password_hash).decode("utf-8"),
            },
            "api_key": user.api_key,
        }
    with open(USERS_FILE, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _hash_password(password: str) -> tuple[bytes, bytes]:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return salt, digest


def _verify_password(user: User, password: str) -> bool:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        user.password_salt,
        user.iterations,
    )
    return hmac.compare_digest(digest, user.password_hash)


def _validate_username(username: str) -> bool:
    return bool(USERNAME_PATTERN.match(username))


def _validate_password(password: str) -> bool:
    return bool(PASSWORD_PATTERN.match(password))


def _generate_api_key() -> str:
    return f"cs_{secrets.token_urlsafe(24)}"


def _get_schedule_path(username: str) -> str:
    filename = f"{username}.json"
    return os.path.join(SCHEDULE_DIR, filename)


def _load_schedule(username: str) -> Dict[str, Any]:
    os.makedirs(SCHEDULE_DIR, exist_ok=True)
    path = _get_schedule_path(username)
    if not os.path.exists(path):
        return {"next_id": 1, "items": []}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_schedule(username: str, data: Dict[str, Any]) -> None:
    os.makedirs(SCHEDULE_DIR, exist_ok=True)
    path = _get_schedule_path(username)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def _get_user_from_api_key(api_key: str) -> Optional[str]:
    users = _load_users()
    for username, user in users.items():
        if user.api_key == api_key:
            return username
    return None


def _current_username() -> Optional[str]:
    if "username" in session:
        return session["username"]
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            api_key = auth.split(" ", 1)[1].strip()
    if api_key:
        return _get_user_from_api_key(api_key)
    return None


def _parse_event_time(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except (TypeError, ValueError):
        raise ValueError("time must be YYYY-MM-DDTHH:MM")


def _parse_end_date(value: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise ValueError("recurrence.until must be YYYY-MM-DD")
    return parsed.replace(hour=23, minute=59)


def _normalize_recurrence(payload: Dict[str, Any]) -> Dict[str, Any]:
    recurrence = payload.get("recurrence") or {}
    frequency = (recurrence.get("frequency") or "none").lower()
    if frequency not in ALLOWED_FREQUENCIES:
        raise ValueError("recurrence.frequency is invalid")

    if frequency == "none":
        return {"frequency": "none", "end_type": "never", "until": None, "count": None}

    end_type = (recurrence.get("end_type") or "never").lower()
    if end_type not in ALLOWED_END_TYPES:
        raise ValueError("recurrence.end_type is invalid")

    until_value = None
    count_value = None
    if end_type == "until":
        until_raw = recurrence.get("until")
        until_value = _parse_end_date(until_raw).strftime("%Y-%m-%d")
    elif end_type == "count":
        try:
            count_value = int(recurrence.get("count"))
        except (TypeError, ValueError):
            raise ValueError("recurrence.count must be an integer")
        if count_value < 1:
            raise ValueError("recurrence.count must be greater than 0")

    return {
        "frequency": frequency,
        "end_type": end_type,
        "until": until_value,
        "count": count_value,
    }


def _advance_occurrence(current: datetime, frequency: str) -> datetime:
    if frequency == "daily":
        return current + timedelta(days=1)
    if frequency == "weekly":
        return current + timedelta(weeks=1)
    if frequency == "monthly":
        year = current.year + (current.month // 12)
        month = (current.month % 12) + 1
        day = min(current.day, calendar.monthrange(year, month)[1])
        return current.replace(year=year, month=month, day=day)
    if frequency == "yearly":
        year = current.year + 1
        day = min(current.day, calendar.monthrange(year, current.month)[1])
        return current.replace(year=year, day=day)
    return current


def _build_occurrences(item: Dict[str, Any], query_start: Optional[datetime], query_end: Optional[datetime]) -> list[Dict[str, Any]]:
    base_time = _parse_event_time(item["time"])
    recurrence = item.get("recurrence") or {"frequency": "none"}
    frequency = recurrence.get("frequency", "none")
    if frequency == "none":
        if query_start and base_time < query_start:
            return []
        if query_end and base_time > query_end:
            return []
        return [{**item, "occurrence_time": item["time"], "source_id": item["id"]}]

    end_type = recurrence.get("end_type", "never")
    until_dt = _parse_end_date(recurrence.get("until")) if recurrence.get("until") else None
    max_count = recurrence.get("count") if recurrence.get("count") else MAX_OCCURRENCES
    max_count = min(int(max_count), MAX_OCCURRENCES)

    if end_type == "until" and until_dt:
        absolute_end = until_dt
    elif query_end:
        absolute_end = query_end
    else:
        absolute_end = base_time + timedelta(days=366)

    if query_start and base_time > absolute_end:
        return []

    events: list[Dict[str, Any]] = []
    cursor = base_time
    emitted = 0
    while emitted < max_count and cursor <= absolute_end:
        if (not query_start or cursor >= query_start) and (not query_end or cursor <= query_end):
            events.append({
                **item,
                "occurrence_time": cursor.strftime("%Y-%m-%dT%H:%M"),
                "source_id": item["id"],
            })
        emitted += 1
        cursor = _advance_occurrence(cursor, frequency)

    return events


def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        username = _current_username()
        if not username:
            abort(401, description="Authentication required")
        return func(username, *args, **kwargs)

    return wrapper


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or request.form
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    users = _load_users()
    user = users.get(username)
    if not user or not _verify_password(user, password):
        return jsonify({"message": "Invalid username or password"}), 401
    session["username"] = username
    return jsonify({"message": "Login successful", "username": username})


@app.route("/api/register", methods=["POST"])
def register():
    payload = request.get_json(force=True)
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not _validate_username(username):
        return jsonify({"message": "Username must be 4-20 chars (letters, numbers, underscore)"}), 400
    if not _validate_password(password):
        return jsonify({"message": "Password must be at least 8 chars and include letters and numbers"}), 400

    users = _load_users()
    if username in users:
        return jsonify({"message": "Username already exists"}), 400

    salt, password_hash = _hash_password(password)
    api_key = _generate_api_key()
    users[username] = User(
        username=username,
        api_key=api_key,
        password_salt=salt,
        password_hash=password_hash,
        iterations=PASSWORD_ITERATIONS,
    )
    _save_users(users)
    _save_schedule(username, {"next_id": 1, "items": []})
    return jsonify({"message": "Registration successful", "username": username, "api_key": api_key}), 201


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("username", None)
    return jsonify({"message": "Logged out"})


@app.route("/session", methods=["GET"])
def session_info():
    username = session.get("username")
    return jsonify({"username": username})


def _list_events(username: str):
    data = _load_schedule(username)
    if request.args.get("expand") != "1":
        return jsonify({"items": data["items"]})

    start_raw = request.args.get("start")
    end_raw = request.args.get("end")
    query_start = _parse_event_time(start_raw) if start_raw else None
    query_end = _parse_event_time(end_raw) if end_raw else None
    occurrences: list[Dict[str, Any]] = []
    for item in data["items"]:
        occurrences.extend(_build_occurrences(item, query_start, query_end))
    occurrences.sort(key=lambda item: item["occurrence_time"])
    return jsonify({"items": occurrences})


def _create_event(username: str):
    data = _load_schedule(username)
    payload = request.get_json(force=True)

    required = ["title", "time", "location", "description"]
    if not all(payload.get(field) for field in required):
        return jsonify({"message": "All fields are required"}), 400

    try:
        _parse_event_time(payload["time"])
        recurrence = _normalize_recurrence(payload)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    item = {
        "id": data["next_id"],
        "title": payload["title"],
        "time": payload["time"],
        "location": payload["location"],
        "description": payload["description"],
        "recurrence": recurrence,
    }
    data["next_id"] += 1
    data["items"].append(item)
    _save_schedule(username, data)
    return jsonify(item), 201


@app.route("/api/events", methods=["GET", "POST"])
@require_auth
def events(username: str):
    if request.method == "GET":
        return _list_events(username)
    return _create_event(username)


@app.route("/api/events/<int:item_id>", methods=["GET", "PUT", "DELETE"])
@require_auth
def event_detail(username: str, item_id: int):
    data = _load_schedule(username)
    items = data["items"]
    item = next((entry for entry in items if entry["id"] == item_id), None)
    if not item:
        return jsonify({"message": "Schedule item not found"}), 404

    if request.method == "GET":
        return jsonify(item)

    if request.method == "DELETE":
        data["items"] = [entry for entry in items if entry["id"] != item_id]
        _save_schedule(username, data)
        return jsonify({"message": "Deleted"})

    payload = request.get_json(force=True)
    try:
        if "time" in payload:
            _parse_event_time(payload["time"])
        if "recurrence" in payload:
            item["recurrence"] = _normalize_recurrence(payload)
        for field in ["title", "time", "location", "description"]:
            if field in payload:
                item[field] = payload[field]
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400

    if "recurrence" not in item:
        item["recurrence"] = {"frequency": "none", "end_type": "never", "until": None, "count": None}
    _save_schedule(username, data)
    return jsonify(item)


@app.route("/api/schedules", methods=["GET", "POST"])
@require_auth
def schedules(username: str):
    if request.method == "GET":
        return _list_events(username)
    return _create_event(username)


@app.route("/api/schedules/<int:item_id>", methods=["GET", "PUT", "DELETE"])
@require_auth
def schedule_detail(username: str, item_id: int):
    return event_detail(username, item_id)


@app.route("/api/profile", methods=["GET"])
@require_auth
def profile(username: str):
    users = _load_users()
    user = users.get(username)
    if not user:
        return jsonify({"message": "User not found"}), 404
    return jsonify({"username": user.username, "api_key": user.api_key})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    os.makedirs(SCHEDULE_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
