# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
PySide6 PC 客户端入口

Phase 2：先以 MockProvider 预览界面（不依赖后端）。
Phase 3：切换为 ApiClient 接入真实 Flask API。
Phase 6：真实模式下后台启动提醒轮询（到点弹桌面通知）。
可通过环境变量 USE_MOCK=0 强制使用真实后端。
"""
import os
import sys

# 项目根目录加入导入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

from pc_client.services.api_client import ApiClient, MockProvider  # noqa: E402
from pc_client.ui.main_window import APP_QSS, MainWindow  # noqa: E402


def build_provider():
    """选择数据提供者：默认 Mock（Phase 2），USE_MOCK=0 时走真实后端"""
    use_mock = os.getenv("USE_MOCK", "1") != "0"
    if use_mock:
        print("[PC] 使用 Mock 数据预览模式（USE_MOCK=1）。连接真实后端请设置 USE_MOCK=0")
        return MockProvider()
    print("[PC] 连接后端 API ...")
    return ApiClient()


def start_notification_service(provider):
    """真实后端模式下启动提醒轮询线程；Mock 模式不启动"""
    if not isinstance(provider, ApiClient):
        return None
    from pc_client.notifier import send_notification
    from pc_client.services.notification_service import NotificationWorker

    worker = NotificationWorker(provider.get_reminders)
    worker.notify.connect(send_notification)
    worker.start()
    return worker


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)

    provider = build_provider()
    notify_worker = start_notification_service(provider)

    window = MainWindow(provider)
    window.show()

    code = app.exec()
    if notify_worker is not None:
        notify_worker.stop()
        notify_worker.wait(3000)
    sys.exit(code)


if __name__ == "__main__":
    main()
