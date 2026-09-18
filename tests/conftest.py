# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
pytest 全局夹具

关键设计：
- 在导入任何 backend 模块之前，通过 SCHEDULE_DB_FILE 把数据库重定向到临时文件，
  实现测试与开发数据库完全隔离
- 默认不配置 AI_API_KEY，走正则兜底；需要 AI 的用例使用 mock_ai 夹具
"""
import json
import os
import sys
import tempfile
import pathlib

import pytest

# 项目根目录加入导入路径
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 必须在 import backend.* 之前设置：重定向数据库到临时目录
_TEST_DIR = tempfile.mkdtemp(prefix="schedule_extractor_test_")
os.environ["SCHEDULE_DB_FILE"] = os.path.join(_TEST_DIR, "test_schedule.db")
# 保证测试环境默认无真实 AI Key
os.environ.pop("AI_API_KEY", None)

from backend.app import create_app           # noqa: E402
from backend.db.database import execute      # noqa: E402
import backend.core.extractor as extractor   # noqa: E402

# 清表顺序：先子表后父表
_TABLES = [
    "chat_messages",
    "chat_sessions",
    "reminders",
    "qa_records",
    "schedules",
    "users",
    "parse_logs",
]

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def client():
    """Flask 测试客户端，每个用例前清空所有业务表"""
    app = create_app()
    app.config["TESTING"] = True
    for table in _TABLES:
        execute(f"DELETE FROM {table}")
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def mock_ai(monkeypatch):
    """
    模拟 AI 返回，不调用真实 API。
    用法：mock_ai('normal_schedule.json')
    """
    def _load(fixture_name):
        data = json.loads((FIXTURES_DIR / fixture_name).read_text(encoding="utf-8"))
        # 使 extract_schedules 进入 AI 分支
        monkeypatch.setattr(extractor, "AI_API_KEY", "test-key")
        # _call_ai_extract 约定返回"已结构校验+标准化"的列表
        monkeypatch.setattr(
            extractor,
            "_call_ai_extract",
            lambda text: extractor.clean_ai_payload(data),
        )
        return data

    return _load


@pytest.fixture
def mock_ai_bad_payload(monkeypatch):
    """模拟 AI 返回无法解析的内容（json.loads 失败）"""
    def _raise(text):
        raise extractor.ExtractionError("AI 返回的内容不是合法 JSON：test")
    monkeypatch.setattr(extractor, "AI_API_KEY", "test-key")
    monkeypatch.setattr(extractor, "_call_ai_extract", _raise)
    return _raise
