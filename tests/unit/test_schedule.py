"""单元测试 - 日程和重复功能"""
import pytest
from datetime import datetime, timedelta
from app import (
    _parse_event_time,
    _parse_end_date,
    _normalize_recurrence,
    _advance_occurrence,
    _build_occurrences,
    _resolve_event_range,
    _find_conflict,
    ALLOWED_FREQUENCIES,
    ALLOWED_END_TYPES,
    _check_day_type,
    _parse_workday_date,
)


class TestEventTimeParsing:
    """事件时间解析测试"""
    
    def test_parse_valid_event_time(self):
        """测试有效时间解析"""
        result = _parse_event_time("2025-02-10T14:00")
        assert result.year == 2025
        assert result.month == 2
        assert result.day == 10
        assert result.hour == 14
        assert result.minute == 0
    
    def test_parse_invalid_event_time_format(self):
        """测试无效时间格式"""
        with pytest.raises(ValueError) as exc_info:
            _parse_event_time("2025-02-10 14:00")  # wrong format
        assert "YYYY-MM-DDTHH:MM" in str(exc_info.value)
    
    def test_parse_invalid_event_time_empty(self):
        """测试空时间"""
        with pytest.raises(ValueError):
            _parse_event_time("")
    
    def test_parse_invalid_event_time_none(self):
        """测试None时间"""
        with pytest.raises((TypeError, ValueError)):
            _parse_event_time(None)


class TestEndDateParsing:
    """结束日期解析测试"""
    
    def test_parse_valid_end_date(self):
        """测试有效结束日期"""
        result = _parse_end_date("2025-12-31")
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 31
        assert result.hour == 23
        assert result.minute == 59
    
    def test_parse_invalid_end_date_format(self):
        """测试无效结束日期格式"""
        with pytest.raises(ValueError) as exc_info:
            _parse_end_date("2025/12/31")
        assert "YYYY-MM-DD" in str(exc_info.value)


class TestNormalizeRecurrence:
    """重复规则规范化测试"""
    
    def test_recurrence_none(self):
        """测试无重复"""
        result = _normalize_recurrence({"recurrence": {"frequency": "none"}})
        assert result["frequency"] == "none"
        assert result["end_type"] == "never"
    
    def test_recurrence_daily_no_end(self):
        """测试每日重复无结束"""
        result = _normalize_recurrence({
            "recurrence": {"frequency": "daily", "end_type": "never"}
        })
        assert result["frequency"] == "daily"
        assert result["end_type"] == "never"
    
    def test_recurrence_weekly_with_until(self):
        """测试每周重复带结束日期"""
        result = _normalize_recurrence({
            "recurrence": {"frequency": "weekly", "end_type": "until", "until": "2025-03-31"}
        })
        assert result["frequency"] == "weekly"
        assert result["end_type"] == "until"
        assert result["until"] == "2025-03-31"
    
    def test_recurrence_monthly_with_count(self):
        """测试每月重复带次数"""
        result = _normalize_recurrence({
            "recurrence": {"frequency": "monthly", "end_type": "count", "count": 6}
        })
        assert result["frequency"] == "monthly"
        assert result["end_type"] == "count"
        assert result["count"] == 6
    
    def test_recurrence_yearly(self):
        """测试每年重复"""
        result = _normalize_recurrence({
            "recurrence": {"frequency": "yearly", "end_type": "count", "count": 5}
        })
        assert result["frequency"] == "yearly"
    
    def test_recurrence_invalid_frequency(self):
        """测试无效频率"""
        with pytest.raises(ValueError) as exc_info:
            _normalize_recurrence({"recurrence": {"frequency": "hourly"}})
        assert "frequency is invalid" in str(exc_info.value)
    
    def test_recurrence_invalid_end_type(self):
        """测试无效结束类型"""
        with pytest.raises(ValueError) as exc_info:
            _normalize_recurrence({
                "recurrence": {"frequency": "daily", "end_type": "sometime"}
            })
        assert "end_type is invalid" in str(exc_info.value)
    
    def test_recurrence_count_zero(self):
        """测试重复次数为0"""
        with pytest.raises(ValueError) as exc_info:
            _normalize_recurrence({
                "recurrence": {"frequency": "daily", "end_type": "count", "count": 0}
            })
        assert "count must be greater than 0" in str(exc_info.value)
    
    def test_recurrence_count_negative(self):
        """测试重复次数为负数"""
        with pytest.raises(ValueError):
            _normalize_recurrence({
                "recurrence": {"frequency": "daily", "end_type": "count", "count": -1}
            })
    
    def test_recurrence_default_values(self):
        """测试默认重复值（无recurrence字段）"""
        result = _normalize_recurrence({})
        assert result["frequency"] == "none"


