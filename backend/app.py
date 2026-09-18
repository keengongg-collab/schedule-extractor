# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
Flask 应用入口
启动后端服务，注册所有 API 蓝图

v1.0：
- 数据库初始化集中在 create_app() 中完成（首次启动自动建库）
- 统一错误响应格式 {"code": 1, "msg": ..., "data": null}
- 通过 MAX_CONTENT_LENGTH 限制上传文件大小
"""
import os
import sys

# 将项目根目录加入 Python 路径，方便 from backend.xxx 导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from backend.config import HOST, PORT, DEBUG, MAX_UPLOAD_MB
from backend.db.database import init_db
from backend.api.routes_schedule import schedule_bp
from backend.api.routes_upload import upload_bp
from backend.api.routes_reminder import reminder_bp
from backend.api.routes_user import user_bp
from backend.api.routes_chat import chat_bp
from backend.api.routes_qa import qa_bp
from backend.utils.logger import get_logger

logger = get_logger("app")


def _error_payload(msg, data=None):
    return {"code": 1, "msg": msg, "data": data}


def create_app():
    """创建 Flask 应用：初始化数据库、注册蓝图与统一错误处理"""
    # 集中初始化数据库（首次启动自动创建 SQLite 与表结构）
    init_db()

    app = Flask(__name__)
    # 允许跨域访问（小程序和PC端都需要）
    CORS(app)

    # 上传文件大小限制
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

    # 注册 API 蓝图
    app.register_blueprint(schedule_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(reminder_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(qa_bp)

    # 健康检查接口
    @app.route("/api/health")
    def health_check():
        return jsonify({
            "code": 0,
            "msg": "服务正常运行",
            "data": {"version": "1.0.0"},
        })

    # ===== 统一错误处理（所有错误返回同一 JSON 结构）=====

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(_error_payload(getattr(e, "description", "请求参数错误"))), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(_error_payload("资源不存在")), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify(_error_payload("请求方法不允许")), 405

    @app.errorhandler(413)
    def file_too_large(e):
        return jsonify(_error_payload(f"上传文件过大，最大允许 {MAX_UPLOAD_MB}MB")), 413

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("服务器内部错误")
        return jsonify(_error_payload("服务器内部错误")), 500

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        # HTTP 异常交给对应默认处理器（避免覆盖上面的状态码语义）
        if isinstance(e, HTTPException):
            return jsonify(_error_payload(e.description)), e.code
        logger.exception("未捕获异常")
        return jsonify(_error_payload(f"服务器内部错误: {e}")), 500

    return app


if __name__ == "__main__":
    # 创建并启动应用（create_app 内部已完成数据库初始化）
    app = create_app()
    print(f"\n{'='*50}")
    print(f"  轻量化AI排班提取工具 - 后端服务")
    print(f"  访问地址: http://{HOST}:{PORT}  (DEBUG={DEBUG})")
    print(f"  健康检查: http://{HOST}:{PORT}/api/health")
    print(f"{'='*50}\n")

    app.run(host=HOST, port=PORT, debug=DEBUG)
