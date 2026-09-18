# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""用户信息收集接口测试：创建、查询、openid 更新、不存在用户"""


def test_create_user(client):
    """创建用户成功"""
    resp = client.post("/api/users", json={
        "name": "张三",
        "openid": "wx_test_001",
        "student_id": "20260001",
        "phone": "13800000000",
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["name"] == "张三"
    assert body["data"]["openid"] == "wx_test_001"


def test_create_user_without_name(client):
    """缺少姓名返回 400"""
    resp = client.post("/api/users", json={"openid": "wx_no_name"})
    assert resp.status_code == 400


def test_get_user_by_openid(client):
    """按 openid 查询用户"""
    client.post("/api/users", json={"name": "李四", "openid": "wx_test_002"})
    resp = client.get("/api/users/wx_test_002")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["name"] == "李四"


def test_get_user_not_found(client):
    """查询不存在的用户返回 404"""
    resp = client.get("/api/users/wx_not_exist")
    assert resp.status_code == 404
    assert resp.get_json()["code"] == 1


def test_user_openid_upsert(client):
    """同一 openid 再次提交应更新而不是新增"""
    client.post("/api/users", json={"name": "王五", "openid": "wx_test_003"})
    resp = client.post("/api/users", json={"name": "王五新", "openid": "wx_test_003"})
    assert resp.status_code == 200
    assert resp.get_json()["data"]["name"] == "王五新"

    detail = client.get("/api/users/wx_test_003").get_json()["data"]
    assert detail["name"] == "王五新"

    # 数据库中该 openid 只有一条记录
    from backend.db.database import query
    rows = query("SELECT COUNT(*) AS c FROM users WHERE openid = ?", ("wx_test_003",))
    assert rows[0]["c"] == 1
