# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
上传确认流程（dry_run 预览 + apply 落库）测试
覆盖：
- dry_run=True 时 /api/upload/text 只预览不落库（id 为 None）
- 不传 dry_run 时行为不变（立即落库，兼容回归）
- /api/upload/apply 将预览结果落库，并为缺失字段生成 QA 待补充记录
"""


def test_dry_run_preview_no_save(client, mock_ai):
    mock_ai("multiple_schedules.json")
    resp = client.post("/api/upload/text", json={"text": "张三 2026-09-18 09:00-12:00 图书馆", "dry_run": "1"})
    data = resp.get_json()
    assert data["code"] == 0
    result = data["data"]
    assert result["total"] >= 1
    # 预览不落库：所有 id 为 None
    assert all(s["id"] is None for s in result["schedules"])
    # schedules 表无新增
    resp2 = client.get("/api/schedules")
    assert resp2.get_json()["total"] == 0


def test_non_dry_run_still_saves(client, mock_ai):
    """不传 dry_run 保持原有行为：立即落库"""
    mock_ai("multiple_schedules.json")
    resp = client.post("/api/upload/text", json={"text": "张三 2026-09-18 09:00-12:00 图书馆"})
    data = resp.get_json()
    assert data["code"] == 0
    assert all(s["id"] is not None for s in data["data"]["schedules"])


def test_apply_confirmed_schedules(client, mock_ai):
    """apply：预览结果落库，且缺失字段生成 QA"""
    mock_ai("missing_time.json")  # 该 fixture 包含缺失时间字段的排班
    resp = client.post("/api/upload/text", json={"text": "张三 2026-09-20 值班", "dry_run": "1"})
    preview = resp.get_json()["data"]
    assert preview["total"] >= 1

    resp = client.post("/api/upload/apply", json={
        "schedules": preview["schedules"],
        "source_type": "upload",
    })
    data = resp.get_json()
    assert data["code"] == 0
    result = data["data"]
    assert result["total"] == preview["total"]
    # 落库成功：id 均为真实值
    assert all(s["id"] is not None for s in result["schedules"])
    saved_id = result["schedules"][0]["id"]
    detail = client.get(f"/api/schedules/{saved_id}").get_json()["data"]
    assert detail["source_type"] == "upload"
    # 缺失字段生成了 QA 待补充记录
    pending = client.get("/api/qa/pending").get_json()["data"]
    assert any(q["schedule_id"] == saved_id for q in pending)


def test_apply_requires_schedules(client):
    resp = client.post("/api/upload/apply", json={"schedules": []})
    assert resp.status_code == 400
    assert resp.get_json()["code"] == 1
