# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
统一日志工具
关键流程（上传、解析、AI 请求/返回、日程与 QA 变更、API 异常）均通过此 logger 记录。

日志安全：只记录业务摘要，禁止记录 API Key、完整隐私文本。
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from backend.config import DATA_DIR

_LOG_DIR = os.path.join(DATA_DIR, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_configured = False


def _configure_root():
    """配置根 logger（仅一次），同时输出到控制台与滚动文件"""
    global _configured
    if _configured:
        return

    root = logging.getLogger("schedule_extractor")
    root.setLevel(logging.INFO)

    formatter = logging.Formatter(_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    try:
        file_handler = RotatingFileHandler(
            os.path.join(_LOG_DIR, "app.log"),
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # 文件日志不可用时仅使用控制台，不影响业务
        pass

    root.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """获取业务 logger"""
    _configure_root()
    return logging.getLogger(f"schedule_extractor.{name}")
