"""
Windows 桌面通知模块
使用 plyer 实现系统级桌面通知
"""
from plyer import notification
from datetime import datetime


def send_notification(title: str, message: str, timeout: int = 10):
    """
    发送 Windows 桌面通知
    :param title: 通知标题
    :param message: 通知内容
    :param timeout: 通知显示时长（秒）
    """
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="排班提醒助手",
            timeout=timeout,
        )
        print(f"[通知] {datetime.now().strftime('%H:%M:%S')} - {title}: {message}")
    except Exception as e:
        print(f"[通知] 发送失败: {e}")


def send_schedule_reminder(name: str, duty_date: str, start_time: str, location: str, custom_message: str = ""):
    """
    发送值班提醒通知
    :param name: 值班人姓名
    :param duty_date: 值班日期
    :param start_time: 开始时间
    :param location: 值班地点
    :param custom_message: 自定义提醒文案
    """
    title = "排班提醒"
    if custom_message:
        message = custom_message
    else:
        message = f"{name}，您于 {duty_date} {start_time} 在 {location} 有值班安排，请提前准备。"

    send_notification(title, message)


def send_test_notification():
    """发送测试通知，验证通知功能是否正常"""
    send_notification(
        title="测试通知",
        message="排班提醒助手已启动，通知功能正常工作！",
        timeout=5,
    )
