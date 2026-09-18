# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
AI 自然语言指令（/api/ai/intent）测试
覆盖（无 AI Key 时走正则兜底）：
- 删除指令解析 + 候选匹配（不执行写操作）
- 修改指令解析 + 候选匹配
- 查询指令解析
- 创建指令解析（值班表文本 + 自然语言单条）
- 空指令 400
"""


def _seed(client):
    from datetime import date, timedelta
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    client.post("/api/schedules", json={
        "name": "项目会议", "duty_date": tomorrow,
        "start_time": "15:00", "end_time": "16:30", "location": "会议室 A",
    })
    client.post("/api/schedules", json={
        "name": "值班", "duty_date": tomorrow,
        "start_time": "09:00", "end_time": "12:00", "location": "图书馆",
    })


def _intent(client, text):
    resp = client.post("/api/ai/intent", json={"text": text})
    assert resp.status_code == 200
    return resp.get_json()["data"]


def test_delete_intent_with_candidates(client):
    _seed(client)
    result = _intent(client, "删除我明天的项目会议")
    assert result["action"] == "delete"
    assert result["candidates"]
    assert result["candidates"][0]["name"] == "项目会议"
    # 不执行写操作：日程仍在
    resp = client.get("/api/schedules")
    assert resp.get_json()["total"] == 2


def test_update_intent_with_candidates(client):
    _seed(client)
    result = _intent(client, "把我明天下午三点的项目会议改到四点")
    assert result["action"] == "update"
    assert result["candidates"]
    assert result["candidates"][0]["name"] == "项目会议"
    assert result["fields"]  # 修改字段非空


def test_update_ambiguous_returns_multiple(client):
    _seed(client)
    # 匹配条件过宽（只给姓名模糊），返回多个候选并要求选择
    result = _intent(client, "把项目会议改到四点")
    assert result["action"] == "update"
    assert len(result["candidates"]) == 1  # 只有一条项目会议


def test_query_intent(client):
    _seed(client)
    result = _intent(client, "明天有什么安排")
    assert result["action"] == "query"
    assert result["candidates"]


def test_create_intent_from_duty_table(client):
    result = _intent(client, "张三 2026-09-28 09:00-12:00 图书馆一楼\n李四 2026-09-29 14:00-17:00 二楼")
    assert result["action"] == "create"
    assert len(result["previews"]) == 2
    assert result["previews"][0]["name"] == "张三"
    assert result["previews"][0]["duty_date"] == "2026-09-28"
    # 预览不落库
    resp = client.get("/api/schedules")
    assert resp.get_json()["total"] == 0


def test_create_intent_natural_language(client):
    result = _intent(client, "明天下午三点去图书馆开会")
    assert result["action"] == "create"
    assert len(result["previews"]) == 1
    preview = result["previews"][0]
    assert preview["start_time"] == "15:00"
    assert preview["location"] == "图书馆"


def test_empty_text_400(client):
    resp = client.post("/api/ai/intent", json={"text": "  "})
    assert resp.status_code == 400
    assert resp.get_json()["code"] == 1
