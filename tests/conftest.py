import os
import sys

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Use isolated sqlite database for every test."""
    import app as app_module

    db_path = tmp_path / "calendar_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setattr(app_module, "_STORAGE", None)


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
