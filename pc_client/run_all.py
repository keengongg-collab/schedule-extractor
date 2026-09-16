# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
一键启动入口
同时启动 Streamlit 网页 + 划词监听插件

使用方式：python run_all.py
"""
import threading
import subprocess
import sys
import os
import time

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def start_streamlit():
    """启动 Streamlit 网页"""
    app_path = os.path.join(BASE_DIR, "pc_client", "app_streamlit.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])


def start_word_selector():
    """启动划词监听插件"""
    from pc_client.word_selector import WordSelector

    selector = WordSelector()
    selector.start()
    return selector


def start_backend():
    """启动后端 Flask 服务"""
    app_path = os.path.join(BASE_DIR, "backend", "app.py")
    subprocess.run([sys.executable, app_path])


if __name__ == "__main__":
    print("=" * 50)
    print("  轻量化AI排班提取工具 - 一键启动")
    print("=" * 50)

    # 1. 先启动后端（独立进程）
    print("\n[1/3] 启动后端服务...")
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    time.sleep(2)  # 等待后端初始化

    # 2. 启动划词插件（后台线程）
    print("[2/3] 启动划词插件...")
    try:
        selector = start_word_selector()
    except Exception as e:
        print(f"  划词插件启动失败（不影响网页功能）: {e}")
        selector = None

    # 3. 启动 Streamlit（主线程，阻塞）
    print("[3/3] 启动 Streamlit 网页...")
    print("\n" + "=" * 50)
    print("  Streamlit: http://localhost:8501")
    print("  后端API:   http://localhost:5000")
    print("  划词快捷键: Ctrl+Shift+D")
    print("=" * 50 + "\n")

    try:
        start_streamlit()
    except KeyboardInterrupt:
        print("\n正在关闭...")
        if selector:
            selector.stop()
