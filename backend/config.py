# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
全局配置文件
所有可配置参数集中管理，优先从环境变量 / .env 读取，不硬编码环境差异。
"""
import os
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def _env_bool(key: str, default: bool = False) -> bool:
    """读取布尔型环境变量"""
    return os.environ.get(key, str(default)).strip().lower() in ("1", "true", "yes", "on")


# ===== 路径配置 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

# ===== 服务配置（均可通过环境变量覆盖）=====
# HOST 默认 0.0.0.0 以兼容小程序局域网真机调试；生产环境可用 .env 改为 127.0.0.1
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))
# DEBUG 默认关闭，开发时在 .env 中设置 DEBUG=true
DEBUG = _env_bool("DEBUG", False)
# 上传文件大小上限（MB），防止超大文件
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "10"))

# ===== AI 配置 =====
# 使用 OpenAI 兼容接口，可对接各类大模型（如 DeepSeek、通义千问等）
# 实际使用时在 .env 文件中配置，不硬编码到代码里，不提交真实 Key
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.deepseek.com/v1")
AI_MODEL = os.environ.get("AI_MODEL", "deepseek-chat")

# ===== PC 端默认 API 地址（Streamlit / 划词插件读取）=====
API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:5000")

# ===== 微信小程序配置 =====
# 订阅消息模板 ID（在微信公众平台配置）
WECHAT_TEMPLATE_ID = os.environ.get("WECHAT_TEMPLATE_ID", "")

# ===== 确保必要目录存在 =====
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
