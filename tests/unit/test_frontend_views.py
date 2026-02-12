"""前端视图相关测试"""

from pathlib import Path


def test_index_contains_view_switch_controls(client):
    """首页模板包含日/周/月视图切换与导航按钮"""
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'data-view="day"' in html
    assert 'data-view="week"' in html
    assert 'data-view="month"' in html
    assert 'id="prev-period"' in html
    assert 'id="today-period"' in html
    assert 'id="next-period"' in html
    assert 'id="calendar-content"' in html


def test_script_persists_selected_view():
    """前端脚本使用 localStorage 持久化视图模式"""
    script = Path("static/script.js").read_text(encoding="utf-8")

    assert 'const VIEW_STORAGE_KEY = "calendarSecretary.view";' in script
    assert 'localStorage.getItem(VIEW_STORAGE_KEY)' in script
    assert 'localStorage.setItem(VIEW_STORAGE_KEY, state.currentView);' in script
    assert 'const renderMonthView = () => {' in script
