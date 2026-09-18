# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
AI 问答（待补充信息）REST API 路由
从 routes_reminder.py 中拆出，仅负责：
- GET  /api/qa/pending  查看待补充问题
- POST /api/qa/answer   提交回答并更新日程字段（白名单校验）
"""
from flask import Blueprint, request, jsonify

from backend.core import qa as qa_service

qa_bp = Blueprint("qa", __name__)


@qa_bp.route("/api/qa/pending", methods=["GET"])
def get_pending_questions():
    """获取待回答的 AI 提问"""
    rows = qa_service.get_pending_questions()
    return jsonify({"code": 0, "msg": "success", "data": rows, "total": len(rows)})


@qa_bp.route("/api/qa/answer", methods=["POST"])
def answer_question():
    """用户回答 AI 的提问，补充信息并更新对应日程"""
    data = request.get_json(silent=True) or {}
    qa_id = data.get("qa_id")
    answer = (data.get("answer") or "").strip()

    if not qa_id or not answer:
        return jsonify({"code": 1, "msg": "缺少问题ID或回答内容", "data": None}), 400

    result = qa_service.submit_answer(qa_id, answer)
    return jsonify({
        "code": 0 if result["success"] else 1,
        "msg": result["msg"],
        "data": result.get("data"),
    }), result["status"]
