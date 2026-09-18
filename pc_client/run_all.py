# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
一键启动入口
同时启动 Flask 后端 + PySide6 PC 桌面客户端

使用方式：python run_all.py
"""
import threading
import subprocess
import sys
import os
import time

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def start_pc_client():
    """启动 PySide6 PC 桌面客户端（连接真实后端）"""
    env = dict(os.environ)
    env["USE_MOCK"] = "0"
    app_path = os.path.join(BASE_DIR, "pc_client", "app.py")
    subprocess.run([sys.executable, app_path], env=env)


def start_backend():
    """启动后端 Flask 服务"""
    app_path = os.path.join(BASE_DIR, "backend", "app.py")
    subprocess.run([sys.executable, app_path])


if __name__ == "__main__":
    print("=" * 50)
    print("  轻量化AI排班提取工具 v1.1 - 一键启动")
    print("=" * 50)

    # 1. 先启动后端（独立进程）
    print("\n[1/2] 启动后端服务...")
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    time.sleep(3)  # 等待后端初始化

    # 2. 启动 PySide6 PC 客户端（主线程，阻塞）
    print("[2/2] 启动 PySide6 PC 客户端（USE_MOCK=0）...")
    print("\n" + "=" * 50)
    print("  后端API:   http://localhost:5000")
    print("  PC 客户端: 桌面窗口")
    print("=" * 50 + "\n")

    try:
        start_pc_client()
    except KeyboardInterrupt:
        print("\n正在关闭...")
