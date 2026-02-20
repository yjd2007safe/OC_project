"""集成测试 - API + 数据库存储场景"""

from concurrent.futures import ThreadPoolExecutor


def _register_and_login(client, username: str = "itestuser", password: str = "Test1234"):
    reg = client.post("/api/register", json={"username": username, "password": password})
    assert reg.status_code == 201
    login = client.post("/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return reg.get_json()["api_key"]


class TestAuthFlow:
    def test_register_login_and_profile(self, client):
        api_key = _register_and_login(client)
        response = client.get("/api/profile", headers={"X-API-Key": api_key})
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["username"] == "itestuser"
        assert payload["api_key"] == api_key


class TestEventCrud:
    def test_event_crud_contract(self, client):
        api_key = _register_and_login(client, username="cruduser")
        headers = {"X-API-Key": api_key}

        create_resp = client.post(
            "/api/events",
            headers=headers,
            json={
                "title": "Demo",
                "time": "2026-01-01T10:00",
                "end_time": "2026-01-01T11:00",
                "location": "Room A",
                "description": "planning",
            },
        )
        assert create_resp.status_code == 201
        item = create_resp.get_json()
        item_id = item["id"]

        list_resp = client.get("/api/events", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.get_json()["items"]) == 1

        detail_resp = client.get(f"/api/events/{item_id}", headers=headers)
        assert detail_resp.status_code == 200

        update_resp = client.put(
            f"/api/events/{item_id}",
            headers=headers,
            json={"location": "Room B", "description": "updated"},
        )
        assert update_resp.status_code == 200
        assert update_resp.get_json()["location"] == "Room B"

        delete_resp = client.delete(f"/api/events/{item_id}", headers=headers)
        assert delete_resp.status_code == 200

        final_list = client.get("/api/events", headers=headers)
        assert final_list.status_code == 200
        assert final_list.get_json()["items"] == []


class TestConfigAndConcurrency:
    def test_returns_json_when_database_not_configured(self, client, monkeypatch):
        import app as app_module

        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setattr(app_module, "_STORAGE", None)
        response = client.post("/api/register", json={"username": "nouser", "password": "Test1234"})
        assert response.status_code == 503
        data = response.get_json()
        assert data["error"] == "database_not_configured"

    def test_concurrent_event_creation_basic(self, client):
        from app import app

        api_key = _register_and_login(client, username="concurrent")
        headers = {"X-API-Key": api_key}

        def create(i: int):
            with app.test_client() as worker_client:
                return worker_client.post(
                    "/api/events",
                    headers=headers,
                    json={
                        "title": f"E{i}",
                        "time": f"2026-01-01T{i:02d}:00",
                        "end_time": f"2026-01-01T{i+1:02d}:00",
                        "location": "Online",
                        "description": "batch",
                    },
                ).status_code

        with ThreadPoolExecutor(max_workers=4) as pool:
            statuses = list(pool.map(create, range(8, 12)))

        assert all(code == 201 for code in statuses)
        response = client.get("/api/events", headers=headers)
        assert response.status_code == 200
        assert len(response.get_json()["items"]) == 4
