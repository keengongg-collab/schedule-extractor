"""
全局配置文件
所有可配置参数集中管理，避免硬编码
"""
import os
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# ===== 路径配置 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

# ===== 服务配置 =====
HOST = "0.0.0.0"          # 监听地址，0.0.0.0 允许外部访问（小程序调试需要）
PORT = 5000                # 服务端口
DEBUG = True               # 调试模式

# ===== AI 配置 =====
# 使用 OpenAI 兼容接口，可对接各类大模型（如 DeepSeek、通义千问等）
# 实际使用时在 .env 文件中配置，不硬编码到代码里
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.deepseek.com/v1")
AI_MODEL = os.environ.get("AI_MODEL", "deepseek-chat")

# ===== 微信小程序配置 =====
# 订阅消息模板 ID（在微信公众平台配置）
WECHAT_TEMPLATE_ID = os.environ.get("WECHAT_TEMPLATE_ID", "")

# ===== 确保必要目录存在 =====
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