class TestAdvanceOccurrence:
    """重复事件推进测试"""
    
    def test_advance_daily(self):
        """测试每日推进"""
        base = datetime(2025, 2, 10, 14, 0)
        result = _advance_occurrence(base, "daily")
        assert result == datetime(2025, 2, 11, 14, 0)
    
    def test_advance_weekly(self):
        """测试每周推进"""
        base = datetime(2025, 2, 10, 14, 0)
        result = _advance_occurrence(base, "weekly")
        assert result == datetime(2025, 2, 17, 14, 0)
    
    def test_advance_monthly(self):
        """测试每月推进"""
        base = datetime(2025, 2, 10, 14, 0)
        result = _advance_occurrence(base, "monthly")
        assert result == datetime(2025, 3, 10, 14, 0)
    
    def test_advance_monthly_leap_year(self):
        """测试闰年月推进"""
        base = datetime(2024, 1, 31, 14, 0)  # Jan 31
        result = _advance_occurrence(base, "monthly")
        assert result == datetime(2024, 2, 29, 14, 0)  # Feb 29 (leap year)
    
    def test_advance_yearly(self):
        """测试每年推进"""
        base = datetime(2025, 2, 10, 14, 0)
        result = _advance_occurrence(base, "yearly")
        assert result == datetime(2026, 2, 10, 14, 0)


class TestBuildOccurrences:
    """重复事件展开测试"""
    
    def test_build_no_recurrence(self):
        """测试无重复事件"""
        item = {
            "id": 1,
            "title": "单次会议",
            "time": "2025-02-10T14:00",
            "recurrence": {"frequency": "none"}
        }
        result = _build_occurrences(item, None, None)
        assert len(result) == 1
        assert result[0]["occurrence_time"] == "2025-02-10T14:00"
    
    def test_build_daily_count_3(self):
        """测试每日重复3次"""
        item = {
            "id": 1,
            "title": "每日站会",
            "time": "2025-02-10T09:00",
            "recurrence": {"frequency": "daily", "end_type": "count", "count": 3}
        }
        result = _build_occurrences(item, None, None)
        assert len(result) == 3
        assert result[0]["occurrence_time"] == "2025-02-10T09:00"
        assert result[1]["occurrence_time"] == "2025-02-11T09:00"
        assert result[2]["occurrence_time"] == "2025-02-12T09:00"
    
    def test_build_weekly_count_4(self):
        """测试每周重复4次"""
        item = {
            "id": 1,
            "title": "周例会",
            "time": "2025-02-10T14:00",
            "recurrence": {"frequency": "weekly", "end_type": "count", "count": 4}
        }
        result = _build_occurrences(item, None, None)
        assert len(result) == 4
        # Check dates are 7 days apart
        assert result[1]["occurrence_time"] == "2025-02-17T14:00"
        assert result[2]["occurrence_time"] == "2025-02-24T14:00"
        assert result[3]["occurrence_time"] == "2025-03-03T14:00"
    
    def test_build_with_date_range_filter(self):
        """测试带日期范围过滤"""
        item = {
            "id": 1,
            "title": "每日会议",
            "time": "2025-02-10T09:00",
            "recurrence": {"frequency": "daily", "end_type": "count", "count": 10}
        }
        query_start = datetime(2025, 2, 12, 0, 0)
        query_end = datetime(2025, 2, 14, 23, 59)
        result = _build_occurrences(item, query_start, query_end)
        # Should only get Feb 12, 13, 14
        assert len(result) == 3
        assert result[0]["occurrence_time"] == "2025-02-12T09:00"
        assert result[1]["occurrence_time"] == "2025-02-13T09:00"
        assert result[2]["occurrence_time"] == "2025-02-14T09:00"
    
    def test_build_outside_date_range(self):
        """测试事件完全在查询范围外"""
        item = {
            "id": 1,
            "title": "过期会议",
            "time": "2025-01-10T09:00",
            "recurrence": {"frequency": "none"}
        }
        query_start = datetime(2025, 2, 1, 0, 0)
        query_end = datetime(2025, 2, 28, 23, 59)
        result = _build_occurrences(item, query_start, query_end)
        assert len(result) == 0
    
    def test_build_with_until_date(self):
        """测试带结束日期的重复"""
        item = {
            "id": 1,
            "title": "临时项目",
            "time": "2025-02-10T14:00",
            "recurrence": {"frequency": "daily", "end_type": "until", "until": "2025-02-14"}
        }
        result = _build_occurrences(item, None, None)
        # Should get Feb 10, 11, 12, 13, 14
        assert len(result) == 5
        assert result[-1]["occurrence_time"] == "2025-02-14T14:00"
    
    def test_build_preserves_item_data(self):
        """测试展开后保留原始数据"""
        item = {
            "id": 1,
            "title": "会议",
            "time": "2025-02-10T14:00",
            "location": "会议室A",
            "description": "项目讨论",
            "recurrence": {"frequency": "daily", "end_type": "count", "count": 2}
        }
        result = _build_occurrences(item, None, None)
        for occ in result:
            assert occ["title"] == "会议"
            assert occ["location"] == "会议室A"
            assert occ["description"] == "项目讨论"
            assert occ["source_id"] == 1


