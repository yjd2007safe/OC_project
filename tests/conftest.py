import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SCHEDULES_DIR = DATA_DIR / "schedules"


@pytest.fixture
def client():
    """Flask test client fixture"""
    from app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_client(client):
    """Authenticated test client"""
    # Register a test user
    client.post(
        "/api/register",
        json={"username": "testuser", "password": "TestPass123"},
    )
    # Login
    client.post(
        "/login",
        json={"username": "testuser", "password": "TestPass123"},
    )
    yield client


@pytest.fixture(autouse=True)
def clean_test_data():
    """Isolate data directory for every test case."""

    backup_dir = Path(tempfile.mkdtemp(prefix="calendar_data_backup_")) / "data"

    # Backup current data directory (if any) and start from a clean state
    if DATA_DIR.exists():
        shutil.copytree(DATA_DIR, backup_dir)
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SCHEDULES_DIR.mkdir(parents=True, exist_ok=True)

    try:
        yield
    finally:
        # Clean up test artifacts and restore original data snapshot
        if DATA_DIR.exists():
            shutil.rmtree(DATA_DIR)
        if backup_dir.exists():
            shutil.copytree(backup_dir, DATA_DIR)
        else:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            SCHEDULES_DIR.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(backup_dir.parent, ignore_errors=True)
