# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
提醒配置相关接口
管理日程提醒设置，支持自定义提前时长和提醒文案

注意：AI 待补充问答接口已拆至 routes_qa.py（/api/qa/*），
本蓝图只保留 /api/reminders/* 提醒功能。
"""
from flask import Blueprint, request, jsonify

from backend.db.database import query, execute
from backend.utils.logger import get_logger

reminder_bp = Blueprint("reminder", __name__)
logger = get_logger("reminder")

# 允许通过 API 修改的提醒字段白名单
_UPDATABLE = {"advance_minutes", "custom_message", "is_active"}


def _schedule_exists(schedule_id) -> bool:
    return query("SELECT id FROM schedules WHERE id = ?", (schedule_id,), one=True) is not None


def _reminder_not_found():
    return jsonify({"code": 1, "msg": "提醒配置不存在", "data": None}), 404


@reminder_bp.route("/api/reminders", methods=["GET"])
def get_reminders():
    """获取提醒列表（可按 schedule_id 筛选）"""
    schedule_id = request.args.get("schedule_id")
    if schedule_id:
        rows = query(
            """SELECT r.*, s.name, s.duty_date, s.start_time, s.location
               FROM reminders r
               LEFT JOIN schedules s ON r.schedule_id = s.id
               WHERE r.schedule_id = ?
               ORDER BY s.duty_date, s.start_time""",
            (schedule_id,),
        )
    else:
        rows = query(
            """SELECT r.*, s.name, s.duty_date, s.start_time, s.location
               FROM reminders r
               LEFT JOIN schedules s ON r.schedule_id = s.id
               WHERE r.is_active = 1
               ORDER BY s.duty_date, s.start_time"""
        )
    return jsonify({"code": 0, "msg": "success", "data": rows, "total": len(rows)})


@reminder_bp.route("/api/reminders", methods=["POST"])
def create_reminder():
    """创建提醒配置（关联日程必须存在）"""
    data = request.get_json(silent=True) or {}
    schedule_id = data.get("schedule_id")

    if not schedule_id:
        return jsonify({"code": 1, "msg": "缺少日程ID", "data": None}), 400
    if not _schedule_exists(schedule_id):
        return jsonify({"code": 1, "msg": "关联的日程不存在", "data": None}), 404

    # 提前分钟数做整数校验
    try:
        advance = int(data.get("advance_minutes", 15))
        if advance < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"code": 1, "msg": "提前提醒分钟数必须是非负整数", "data": None}), 400

    reminder_id = execute(
        """INSERT INTO reminders (schedule_id, advance_minutes, custom_message, is_active)
           VALUES (?, ?, ?, 1)""",
        (schedule_id, advance, (data.get("custom_message") or "").strip()),
    )
    logger.info("提醒已创建 id=%s schedule_id=%s 提前%s分钟", reminder_id, schedule_id, advance)
    return jsonify({
        "code": 0, "msg": "提醒已创建",
        "data": {"id": reminder_id},
    }), 201


@reminder_bp.route("/api/reminders/<int:reminder_id>", methods=["PUT"])
def update_reminder(reminder_id):
    """更新提醒配置（修改提前时长或文案）"""
    if not query("SELECT id FROM reminders WHERE id = ?", (reminder_id,), one=True):
        return _reminder_not_found()

    data = request.get_json(silent=True) or {}
    fields, values = [], []
    for key in _UPDATABLE:
        if key in data:
            if key == "advance_minutes":
                try:
                    val = int(data[key])
                    if val < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    return jsonify({"code": 1, "msg": "提前提醒分钟数必须是非负整数", "data": None}), 400
            elif key == "is_active":
                val = 1 if data[key] else 0
            else:
                val = (data[key] or "").strip()
            fields.append(f"{key} = ?")
            values.append(val)

    if not fields:
        return jsonify({"code": 1, "msg": "无有效更新字段", "data": None}), 400

    values.append(reminder_id)
    execute(f"UPDATE reminders SET {', '.join(fields)} WHERE id = ?", tuple(values))
    logger.info("提醒已更新 id=%s 字段=%s", reminder_id, [f.split(" ")[0] for f in fields])
    return jsonify({"code": 0, "msg": "更新成功", "data": {"id": reminder_id}})


@reminder_bp.route("/api/reminders/<int:reminder_id>", methods=["DELETE"])
def delete_reminder(reminder_id):
    """删除提醒配置"""
    if not query("SELECT id FROM reminders WHERE id = ?", (reminder_id,), one=True):
        return _reminder_not_found()

    execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    logger.info("提醒已删除 id=%s", reminder_id)
    return jsonify({"code": 0, "msg": "已删除", "data": None})