class TestWorkdayHelpers:
    """工作日判断工具函数测试"""

    def test_parse_workday_date_success(self):
        """测试工作日查询日期解析成功"""
        parsed = _parse_workday_date("2025-02-10")
        assert parsed == datetime(2025, 2, 10)

    def test_parse_workday_date_invalid(self):
        """测试工作日查询日期解析失败"""
        with pytest.raises(ValueError) as exc_info:
            _parse_workday_date("2025/02/10")
        assert "date must be YYYY-MM-DD" in str(exc_info.value)

    def test_check_day_type_workday(self):
        """测试工作日判断"""
        result = _check_day_type(datetime(2025, 2, 10))  # Monday
        assert result["is_workday"] is True
        assert result["day_type"] == "workday"

    def test_check_day_type_restday(self):
        """测试休息日判断"""
        result = _check_day_type(datetime(2025, 2, 9))  # Sunday
        assert result["is_workday"] is False
        assert result["day_type"] == "restday"



class TestConflictDetection:
    """冲突检测测试"""

    def test_resolve_event_range_with_end_time(self):
        """测试解析开始和结束时间"""
        start_at, end_at = _resolve_event_range("2025-02-10T10:00", "2025-02-10T11:00")
        assert start_at == datetime(2025, 2, 10, 10, 0)
        assert end_at == datetime(2025, 2, 10, 11, 0)

    def test_resolve_event_range_invalid_order(self):
        """测试结束时间早于开始时间"""
        with pytest.raises(ValueError) as exc_info:
            _resolve_event_range("2025-02-10T11:00", "2025-02-10T10:00")
        assert "end_time" in str(exc_info.value)

    def test_find_conflict_overlap(self):
        """测试检测重叠冲突"""
        items = [{"id": 1, "title": "已有会议", "time": "2025-02-10T10:00", "end_time": "2025-02-10T11:00"}]
        conflict = _find_conflict(items, datetime(2025, 2, 10, 10, 30), datetime(2025, 2, 10, 11, 30))
        assert conflict is not None
        assert conflict["id"] == 1

    def test_find_conflict_ignore_self(self):
        """测试更新时忽略自身"""
        items = [{"id": 1, "title": "已有会议", "time": "2025-02-10T10:00", "end_time": "2025-02-10T11:00"}]
        conflict = _find_conflict(items, datetime(2025, 2, 10, 10, 0), datetime(2025, 2, 10, 11, 0), ignore_id=1)
        assert conflict is None


