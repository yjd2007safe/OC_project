import json
import os
import sys

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Use isolated users/schedules storage for every test."""
    import app as app_module

    data_dir = tmp_path / "data"
    schedules_dir = data_dir / "schedules"
    users_file = data_dir / "users.json"

    schedules_dir.mkdir(parents=True, exist_ok=True)
    users_file.write_text(json.dumps({}, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(app_module, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(app_module, "USERS_FILE", str(users_file))
    monkeypatch.setattr(app_module, "SCHEDULE_DIR", str(schedules_dir))


@pytest.fixture
def client():
    """Flask test client fixture"""
    from app import app

    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_client(client):
    """Authenticated test client"""
    client.post('/api/register', json={'username': 'testuser', 'password': 'TestPass123'})
    client.post('/login', json={'username': 'testuser', 'password': 'TestPass123'})
    yield client
