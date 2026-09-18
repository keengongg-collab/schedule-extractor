# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
GET /api/schedules 查询参数测试
覆盖：date 单日 / start+end 范围 / month 整月 / name 与日期组合
（原有 name 兼容性由 test_schedule.py 覆盖）
"""


def _seed(client):
    """预置 3 条跨月日程"""
    base = [
        ("张三", "2026-09-18", "09:00", "10:00", "会议室 A"),
        ("张三", "2026-09-19", "14:00", "15:00", "图书馆"),
        ("李四", "2026-10-01", "08:00", "09:00", "一楼"),
    ]
    for name, date, start, end, loc in base:
        client.post("/api/schedules", json={
            "name": name, "duty_date": date,
            "start_time": start, "end_time": end, "location": loc,
        })


def test_get_by_date(client):
    _seed(client)
    resp = client.get("/api/schedules?date=2026-09-18")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["code"] == 0
    assert data["total"] == 1
    assert data["data"][0]["name"] == "张三"
    assert data["data"][0]["duty_date"] == "2026-09-18"


def test_get_by_date_combined_with_name(client):
    _seed(client)
    # 日期 + 姓名组合筛选
    resp = client.get("/api/schedules?date=2026-09-18&name=张三")
    assert resp.get_json()["total"] == 1
    # 日期对但姓名不匹配
    resp = client.get("/api/schedules?date=2026-09-18&name=李四")
    assert resp.get_json()["total"] == 0


def test_get_by_range(client):
    _seed(client)
    resp = client.get("/api/schedules?start=2026-09-18&end=2026-09-30")
    data = resp.get_json()
    assert data["code"] == 0
    assert data["total"] == 2
    dates = sorted(r["duty_date"] for r in data["data"])
    assert dates == ["2026-09-18", "2026-09-19"]


def test_get_by_range_half_open(client):
    _seed(client)
    # 只有 start（无 end）：start 之后全部
    resp = client.get("/api/schedules?start=2026-10-01")
    assert resp.get_json()["total"] == 1
    # 只有 end（无 start）：end 之前全部
    resp = client.get("/api/schedules?end=2026-09-18")
    assert resp.get_json()["total"] == 1


def test_get_by_month(client):
    _seed(client)
    resp = client.get("/api/schedules?month=2026-09")
    data = resp.get_json()
    assert data["code"] == 0
    assert data["total"] == 2
    resp = client.get("/api/schedules?month=2026-10")
    assert resp.get_json()["total"] == 1


def test_get_all_still_works(client):
    _seed(client)
    resp = client.get("/api/schedules")
    assert resp.get_json()["total"] == 3
