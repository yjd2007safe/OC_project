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
    CONSTRAINT fk_events_user FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_events_username ON events(username);
CREATE INDEX IF NOT EXISTS idx_events_username_time ON events(username, time);