class TestFindAvailableSlot:
    """可用时段匹配测试"""

    def test_find_first_slot_within_window(self):
        """测试在偏好时间段内找到最早可用时段"""
        items = [
            {
                "id": 1,
                "title": "早会",
                "time": "2025-02-10T09:00",
                "end_time": "2025-02-10T10:00",
                "recurrence": {"frequency": "none"},
            },
            {
                "id": 2,
                "title": "午会",
                "time": "2025-02-10T11:00",
                "end_time": "2025-02-10T12:00",
                "recurrence": {"frequency": "none"},
            },
        ]
        target_date = datetime(2025, 2, 10)
        from app import _find_first_available_slot

        slot = _find_first_available_slot(
            items,
            target_date,
            required_minutes=30,
            window_start=target_date.replace(hour=9, minute=0),
            window_end=target_date.replace(hour=12, minute=0),
        )
        assert slot is not None
        assert slot[0] == datetime(2025, 2, 10, 10, 0)
        assert slot[1] == datetime(2025, 2, 10, 10, 30)

    def test_find_slot_with_recurring_occurrence(self):
        """测试会考虑重复日程展开"""
        items = [
            {
                "id": 1,
                "title": "每日站会",
                "time": "2025-02-09T10:00",
                "end_time": "2025-02-09T11:00",
                "recurrence": {"frequency": "daily", "end_type": "count", "count": 3},
            }
        ]
        target_date = datetime(2025, 2, 10)
        from app import _find_first_available_slot

        slot = _find_first_available_slot(
            items,
            target_date,
            required_minutes=60,
            window_start=target_date.replace(hour=9, minute=0),
            window_end=target_date.replace(hour=12, minute=0),
        )
        assert slot is not None
        assert slot[0] == datetime(2025, 2, 10, 9, 0)
        assert slot[1] == datetime(2025, 2, 10, 10, 0)


class TestFindAndBookEndpoint:
    """智能时段匹配接口测试"""

    def test_find_and_book_success(self):
        """测试找到时段后自动创建日程"""
        from app import app

        app.config["TESTING"] = True
        with app.test_client() as client:
            register = client.post("/api/register", json={"username": "slotuser", "password": "Test1234"})
            api_key = register.get_json()["api_key"]
            headers = {"X-API-Key": api_key}

            create = client.post(
                "/api/events",
                headers=headers,
                json={
                    "title": "占用",
                    "time": "2025-02-10T09:00",
                    "end_time": "2025-02-10T10:00",
                    "location": "A",
                    "description": "busy",
                },
            )
            assert create.status_code == 201

            response = client.post(
                "/api/slots/find-and-book",
                headers=headers,
                json={
                    "target_date": "2025-02-10",
                    "duration_hours": 1.5,
                    "title": "自动安排",
                    "location": "B",
                    "description": "自动创建",
                    "preferred_start_time": "09:00",
                    "preferred_end_time": "12:00",
                },
            )
            assert response.status_code == 201
            payload = response.get_json()
            assert payload["item"]["time"] == "2025-02-10T10:00"
            assert payload["item"]["end_time"] == "2025-02-10T11:30"

    def test_find_and_book_no_slot(self):
        """测试无可用时段时返回冲突"""
        from app import app

        app.config["TESTING"] = True
        with app.test_client() as client:
            register = client.post("/api/register", json={"username": "slotuser2", "password": "Test1234"})
            api_key = register.get_json()["api_key"]
            headers = {"X-API-Key": api_key}

            client.post(
                "/api/events",
                headers=headers,
                json={
                    "title": "占用1",
                    "time": "2025-02-10T09:00",
                    "end_time": "2025-02-10T11:00",
                    "location": "A",
                    "description": "busy",
                },
            )
            client.post(
                "/api/events",
                headers=headers,
                json={
                    "title": "占用2",
                    "time": "2025-02-10T11:00",
                    "end_time": "2025-02-10T12:00",
                    "location": "A",
                    "description": "busy",
                },
            )

            response = client.post(
                "/api/slots/find-and-book",
                headers=headers,
                json={
                    "target_date": "2025-02-10",
                    "duration_hours": 1,
                    "title": "无法安排",
                    "location": "B",
                    "description": "no slot",
                    "preferred_start_time": "09:00",
                    "preferred_end_time": "12:00",
                },
            )
            assert response.status_code == 409
            assert "No available slot" in response.get_json()["message"]
