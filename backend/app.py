# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
Flask 应用入口
启动后端服务，注册所有 API 蓝图
"""
import os
import sys

# 将项目根目录加入 Python 路径，方便 from backend.xxx 导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_cors import CORS

from backend.config import HOST, PORT, DEBUG
from backend.db.database import init_db
from backend.api.routes_schedule import schedule_bp
from backend.api.routes_upload import upload_bp
from backend.api.routes_reminder import reminder_bp
from backend.api.routes_user import user_bp


def create_app():
    """创建 Flask 应用，注册蓝图"""
    app = Flask(__name__)
    # 允许跨域访问（小程序和PC端都需要）
    CORS(app)

    # 注册 API 蓝图
    app.register_blueprint(schedule_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(reminder_bp)
    app.register_blueprint(user_bp)

    # 健康检查接口
    @app.route("/api/health")
    def health_check():
        return {"code": 0, "msg": "服务正常运行", "data": {"version": "1.0.0"}}

    return app


if __name__ == "__main__":
    # 初始化数据库
    init_db()

    # 创建并启动应用
    app = create_app()
    print(f"\n{'='*50}")
    print(f"  轻量化AI排班提取工具 - 后端服务")
    print(f"  访问地址: http://127.0.0.1:{PORT}")
    print(f"  API文档: http://127.0.0.1:{PORT}/api/health")
    print(f"{'='*50}\n")

    app.run(host=HOST, port=PORT, debug=DEBUG)
