# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
对话智能体 REST API 路由
提供聊天入口、历史记录、会话重置接口
"""
from flask import Blueprint, request, jsonify

from backend.core.agent import handle_message, start_session, get_history, reset_session

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/api/chat/start", methods=["GET"])
def chat_start():
    """打开聊天页时调用，返回欢迎语与用户登记状态"""
    session_id = (request.args.get("session_id") or "").strip()
    openid = (request.args.get("openid") or "").strip() or None
    if not session_id:
        return jsonify({"code": 1, "msg": "缺少 session_id"}), 400
    return jsonify({"code": 0, "data": start_session(session_id, openid)})


@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    """发送一条消息给智能体"""
    data = request.get_json(silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    text = data.get("text") or ""
    openid = (data.get("openid") or "").strip() or None
    if not session_id:
        return jsonify({"code": 1, "msg": "缺少 session_id", "data": None}), 400
    return jsonify({"code": 0, "msg": "success", "data": handle_message(session_id, text, openid)})


@chat_bp.route("/api/chat/history", methods=["GET"])
def chat_history():
    """获取对话历史"""
    session_id = (request.args.get("session_id") or "").strip()
    limit = int(request.args.get("limit", 50))
    if not session_id:
        return jsonify({"code": 1, "msg": "缺少 session_id"}), 400
    return jsonify({"code": 0, "data": get_history(session_id, limit)})


@chat_bp.route("/api/chat/reset", methods=["POST"])
def chat_reset():
    """重置会话"""
    data = request.get_json(silent=True) or {}
    session_id = (data.get("session_id") or "").strip()
    if not session_id:
        return jsonify({"code": 1, "msg": "缺少 session_id", "data": None}), 400
    reset_session(session_id)
    return jsonify({"code": 0, "msg": "会话已重置", "data": None})
