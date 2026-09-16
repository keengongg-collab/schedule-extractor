# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
提醒配置相关接口
管理日程提醒设置，支持自定义提前时长和提醒文案
"""
from flask import Blueprint, request, jsonify
from backend.db.database import query, execute

reminder_bp = Blueprint("reminder", __name__)


@reminder_bp.route("/api/reminders", methods=["GET"])
def get_reminders():
    """获取提醒列表"""
    rows = query(
        """SELECT r.*, s.name, s.duty_date, s.start_time, s.location
           FROM reminders r
           LEFT JOIN schedules s ON r.schedule_id = s.id
           WHERE r.is_active = 1
           ORDER BY s.duty_date, s.start_time"""
    )
    return jsonify({"code": 0, "data": rows, "total": len(rows)})


@reminder_bp.route("/api/reminders", methods=["POST"])
def create_reminder():
    """创建提醒配置"""
    data = request.get_json(force=True)
    schedule_id = data.get("schedule_id")

    if not schedule_id:
        return jsonify({"code": 1, "msg": "缺少日程ID"}), 400

    reminder_id = execute(
        """INSERT INTO reminders (schedule_id, advance_minutes, custom_message, is_active)
           VALUES (?, ?, ?, 1)""",
        (schedule_id, data.get("advance_minutes", 15), data.get("custom_message", "")),
    )
    return jsonify({"code": 0, "msg": "提醒已创建", "data": {"id": reminder_id}})


@reminder_bp.route("/api/reminders/<int:reminder_id>", methods=["PUT"])
def update_reminder(reminder_id):
    """更新提醒配置（修改提前时长或文案）"""
    data = request.get_json(force=True)
    fields = []
    values = []
    for key in ["advance_minutes", "custom_message", "is_active"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])

    if not fields:
        return jsonify({"code": 1, "msg": "无更新字段"}), 400

    values.append(reminder_id)
    execute(f"UPDATE reminders SET {', '.join(fields)} WHERE id = ?", tuple(values))
    return jsonify({"code": 0, "msg": "更新成功"})


@reminder_bp.route("/api/reminders/<int:reminder_id>", methods=["DELETE"])
def delete_reminder(reminder_id):
    """删除提醒配置"""
    execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    return jsonify({"code": 0, "msg": "已删除"})


@reminder_bp.route("/api/qa/pending", methods=["GET"])
def get_pending_questions():
    """获取待回答的AI提问"""
    rows = query(
        """SELECT q.*, s.name, s.duty_date, s.start_time
           FROM qa_records q
           LEFT JOIN schedules s ON q.schedule_id = s.id
           WHERE q.status = 'pending'"""
    )
    return jsonify({"code": 0, "data": rows, "total": len(rows)})


@reminder_bp.route("/api/qa/answer", methods=["POST"])
def answer_question():
    """用户回答AI的提问，补充信息后重新解析"""
    data = request.get_json(force=True)
    qa_id = data.get("qa_id")
    answer = data.get("answer", "").strip()

    if not qa_id or not answer:
        return jsonify({"code": 1, "msg": "缺少问题ID或回答内容"}), 400

    # 更新问答记录
    execute("UPDATE qa_records SET answer = ?, status = 'answered' WHERE id = ?", (answer, qa_id))

    # 获取问答详情，更新对应日程
    qa = query("SELECT * FROM qa_records WHERE id = ?", (qa_id,), one=True)
    if qa and qa.get("field_name"):
        # 根据字段名更新日程
        field = qa["field_name"]
        execute(
            f"UPDATE schedules SET {field} = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (answer, qa["schedule_id"]),
        )

    return jsonify({"code": 0, "msg": "回答已提交，日程已更新"})
