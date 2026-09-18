# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
后台提醒轮询服务

在独立 QThread 中定时拉取提醒列表（GET /api/reminders），
到点触发 Windows 桌面通知，同一提醒只通知一次。

- 轮询间隔由环境变量 PC_NOTIFY_INTERVAL 控制（秒，默认 60）
- 提醒触发时刻 = 日程开始时间 - 提前分钟数
- remind_at / iter_due 为纯函数，便于单测
"""
import os
from datetime import datetime, timedelta

from PySide6.QtCore import QThread, Signal

from backend.utils.logger import get_logger

logger = get_logger("pc_notify_service")

DEFAULT_INTERVAL = int(os.getenv("PC_NOTIFY_INTERVAL", "60"))


def remind_at(row: dict) -> datetime | None:
    """
    计算提醒触发时刻：日程开始时间 - 提前分钟数。
    日期/时间缺失或格式非法时返回 None（不触发通知）。
    """
    duty_date = (row.get("duty_date") or "").strip()
    start_time = (row.get("start_time") or "").strip()
    if not duty_date or not start_time or ":" not in start_time:
        return None
    try:
        day = datetime.strptime(duty_date, "%Y-%m-%d")
        hour, minute = (int(x) for x in start_time.split(":")[:2])
        start = day.replace(hour=hour, minute=minute)
        return start - timedelta(minutes=int(row.get("advance_minutes") or 0))
    except (TypeError, ValueError):
        return None


def iter_due(reminders: list, now: datetime) -> list:
    """筛选出已到提醒时刻的提醒列表（纯函数，便于测试）"""
    due = []
    for row in reminders or []:
        at = remind_at(row)
        if at is not None and now >= at:
            due.append(row)
    return due


class NotificationWorker(QThread):
    """
    后台轮询线程

    - fetch_reminders: 可调用对象，返回提醒列表（如 ApiClient().get_reminders）
    - notify: 信号，携带 (标题, 内容)，由调用方连接到桌面通知槽
    """

    notify = Signal(str, str)

    def __init__(self, fetch_reminders, interval: int = DEFAULT_INTERVAL, parent=None):
        super().__init__(parent)
        self._fetch = fetch_reminders
        self._interval = max(int(interval), 5)
        # 已通知去重键：reminder_id@advance@date@time
        self._notified = set()

    # ===== 线程主体 =====

    def run(self):
        logger.info("提醒轮询已启动，间隔 %s 秒", self._interval)
        while not self.isInterruptionRequested():
            try:
                self._poll_once()
            except Exception as e:  # noqa: BLE001 - 轮询失败仅记录，不中断线程
                logger.warning("提醒轮询异常: %s", e)
            self.msleep(self._interval * 1000)
        logger.info("提醒轮询已停止")

    def _poll_once(self):
        rows = self._fetch() or []
        for row in iter_due(rows, datetime.now()):
            key = "{}@{}@{}@{}".format(
                row.get("id"), row.get("advance_minutes"),
                row.get("duty_date"), row.get("start_time"),
            )
            if key in self._notified:
                continue
            self._notified.add(key)
            title, message = self._build_message(row)
            logger.info("触发提醒：%s", title)
            self.notify.emit(title, message)

    @staticmethod
    def _build_message(row: dict):
        name = row.get("name") or "日程安排"
        duty_date = row.get("duty_date") or ""
        start_time = row.get("start_time") or ""
        location = (row.get("location") or "").strip()
        custom = (row.get("custom_message") or "").strip()
        if custom:
            message = custom
        else:
            location_text = f" 在 {location}" if location else ""
            message = f"{name}，您于 {duty_date} {start_time}{location_text} 有日程安排，请提前准备。"
        return f"日程提醒：{name}", message

    # ===== 生命周期 =====

    def stop(self):
        """请求停止轮询（配合 start() 使用）"""
        self.requestInterruption()
