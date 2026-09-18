# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
AI 自然语言指令路由
POST /api/ai/intent：解析用户指令 → 返回结构化预览（绝不直接写库，
增删改由 PC 端在用户确认后调用 schedules API 执行）
"""
from flask import Blueprint, request, jsonify

from backend.core.ai_intent import resolve_intent
from backend.utils.logger import get_logger

ai_bp = Blueprint("ai", __name__)
logger = get_logger("ai")


@ai_bp.route("/api/ai/intent", methods=["POST"])
def ai_intent():
    """解析自然语言指令：{text: "..."} → {action, previews/candidates, ambiguous, msg}"""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"code": 1, "msg": "请输入指令", "data": None}), 400

    try:
        result = resolve_intent(text)
        logger.info("意图解析 action=%s 指令长度=%d", result.get("action"), len(text))
        return jsonify({"code": 0, "msg": "success", "data": result})
    except Exception as e:
        logger.exception("意图解析失败")
        return jsonify({"code": 1, "msg": f"意图解析失败: {e}", "data": None}), 500
