import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    # Register a test user
    client.post('/api/register', json={
        'username': 'testuser',
        'password': 'TestPass123'
    })
    # Login
    client.post('/login', json={
        'username': 'testuser',
        'password': 'TestPass123'
    })
    yield client

@pytest.fixture(autouse=True)
def clean_test_data():
    """Clean up test data before each test"""
    # Setup - clean before test
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    users_file = os.path.join(data_dir, 'users.json')
    schedules_dir = os.path.join(data_dir, 'schedules')
    
    # Save original state if exists
    original_users = None
    if os.path.exists(users_file):
        with open(users_file, 'r', encoding='utf-8') as f:
            original_users = f.read()
    
    yield
    
    # Teardown - restore or clean after test
    # Remove test user data
    test_schedule = os.path.join(schedules_dir, 'testuser.json')
    if os.path.exists(test_schedule):
        os.remove(test_schedule)
