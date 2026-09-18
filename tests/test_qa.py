# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
AI 问答（待补充信息）接口测试
覆盖：生成 QA、查询 pending、提交回答、更新日程、重复回答、
      不存在 qa_id、非法 field_name 白名单拦截
"""
from backend.db.database import execute, query


def _create_schedule_with_illegal_qa(field_name="id"):
    """直接在库中构造一条日程与一个非法字段的 QA 记录"""
    sid = execute(
        """INSERT INTO schedules (name, duty_date, start_time, end_time, location)
           VALUES (?, '2026-03-15', '08:00', '12:00', '图书馆')""",
        ("测试用户",),
    )
    qa_id = execute(
        "INSERT INTO qa_records (schedule_id, question, field_name, status) VALUES (?, ?, ?, 'pending')",
        (sid, "非法字段测试", field_name),
    )
    return sid, qa_id


def test_qa_full_flow(client, mock_ai):
    """缺失字段 → 生成 QA → 查询待办 → 回答 → 更新日程 → QA 状态变更"""
    mock_ai("missing_time.json")
    resp = client.post("/api/upload/text", json={"text": "李四值班"})
    data = resp.get_json()["data"]
    questions = data["questions"]
    assert len(questions) == 2

    # pending 列表可查到
    pending = client.get("/api/qa/pending").get_json()
    assert pending["total"] == 2

    # 回答第一条：结束时间
    first = next(q for q in questions if q["field"] == "end_time")
    ans = client.post("/api/qa/answer", json={"qa_id": first["qa_id"], "answer": "13:30"})
    assert ans.status_code == 200
    assert ans.get_json()["code"] == 0

    schedule = client.get(f"/api/schedules/{first['schedule_id']}").get_json()["data"]
    assert schedule["end_time"] == "13:30"

    qa_row = query("SELECT * FROM qa_records WHERE id = ?", (first["qa_id"],), one=True)
    assert qa_row["status"] == "answered"
    assert qa_row["answer"] == "13:30"

    # 回答第二条：地点
    second = next(q for q in questions if q["field"] == "location")
    ans2 = client.post("/api/qa/answer", json={"qa_id": second["qa_id"], "answer": "图书馆二楼"})
    assert ans2.status_code == 200
    schedule2 = client.get(f"/api/schedules/{second['schedule_id']}").get_json()["data"]
    assert schedule2["location"] == "图书馆二楼"


def test_qa_answer_duplicate(client, mock_ai):
    """同一问题重复回答返回 400"""
    mock_ai("missing_time.json")
    data = client.post("/api/upload/text", json={"text": "李四值班"}).get_json()["data"]
    qa_id = data["questions"][0]["qa_id"]

    assert client.post("/api/qa/answer", json={"qa_id": qa_id, "answer": "12:00"}).status_code == 200
    dup = client.post("/api/qa/answer", json={"qa_id": qa_id, "answer": "13:00"})
    assert dup.status_code == 400


def test_qa_answer_not_found(client):
    """回答不存在的 qa_id 返回 404"""
    resp = client.post("/api/qa/answer", json={"qa_id": 999999, "answer": "x"})
    assert resp.status_code == 404
    assert resp.get_json()["code"] == 1


def test_qa_answer_missing_params(client):
    """缺少 qa_id 或 answer 返回 400"""
    assert client.post("/api/qa/answer", json={"answer": "x"}).status_code == 400
    assert client.post("/api/qa/answer", json={"qa_id": 1, "answer": ""}).status_code == 400


def test_qa_answer_illegal_field_rejected(client):
    """field_name 不在白名单（如 id）必须被拦截，且日程 id 不变"""
    sid, qa_id = _create_schedule_with_illegal_qa("id")
    resp = client.post("/api/qa/answer", json={"qa_id": qa_id, "answer": "999"})
    assert resp.status_code == 400
    assert resp.get_json()["code"] == 1

    row = query("SELECT id FROM schedules WHERE id = ?", (sid,), one=True)
    assert row is not None
    qa_row = query("SELECT status FROM qa_records WHERE id = ?", (qa_id,), one=True)
    assert qa_row["status"] == "pending"


def test_qa_answer_illegal_field_is_confirmed(client):
    """试图通过 QA 修改 is_confirmed 也必须被拦截"""
    _, qa_id = _create_schedule_with_illegal_qa("is_confirmed")
    resp = client.post("/api/qa/answer", json={"qa_id": qa_id, "answer": "1"})
    assert resp.status_code == 400
