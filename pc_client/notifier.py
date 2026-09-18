# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
Windows 桌面通知模块
使用 plyer 实现系统级桌面通知，并注册 AppUserModelID
（Windows 8.1+ 需注册应用 ID，通知才会正确显示应用名）
"""
import ctypes
import sys

try:
    from plyer import notification
except ImportError:
    notification = None  # 未安装 plyer 时降级：仅记录日志，不发送桌面通知

from backend.utils.logger import get_logger

logger = get_logger("pc_notify")

# 应用唯一标识（写入 Windows 注册表，用于通知归属）
APP_USER_MODEL_ID = "ScheduleExtractor.AI.ScheduleManager.1.0"


def _register_app_id():
    """注册 Windows AppUserModelID（仅 Windows 生效，失败不影响通知功能）"""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception as e:  # noqa: BLE001 - 通知可用性降级处理
        logger.warning("注册 Windows 通知应用ID失败: %s", e)


def send_notification(title: str, message: str, timeout: int = 10):
    """
    发送 Windows 桌面通知
    :param title: 通知标题
    :param message: 通知内容
    :param timeout: 通知显示时长（秒）
    """
    _register_app_id()
    if notification is None:
        logger.warning("plyer 未安装，跳过桌面通知：%s - %s", title, message)
        return
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="AI日程管理",
            app_icon=None,
            timeout=timeout,
        )
        logger.info("桌面通知已发送：%s", title)
    except Exception as e:
        logger.error("桌面通知发送失败：%s", e)


def send_schedule_reminder(name: str, duty_date: str, start_time: str, location: str, custom_message: str = ""):
    """
    发送日程提醒通知
    :param name: 日程名称/值班人姓名
    :param duty_date: 日期
    :param start_time: 开始时间
    :param location: 地点
    :param custom_message: 自定义提醒文案
    """
    title = "日程提醒"
    if custom_message:
        message = custom_message
    else:
        location_text = f" 在 {location}" if location else ""
        message = f"{name}，您于 {duty_date} {start_time}{location_text} 有日程安排，请提前准备。"

    send_notification(title, message)


def send_test_notification():
    """发送测试通知，验证通知功能是否正常"""
    send_notification(
        title="测试通知",
        message="AI日程管理已启动，通知功能正常工作！",
        timeout=5,
    )
