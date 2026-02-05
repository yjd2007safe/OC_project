from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from functools import wraps
from typing import Any, Dict, Optional

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SCHEDULE_DIR = os.path.join(DATA_DIR, "schedules")

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
            iterations=int(password.get("iterations", 260000)),
        )
    return users


def _verify_password(user: User, password: str) -> bool:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        user.password_salt,
        user.iterations,
    )
    return hmac.compare_digest(digest, user.password_hash)


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


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("username", None)
    return jsonify({"message": "Logged out"})


@app.route("/session", methods=["GET"])
def session_info():
    username = session.get("username")
    return jsonify({"username": username})


@app.route("/api/schedules", methods=["GET", "POST"])
@require_auth
def schedules(username: str):
    data = _load_schedule(username)
    if request.method == "GET":
        return jsonify({"items": data["items"]})

    payload = request.get_json(force=True)
    required = ["title", "time", "location", "description"]
    if not all(payload.get(field) for field in required):
        return jsonify({"message": "All fields are required"}), 400

    item = {
        "id": data["next_id"],
        "title": payload["title"],
        "time": payload["time"],
        "location": payload["location"],
        "description": payload["description"],
    }
    data["next_id"] += 1
    data["items"].append(item)
    _save_schedule(username, data)
    return jsonify(item), 201


@app.route("/api/schedules/<int:item_id>", methods=["GET", "PUT", "DELETE"])
@require_auth
def schedule_detail(username: str, item_id: int):
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
    for field in ["title", "time", "location", "description"]:
        if field in payload:
            item[field] = payload[field]
    _save_schedule(username, data)
    return jsonify(item)


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
