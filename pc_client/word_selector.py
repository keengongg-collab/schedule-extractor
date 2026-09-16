# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
划词插件模块
后台监听键盘快捷键，用户选中文字按快捷键捕获文本，
弹窗询问"是否添加日程？"，确认后调用后端 API 新增日程

实现方式：
- pynput 监听全局键盘事件（不占用鼠标）
- pyperclip 读取剪贴板（先模拟 Ctrl+C 复制选中文本）
- tkinter 弹窗确认
- requests 调用后端 API
"""
import threading
import time
import requests
import pyperclip
import tkinter as tk
from tkinter import messagebox
from pynput import keyboard

# 后端 API 地址
API_BASE = "http://127.0.0.1:5000"

# 触发快捷键组合：Ctrl + Shift + D
HOTKEY_COMBO = {keyboard.Key.ctrl_l, keyboard.Key.shift}
TARGET_KEY = 'd'


class WordSelector:
    """划词监听器"""

    def __init__(self):
        self.listener = None
        self.running = False
        self._pressed = set()  # 记录当前按下的键

    def start(self):
        """启动监听"""
        self.running = True
        self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self.listener.daemon = True
        self.listener.start()
        print("[划词插件] 已启动，选中文字后按 Ctrl+Shift+D 捕获排班文本")

    def stop(self):
        """停止监听"""
        self.running = False
        if self.listener:
            self.listener.stop()
        print("[划词插件] 已停止")

    def _on_press(self, key):
        """按键事件处理"""
        # 记录按下的修饰键
        if key in HOTKEY_COMBO:
            self._pressed.add(key)
            return

        # 检查是否按下了目标键 D 且修饰键都在按下状态
        try:
            if key.char and key.char.lower() == TARGET_KEY:
                if HOTKEY_COMBO.issubset(self._pressed):
                    self._capture_text()
        except AttributeError:
            pass

    def _on_release(self, key):
        """按键释放处理"""
        if key in self._pressed:
            self._pressed.discard(key)

    def _capture_text(self):
        """捕获选中文本"""
        # 方法：模拟 Ctrl+C 复制选中文本，然后读剪贴板
        # 注意：这里用 pynput 模拟复制，确保兼容性
        try:
            # 等待用户松开按键
            time.sleep(0.1)

            # 读取当前剪贴板内容（可能用户已经 Ctrl+C 复制了）
            selected_text = pyperclip.paste()

            if not selected_text or len(selected_text.strip()) < 2:
                # 尝试模拟 Ctrl+C
                with keyboard.Controller() as controller:
                    controller.press(keyboard.Key.ctrl)
                    controller.press('c')
                    controller.release('c')
                    controller.release(keyboard.Key.ctrl)
                time.sleep(0.15)
                selected_text = pyperclip.paste()

            if not selected_text or len(selected_text.strip()) < 2:
                print("[划词插件] 未捕获到有效文本")
                return

            selected_text = selected_text.strip()
            print(f"[划词插件] 捕获到文本: {selected_text[:50]}...")

            # 弹窗确认
            self._show_dialog(selected_text)

        except Exception as e:
            print(f"[划词插件] 捕获失败: {e}")

    def _show_dialog(self, text: str):
        """弹窗询问是否添加为日程"""
        # 在独立线程中显示弹窗，避免阻塞监听
        def dialog():
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            result = messagebox.askyesno(
                "添加排班日程",
                f"捕获到以下文本：\n\n{text[:200]}\n\n是否解析并添加为排班日程？",
            )
            root.destroy()

            if result:
                # 调用后端 API 解析并添加
                self._send_to_api(text)

        threading.Thread(target=dialog, daemon=True).start()

    def _send_to_api(self, text: str):
        """调用后端 API 解析文本"""
        try:
            resp = requests.post(
                f"{API_BASE}/api/upload/text",
                json={"text": text},
                timeout=30,
            )
            data = resp.json()
            if data.get("code") == 0:
                result = data.get("data", {})
                total = result.get("total", 0)
                questions = result.get("questions", [])
                msg = f"解析完成，共提取 {total} 条日程"
                if questions:
                    msg += f"，其中 {len(questions)} 条信息不完整，需要补充"
                print(f"[划词插件] {msg}")
            else:
                print(f"[划词插件] 解析失败: {data.get('msg')}")
        except requests.ConnectionError:
            print("[划词插件] 无法连接后端服务，请确保后端已启动")
        except Exception as e:
            print(f"[划词插件] API调用失败: {e}")


if __name__ == "__main__":
    # 单独运行可测试划词功能
    selector = WordSelector()
    selector.start()

    print("按 Ctrl+C 退出")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        selector.stop()
