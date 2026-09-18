# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""提醒轮询纯函数测试：remind_at 计算与到点筛选（不依赖 Qt 事件循环）"""
from datetime import datetime

from pc_client.services.notification_service import iter_due, remind_at


def test_remind_at_normal():
    """常规：日程开始时间 - 提前分钟数"""
    row = {"duty_date": "2026-09-20", "start_time": "09:00", "advance_minutes": 30}
    assert remind_at(row) == datetime(2026, 9, 20, 8, 30)


def test_remind_at_zero_advance():
    """提前 0 分钟：即为开始时间"""
    row = {"duty_date": "2026-09-20", "start_time": "09:30", "advance_minutes": 0}
    assert remind_at(row) == datetime(2026, 9, 20, 9, 30)


def test_remind_at_missing_fields():
    """缺少日期/时间字段时返回 None"""
    assert remind_at({"duty_date": "2026-09-20", "start_time": ""}) is None
    assert remind_at({"duty_date": "", "start_time": "09:00"}) is None


def test_remind_at_invalid_values():
    """非法日期/时间/提前量返回 None"""
    assert remind_at({"duty_date": "2026-13-99", "start_time": "09:00", "advance_minutes": 30}) is None
    assert remind_at({"duty_date": "2026-09-20", "start_time": "xx:yy", "advance_minutes": 30}) is None
    assert remind_at({"duty_date": "2026-09-20", "start_time": "09:00", "advance_minutes": "abc"}) is None


def test_iter_due_selects_only_due():
    """只返回已到提醒时刻的提醒，未到的排除"""
    now = datetime(2026, 9, 20, 8, 20)
    reminders = [
        {"id": 1, "duty_date": "2026-09-20", "start_time": "08:30", "advance_minutes": 15},   # 8:15 已到
        {"id": 2, "duty_date": "2026-09-20", "start_time": "09:00", "advance_minutes": 15},   # 8:45 未到
        {"id": 3, "duty_date": "2026-09-21", "start_time": "08:00", "advance_minutes": 60},   # 明天未到
        {"id": 4, "duty_date": "2026-09-20", "start_time": "10:00"},                          # 无提前量=10:00 未到
    ]
    due = iter_due(reminders, now)
    assert [r["id"] for r in due] == [1]
