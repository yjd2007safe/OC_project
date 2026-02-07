"""单元测试 - 日程和重复功能"""
import pytest
from datetime import datetime, timedelta
from app import (
    _parse_event_time,
    _parse_end_date,
    _normalize_recurrence,
    _advance_occurrence,
    _build_occurrences,
    ALLOWED_FREQUENCIES,
    ALLOWED_END_TYPES,
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
