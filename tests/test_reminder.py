# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""提醒配置接口测试：创建、查询、修改、删除、不存在日程/提醒"""
import pytest


@pytest.fixture
def schedule_id(client):
    return client.post("/api/schedules", json={
        "name": "张三",
        "duty_date": "2026-03-15",
        "start_time": "08:00",
        "end_time": "12:00",
        "location": "图书馆",
    }).get_json()["data"]["id"]


def test_create_reminder(client, schedule_id):
    """为有效日程创建提醒"""
    resp = client.post("/api/reminders", json={
        "schedule_id": schedule_id,
        "advance_minutes": 30,
        "custom_message": "记得提前到岗",
    })
    assert resp.status_code == 201
    assert resp.get_json()["data"]["id"]


def test_create_reminder_for_missing_schedule(client):
    """为不存在的日程创建提醒返回 404"""
    resp = client.post("/api/reminders", json={"schedule_id": 999999})
    assert resp.status_code == 404
    assert resp.get_json()["code"] == 1


def test_create_reminder_invalid_advance(client, schedule_id):
    """提前分钟数非法返回 400"""
    resp = client.post("/api/reminders", json={
        "schedule_id": schedule_id,
        "advance_minutes": "abc",
    })
    assert resp.status_code == 400


def test_list_reminders(client, schedule_id):
    """提醒列表查询（含联表字段）"""
    client.post("/api/reminders", json={"schedule_id": schedule_id})
    resp = client.get("/api/reminders")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1
    assert body["data"][0]["name"] == "张三"


def test_update_reminder(client, schedule_id):
    """修改提醒配置"""
    rid = client.post("/api/reminders", json={"schedule_id": schedule_id}).get_json()["data"]["id"]
    resp = client.put(f"/api/reminders/{rid}", json={"advance_minutes": 60})
    assert resp.status_code == 200

    rows = client.get("/api/reminders").get_json()["data"]
    assert rows[0]["advance_minutes"] == 60


def test_update_reminder_not_found(client):
    """修改不存在的提醒返回 404"""
    resp = client.put("/api/reminders/999999", json={"advance_minutes": 10})
    assert resp.status_code == 404


def test_delete_reminder(client, schedule_id):
    """删除提醒，重复删除返回 404"""
    rid = client.post("/api/reminders", json={"schedule_id": schedule_id}).get_json()["data"]["id"]
    assert client.delete(f"/api/reminders/{rid}").status_code == 200
    assert client.delete(f"/api/reminders/{rid}").status_code == 404


def test_delete_reminder_not_found(client):
    """删除不存在的提醒返回 404"""
    assert client.delete("/api/reminders/999999").status_code == 404
