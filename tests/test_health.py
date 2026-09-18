# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""健康检查接口测试"""


def test_health_ok(client):
    """GET /api/health 返回 200 与版本信息"""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["version"] == "1.0.0"
