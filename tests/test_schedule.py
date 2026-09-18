# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""日程 CRUD REST API 测试"""
import pytest


def _create(client, name="张三", duty_date="2026-03-15", **extra):
    payload = {"name": name, "duty_date": duty_date}
    payload.update(extra)
    return client.post("/api/schedules", json=payload)


def test_create_schedule(client):
    """创建日程成功，返回 201 与新 ID"""
    resp = _create(client, start_time="08:00", end_time="12:00", location="图书馆")
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["code"] == 0
    assert isinstance(body["data"]["id"], int)


def test_create_schedule_missing_required(client):
    """缺少姓名/日期返回 400"""
    resp = client.post("/api/schedules", json={"name": "张三"})
    assert resp.status_code == 400
    assert resp.get_json()["code"] == 1


def test_create_schedule_invalid_json(client):
    """请求体不是合法 JSON 时返回 400，而不是抛 415/500"""
    resp = client.post(
        "/api/schedules",
        data="这不是JSON",
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_list_and_detail(client):
    """列表与详情查询"""
    new_id = _create(client).get_json()["data"]["id"]

    list_resp = client.get("/api/schedules")
    assert list_resp.status_code == 200
    assert list_resp.get_json()["total"] == 1

    detail = client.get(f"/api/schedules/{new_id}")
    assert detail.status_code == 200
    assert detail.get_json()["data"]["name"] == "张三"


def test_detail_not_found(client):
    """查询不存在的 ID 返回 404 与统一结构"""
    resp = client.get("/api/schedules/999999")
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["code"] == 1
    assert body["msg"] == "日程不存在"
    assert body["data"] is None


def test_update_schedule(client):
    """更新日程字段"""
    new_id = _create(client).get_json()["data"]["id"]
    resp = client.put(f"/api/schedules/{new_id}", json={"location": "行政楼301"})
    assert resp.status_code == 200

    detail = client.get(f"/api/schedules/{new_id}").get_json()["data"]
    assert detail["location"] == "行政楼301"


def test_update_rejects_non_whitelisted_field(client):
    """更新接口不允许修改白名单之外的字段（如 source_type）"""
    new_id = _create(client).get_json()["data"]["id"]
    resp = client.put(f"/api/schedules/{new_id}", json={"source_type": "hacked"})
    # 无有效更新字段 -> 400
    assert resp.status_code == 400
    detail = client.get(f"/api/schedules/{new_id}").get_json()["data"]
    assert detail["source_type"] == "manual"


def test_update_not_found(client):
    """更新不存在的 ID 返回 404"""
    resp = client.put("/api/schedules/999999", json={"location": "x"})
    assert resp.status_code == 404


def test_confirm_schedule(client):
    """确认日程"""
    new_id = _create(client).get_json()["data"]["id"]
    resp = client.post(f"/api/schedules/{new_id}/confirm")
    assert resp.status_code == 200
    detail = client.get(f"/api/schedules/{new_id}").get_json()["data"]
    assert detail["is_confirmed"] == 1


def test_confirm_not_found(client):
    """确认不存在的 ID 返回 404"""
    resp = client.post("/api/schedules/999999/confirm")
    assert resp.status_code == 404


def test_delete_schedule(client):
    """删除日程后再次删除返回 404"""
    new_id = _create(client).get_json()["data"]["id"]
    assert client.delete(f"/api/schedules/{new_id}").status_code == 200
    assert client.delete(f"/api/schedules/{new_id}").status_code == 404
    assert client.get(f"/api/schedules/{new_id}").status_code == 404


def test_delete_not_found(client):
    """删除不存在的 ID 不能返回成功"""
    resp = client.delete("/api/schedules/999999")
    assert resp.status_code == 404
    assert resp.get_json()["code"] == 1
