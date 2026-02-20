"""集成测试 - API接口测试"""
import pytest
import json
import os
import tempfile
import shutil
from app import app, DATA_DIR, USERS_FILE, SCHEDULE_DIR


@pytest.fixture
def client():
    """创建测试客户端"""
    # 使用临时数据目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # 备份原始数据目录路径
        original_data_dir = DATA_DIR

        # 设置临时数据目录
        test_data_dir = os.path.join(tmpdir, "data")
        os.makedirs(test_data_dir, exist_ok=True)
        os.makedirs(os.path.join(test_data_dir, "schedules"), exist_ok=True)

        # 修改应用配置
        app.config["TESTING"] = True
        app.config["DATA_DIR"] = test_data_dir

        # 创建测试客户端
        with app.test_client() as client:
            yield client


@pytest.fixture
def auth_client(client):
    """创建已认证的测试客户端"""
    # 注册用户
    client.post("/api/register", json={
        "username": "testuser",
        "password": "Test1234"
    })
    # 登录
    client.post("/login", json={
        "username": "testuser",
        "password": "Test1234"
    })
    return client


@pytest.fixture
def api_key_client(client):
    """创建使用API Key的测试客户端"""
    # 注册用户
    response = client.post("/api/register", json={
        "username": "apiuser",
        "password": "Test1234"
    })
    data = response.get_json()
    api_key = data.get("api_key")

    # 返回带API Key的客户端函数
    def make_request(method, url, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["X-API-Key"] = api_key
        kwargs["headers"] = headers
        return getattr(client, method)(url, **kwargs)

    return make_request, api_key


class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"


class TestRegistration:
    """用户注册接口测试"""

    def test_register_success(self, client):
        """测试正常注册"""
        response = client.post("/api/register", json={
            "username": "newuser",
            "password": "Test1234"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["username"] == "newuser"
        assert "api_key" in data
        assert data["message"] == "Registration successful"

    def test_register_duplicate_username(self, client):
        """测试重复用户名"""
        # 先注册一个用户
        client.post("/api/register", json={
            "username": "dupuser",
            "password": "Test1234"
        })
        # 再注册同样的用户名
        response = client.post("/api/register", json={
            "username": "dupuser",
            "password": "Test1234"
        })
        assert response.status_code == 400
        data = response.get_json()
        assert "already exists" in data["message"]

    def test_register_invalid_username_too_short(self, client):
        """测试用户名过短"""
        response = client.post("/api/register", json={
            "username": "ab",
            "password": "Test1234"
        })
        assert response.status_code == 400
        data = response.get_json()
        assert "Username must be" in data["message"]

    def test_register_invalid_password_no_numbers(self, client):
        """测试密码无数字"""
        response = client.post("/api/register", json={
            "username": "testuser",
            "password": "onlyletters"
        })
        assert response.status_code == 400
        data = response.get_json()
        assert "Password must be" in data["message"]

    def test_register_invalid_password_too_short(self, client):
        """测试密码过短"""
        response = client.post("/api/register", json={
            "username": "testuser",
            "password": "Test12"
        })
        assert response.status_code == 400

    def test_register_missing_fields(self, client):
        """测试缺少字段"""
        response = client.post("/api/register", json={
            "username": "testuser"
            # 缺少password
        })
        assert response.status_code == 400

    def test_register_requires_json_payload(self, client):
        """测试注册接口要求JSON负载"""
        response = client.post("/api/register", data="username=testuser")
        assert response.status_code == 400
        data = response.get_json()
        assert data["message"] == "Request payload must be JSON"

    def test_register_rejects_empty_json_payload(self, client):
        """测试注册接口拒绝空JSON负载"""
        response = client.post("/api/register", json={})
        assert response.status_code == 400
        data = response.get_json()
        assert data["message"] == "Request JSON body cannot be empty"

    def test_register_rejects_invalid_json_body(self, client):
        """测试注册接口拒绝无效JSON"""
        response = client.post(
            "/api/register",
            data="{",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["message"] == "Request JSON body is required"


    def test_register_non_json_payload(self, client):
        """测试非 JSON 请求体"""
        response = client.post(
            "/api/register",
            data="username=testuser&password=Test1234",
            content_type="application/x-www-form-urlencoded",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["message"] == "Request payload must be JSON"

    def test_register_empty_json_body(self, client):
        """测试空 JSON 请求体"""
        response = client.post(
            "/api/register",
            data="",
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["message"] == "Request JSON body is required"

    def test_register_invalid_json_body(self, client):
        """测试无效 JSON 请求体"""
        response = client.post(
            "/api/register",
            data='{"username": "testuser",',
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["message"] == "Request JSON body is invalid"


class TestLogin:
    """用户登录接口测试"""

    def test_login_success(self, client):
        """测试正常登录"""
        # 先注册
        client.post("/api/register", json={
            "username": "loginuser",
            "password": "Test1234"
        })
        # 再登录
        response = client.post("/login", json={
            "username": "loginuser",
            "password": "Test1234"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Login successful"

    def test_login_wrong_password(self, client):
        """测试错误密码"""
        # 先注册
        client.post("/api/register", json={
            "username": "loginuser2",
            "password": "Test1234"
        })
        # 用错误密码登录
        response = client.post("/login", json={
            "username": "loginuser2",
            "password": "WrongPassword"
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """测试不存在的用户"""
        response = client.post("/login", json={
            "username": "nonexistent",
            "password": "Test1234"
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        """测试缺少字段"""
        response = client.post("/login", json={
            "username": "testuser"
        })
        assert response.status_code == 401


class TestEventsAPI:
    """日程API测试"""

    def test_create_event_success(self, auth_client):
        """测试创建日程"""
        response = auth_client.post("/api/events", json={
            "title": "测试会议",
            "time": "2025-02-10T14:00",
            "location": "会议室A",
            "description": "项目讨论"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "测试会议"
        assert data["location"] == "会议室A"
        assert "id" in data

    def test_create_event_missing_fields(self, auth_client):
        """测试创建日程缺少字段"""
        response = auth_client.post("/api/events", json={
            "title": "测试会议"
            # 缺少其他必需字段
        })
        assert response.status_code == 400

    def test_create_event_invalid_time(self, auth_client):
        """测试创建日程无效时间"""
        response = auth_client.post("/api/events", json={
            "title": "测试会议",
            "time": "2025/02/10 14:00",  # 错误格式
            "location": "会议室A",
            "description": "项目讨论"
        })
        assert response.status_code == 400

    def test_create_recurring_event(self, auth_client):
        """测试创建重复日程"""
        response = auth_client.post("/api/events", json={
            "title": "周例会",
            "time": "2025-02-10T14:00",
            "location": "会议室A",
            "description": "每周例会",
            "recurrence": {
                "frequency": "weekly",
                "end_type": "count",
                "count": 4
            }
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["recurrence"]["frequency"] == "weekly"
        assert data["recurrence"]["count"] == 4

    def test_create_event_conflict(self, auth_client):
        """测试创建冲突日程"""
        first = auth_client.post("/api/events", json={
            "title": "已有会议",
            "time": "2025-02-10T10:00",
            "end_time": "2025-02-10T11:00",
            "location": "会议室A",
            "description": "冲突检测"
        })
        assert first.status_code == 201

        conflict = auth_client.post("/api/events", json={
            "title": "冲突会议",
            "time": "2025-02-10T10:30",
            "end_time": "2025-02-10T11:30",
            "location": "会议室B",
            "description": "应该失败"
        })
        assert conflict.status_code == 409
        data = conflict.get_json()
        assert "Time conflict" in data["message"]

    def test_update_event_conflict(self, auth_client):
        """测试更新日程冲突"""
        first = auth_client.post("/api/events", json={
            "title": "会议1",
            "time": "2025-02-10T10:00",
            "end_time": "2025-02-10T11:00",
            "location": "A",
            "description": "D1"
        })
        second = auth_client.post("/api/events", json={
            "title": "会议2",
            "time": "2025-02-10T12:00",
            "end_time": "2025-02-10T13:00",
            "location": "B",
            "description": "D2"
        })
        second_id = second.get_json()["id"]

        response = auth_client.put(f"/api/events/{second_id}", json={
            "time": "2025-02-10T10:30",
            "end_time": "2025-02-10T11:30"
        })
        assert response.status_code == 409
        data = response.get_json()
        assert "Time conflict" in data["message"]

    def test_create_event_lunch_warning(self, auth_client):
        """测试创建午休时段日程返回提醒"""
        response = auth_client.post("/api/events", json={
            "title": "午休会议",
            "time": "2025-02-10T12:30",
            "location": "会议室A",
            "description": "午休安排"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["warning"]["type"] == "workday_lunch"
        assert "12:00-13:30" in data["warning"]["message"]

    def test_create_event_workday_offhours_warning(self, auth_client):
        """测试创建工作日非工作时段日程返回提醒"""
        response = auth_client.post("/api/events", json={
            "title": "清晨会议",
            "time": "2025-02-10T08:00",
            "location": "会议室A",
            "description": "上班前安排"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["warning"]["type"] == "workday_offhours"
        assert "09:00前" in data["warning"]["message"]

    def test_create_event_restday_warning(self, auth_client):
        """测试创建周末日程返回提醒"""
        response = auth_client.post("/api/events", json={
            "title": "周末会议",
            "time": "2025-02-09T10:00",
            "location": "会议室A",
            "description": "周末安排"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["warning"]["type"] == "restday"
        assert data["warning"]["message"] == "该日程安排在周末"

    def test_create_event_working_hours_without_warning(self, auth_client):
        """测试创建工作时段日程不返回提醒"""
        response = auth_client.post("/api/events", json={
            "title": "周一会议",
            "time": "2025-02-10T10:00",
            "location": "会议室A",
            "description": "工作日安排"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert "warning" not in data

    def test_workday_check_endpoint_morning(self, auth_client):
        """测试工作日查询接口-上午工作时段"""
        response = auth_client.get("/api/events/workday-check?datetime=2025-02-10T09:30")
        assert response.status_code == 200
        data = response.get_json()
        assert data["datetime"] == "2025-02-10T09:30"
        assert data["is_workday"] is True
        assert data["is_working_hours"] is True
        assert data["work_period"] == "morning"
        assert data["day_type"] == "workday_working"

    def test_workday_check_endpoint_lunch(self, auth_client):
        """测试工作日查询接口-午休时段"""
        response = auth_client.get("/api/events/workday-check?datetime=2025-02-10T12:30")
        assert response.status_code == 200
        data = response.get_json()
        assert data["is_working_hours"] is False
        assert data["work_period"] is None
        assert data["day_type"] == "workday_lunch"

    def test_workday_check_endpoint_afternoon(self, auth_client):
        """测试工作日查询接口-下午工作时段"""
        response = auth_client.get("/api/events/workday-check?datetime=2025-02-10T14:30")
        assert response.status_code == 200
        data = response.get_json()
        assert data["is_working_hours"] is True
        assert data["work_period"] == "afternoon"
        assert data["day_type"] == "workday_working"

    def test_workday_check_endpoint_offhours(self, auth_client):
        """测试工作日查询接口-非工作时段"""
        response = auth_client.get("/api/events/workday-check?datetime=2025-02-10T08:30")
        assert response.status_code == 200
        data = response.get_json()
        assert data["is_working_hours"] is False
        assert data["work_period"] is None
        assert data["day_type"] == "workday_offhours"

    def test_workday_check_endpoint_restday(self, auth_client):
        """测试工作日查询接口-周末"""
        response = auth_client.get("/api/events/workday-check?datetime=2025-02-09T10:00")
        assert response.status_code == 200
        data = response.get_json()
        assert data["is_workday"] is False
        assert data["is_working_hours"] is False
        assert data["day_type"] == "restday"

    def test_workday_check_endpoint_invalid_datetime(self, auth_client):
        """测试工作日查询接口-日期时间格式错误"""
        response = auth_client.get("/api/events/workday-check?datetime=2025/02/09 10:00")
        assert response.status_code == 400
        data = response.get_json()
        assert "YYYY-MM-DDTHH:MM" in data["message"]

    def test_list_events(self, auth_client):
        """测试获取日程列表"""
        # 先创建几个日程
        auth_client.post("/api/events", json={
            "title": "会议1",
            "time": "2025-02-10T14:00",
            "location": "A",
            "description": "D1"
        })
        auth_client.post("/api/events", json={
            "title": "会议2",
            "time": "2025-02-11T15:00",
            "location": "B",
            "description": "D2"
        })

        response = auth_client.get("/api/events")
        assert response.status_code == 200
        data = response.get_json()
        assert "items" in data
        assert len(data["items"]) == 2

    def test_list_events_with_expand(self, auth_client):
        """测试展开重复日程"""
        # 创建重复日程
        auth_client.post("/api/events", json={
            "title": "每日会议",
            "time": "2025-02-10T09:00",
            "location": "会议室",
            "description": "",
            "recurrence": {
                "frequency": "daily",
                "end_type": "count",
                "count": 3
            }
        })

        response = auth_client.get("/api/events?expand=1&start=2025-02-10T00:00&end=2025-02-15T23:59")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["items"]) == 3  # 展开为3个实例

    def test_get_event_detail(self, auth_client):
        """测试获取单个日程详情"""
        # 先创建
        create_response = auth_client.post("/api/events", json={
            "title": "特定会议",
            "time": "2025-02-10T14:00",
            "location": "会议室A",
            "description": "详细描述"
        })
        event_id = create_response.get_json()["id"]

        # 再获取
        response = auth_client.get(f"/api/events/{event_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "特定会议"

    def test_get_event_not_found(self, auth_client):
        """测试获取不存在的日程"""
        response = auth_client.get("/api/events/99999")
        assert response.status_code == 404

    def test_update_event(self, auth_client):
        """测试更新日程"""
        # 先创建
        create_response = auth_client.post("/api/events", json={
            "title": "原始标题",
            "time": "2025-02-10T14:00",
            "location": "A",
            "description": "D"
        })
        event_id = create_response.get_json()["id"]

        # 更新
        response = auth_client.put(f"/api/events/{event_id}", json={
            "title": "更新后的标题",
            "location": "B"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "更新后的标题"
        assert data["location"] == "B"

    def test_delete_event(self, auth_client):
        """测试删除日程"""
        # 先创建
        create_response = auth_client.post("/api/events", json={
            "title": "待删除",
            "time": "2025-02-10T14:00",
            "location": "A",
            "description": "D"
        })
        event_id = create_response.get_json()["id"]

        # 删除
        response = auth_client.delete(f"/api/events/{event_id}")
        assert response.status_code == 200

        # 确认已删除
        get_response = auth_client.get(f"/api/events/{event_id}")
        assert get_response.status_code == 404


class TestAuthenticationRequired:
    """认证要求测试"""

    def test_events_api_requires_auth(self, client):
        """测试日程API需要认证"""
        response = client.get("/api/events")
        assert response.status_code == 401

    def test_events_post_requires_auth(self, client):
        """测试创建日程需要认证"""
        response = client.post("/api/events", json={
            "title": "测试",
            "time": "2025-02-10T14:00",
            "location": "A",
            "description": "D"
        })
        assert response.status_code == 401

    def test_profile_requires_auth(self, client):
        """测试个人信息需要认证"""
        response = client.get("/api/profile")
        assert response.status_code == 401


class TestAPIKeyAuth:
    """API Key认证测试"""

    def test_api_key_auth_success(self, client):
        """测试API Key认证成功"""
        # 注册用户
        reg_response = client.post("/api/register", json={
            "username": "apikeyuser",
            "password": "Test1234"
        })
        api_key = reg_response.get_json()["api_key"]

        # 使用API Key访问
        response = client.get("/api/events", headers={"X-API-Key": api_key})
        assert response.status_code == 200

    def test_api_key_auth_invalid(self, client):
        """测试无效API Key"""
        response = client.get("/api/events", headers={"X-API-Key": "invalid_key"})
        assert response.status_code == 401

    def test_api_key_auth_missing(self, client):
        """测试缺少API Key"""
        # 没有session也没有API Key
        with client.session_transaction() as sess:
            sess.clear()
        response = client.get("/api/events")
        assert response.status_code == 401


class TestSession:
    """Session管理测试"""

    def test_logout(self, auth_client):
        """测试登出"""
        response = auth_client.post("/logout")
        assert response.status_code == 200

        # 确认已登出
        response = auth_client.get("/api/events")
        assert response.status_code == 401

    def test_session_info(self, auth_client):
        """测试获取session信息"""
        response = auth_client.get("/session")
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == "testuser"


class TestProfile:
    """个人信息接口测试"""

    def test_get_profile(self, auth_client):
        """测试获取个人信息"""
        response = auth_client.get("/api/profile")
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == "testuser"
        assert "api_key" in data
