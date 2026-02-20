from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Generator, Optional
from urllib.parse import urlparse


class StorageError(Exception):
    """Base storage error."""


class StorageConfigError(StorageError):
    """Raised when database configuration is missing or invalid."""


@dataclass
class DBConfig:
    database_url: str
    supabase_url: str
    supabase_service_role_key: str


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    api_key TEXT UNIQUE NOT NULL,
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    iterations INTEGER NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    title TEXT NOT NULL,
    time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT NOT NULL,
    recurrence TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_events_username ON events(username);
CREATE INDEX IF NOT EXISTS idx_events_username_time ON events(username, time);
"""


class DatabaseStorage:
    def __init__(self, config: Optional[DBConfig] = None):
        self.config = config or self._load_config()
        self.database_url = self.config.database_url
        self._backend = self._detect_backend(self.database_url)

    @staticmethod
    def _load_config() -> DBConfig:
        database_url = os.environ.get("DATABASE_URL", "").strip()
        supabase_url = os.environ.get("SUPABASE_URL", "").strip()
        supabase_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not database_url:
            raise StorageConfigError(
                "Database not configured. Please set DATABASE_URL (and SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY for Supabase deployment)."
            )
        return DBConfig(
            database_url=database_url,
            supabase_url=supabase_url,
            supabase_service_role_key=supabase_service_role_key,
        )

    @staticmethod
    def _detect_backend(database_url: str) -> str:
        parsed = urlparse(database_url)
        scheme = parsed.scheme.lower()
        if scheme in {"sqlite", ""}:
            return "sqlite"
        if scheme in {"postgres", "postgresql"}:
            return "postgres"
        raise StorageConfigError(f"Unsupported DATABASE_URL scheme: {scheme}")

    @contextmanager
    def connection(self) -> Generator[Any, None, None]:
        if self._backend == "sqlite":
            conn = sqlite3.connect(self.database_url.replace("sqlite:///", ""), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
            return

        try:
            import psycopg
        except ImportError as exc:
            raise StorageConfigError(
                "Postgres DATABASE_URL detected but psycopg is not installed. Install psycopg[binary]."
            ) from exc

        conn = psycopg.connect(self.database_url)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connection() as conn:
            if self._backend == "sqlite":
                conn.executescript(SCHEMA_SQL)
            else:
                with conn.cursor() as cur:
                    for stmt in [segment.strip() for segment in SCHEMA_SQL.split(";") if segment.strip()]:
                        cur.execute(stmt)

    def load_users(self) -> Dict[str, Dict[str, Any]]:
        with self.connection() as conn:
            if self._backend == "sqlite":
                rows = conn.execute("SELECT * FROM users").fetchall()
            else:
                with conn.cursor() as cur:
                    cur.execute("SELECT username, api_key, password_salt, password_hash, iterations, enabled, created_at FROM users")
                    rows = cur.fetchall()
        users: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            username = row[0] if not hasattr(row, "keys") else row["username"]
            users[username] = {
                "api_key": row[1] if not hasattr(row, "keys") else row["api_key"],
                "password": {
                    "salt": row[2] if not hasattr(row, "keys") else row["password_salt"],
                    "hash": row[3] if not hasattr(row, "keys") else row["password_hash"],
                    "iterations": int(row[4] if not hasattr(row, "keys") else row["iterations"]),
                },
                "enabled": bool(row[5] if not hasattr(row, "keys") else row["enabled"]),
                "created_at": row[6] if not hasattr(row, "keys") else row["created_at"],
            }
        return users

    def save_users(self, users: Dict[str, Dict[str, Any]]) -> None:
        with self.connection() as conn:
            if self._backend == "sqlite":
                conn.execute("DELETE FROM users")
                for username, payload in users.items():
                    conn.execute(
                        """
                        INSERT INTO users (username, api_key, password_salt, password_hash, iterations, enabled, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            username,
                            payload["api_key"],
                            payload["password"]["salt"],
                            payload["password"]["hash"],
                            payload["password"]["iterations"],
                            1 if payload.get("enabled", True) else 0,
                            payload.get("created_at", ""),
                        ),
                    )
            else:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM users")
                    for username, payload in users.items():
                        cur.execute(
                            """
                            INSERT INTO users (username, api_key, password_salt, password_hash, iterations, enabled, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                username,
                                payload["api_key"],
                                payload["password"]["salt"],
                                payload["password"]["hash"],
                                payload["password"]["iterations"],
                                payload.get("enabled", True),
                                payload.get("created_at", ""),
                            ),
                        )

    def load_schedule(self, username: str) -> Dict[str, Any]:
        with self.connection() as conn:
            if self._backend == "sqlite":
                rows = conn.execute(
                    "SELECT id, title, time, end_time, location, description, recurrence, created_at FROM events WHERE username=? ORDER BY id",
                    (username,),
                ).fetchall()
            else:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, title, time, end_time, location, description, recurrence, created_at FROM events WHERE username=%s ORDER BY id",
                        (username,),
                    )
                    rows = cur.fetchall()
        items = []
        max_id = 0
        for row in rows:
            item_id = int(row[0] if not hasattr(row, "keys") else row["id"])
            max_id = max(max_id, item_id)
            rec_raw = row[6] if not hasattr(row, "keys") else row["recurrence"]
            items.append(
                {
                    "id": item_id,
                    "title": row[1] if not hasattr(row, "keys") else row["title"],
                    "time": row[2] if not hasattr(row, "keys") else row["time"],
                    "end_time": row[3] if not hasattr(row, "keys") else row["end_time"],
                    "location": row[4] if not hasattr(row, "keys") else row["location"],
                    "description": row[5] if not hasattr(row, "keys") else row["description"],
                    "recurrence": json.loads(rec_raw),
                    "created_at": row[7] if not hasattr(row, "keys") else row["created_at"],
                }
            )
        return {"next_id": max_id + 1, "items": items}

    def create_event(self, username: str, item: Dict[str, Any]) -> Dict[str, Any]:
        with self.connection() as conn:
            if self._backend == "sqlite":
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM events WHERE username=?", (username,)).fetchone()
                next_id = int(row[0])
                conn.execute(
                    """
                    INSERT INTO events (id, username, title, time, end_time, location, description, recurrence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        next_id,
                        username,
                        item["title"],
                        item["time"],
                        item["end_time"],
                        item["location"],
                        item["description"],
                        json.dumps(item.get("recurrence", {"frequency": "none", "end_type": "never", "until": None, "count": None}), ensure_ascii=False),
                        item["created_at"],
                    ),
                )
            else:
                with conn.cursor() as cur:
                    cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM events WHERE username=%s FOR UPDATE", (username,))
                    next_id = int(cur.fetchone()[0])
                    cur.execute(
                        """
                        INSERT INTO events (id, username, title, time, end_time, location, description, recurrence, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            next_id,
                            username,
                            item["title"],
                            item["time"],
                            item["end_time"],
                            item["location"],
                            item["description"],
                            json.dumps(item.get("recurrence", {"frequency": "none", "end_type": "never", "until": None, "count": None}), ensure_ascii=False),
                            item["created_at"],
                        ),
                    )
        return {"id": next_id, **item}

    def save_schedule(self, username: str, data: Dict[str, Any]) -> None:
        items = data.get("items", [])
        with self.connection() as conn:
            if self._backend == "sqlite":
                conn.execute("DELETE FROM events WHERE username=?", (username,))
                for item in items:
                    conn.execute(
                        """
                        INSERT INTO events (id, username, title, time, end_time, location, description, recurrence, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item["id"],
                            username,
                            item["title"],
                            item["time"],
                            item.get("end_time", item["time"]),
                            item["location"],
                            item.get("description", ""),
                            json.dumps(item.get("recurrence", {"frequency": "none", "end_type": "never", "until": None, "count": None}), ensure_ascii=False),
                            item.get("created_at", ""),
                        ),
                    )
            else:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM events WHERE username=%s", (username,))
                    for item in items:
                        cur.execute(
                            """
                            INSERT INTO events (id, username, title, time, end_time, location, description, recurrence, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                item["id"],
                                username,
                                item["title"],
                                item["time"],
                                item.get("end_time", item["time"]),
                                item["location"],
                                item.get("description", ""),
                                json.dumps(item.get("recurrence", {"frequency": "none", "end_type": "never", "until": None, "count": None}), ensure_ascii=False),
                                item.get("created_at", ""),
                            ),
                        )
