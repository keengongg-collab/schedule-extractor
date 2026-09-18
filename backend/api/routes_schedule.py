# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
日程相关 REST API 路由
提供日程的增删改查、确认、按姓名查询等接口

约定：
- 所有响应统一为 {"code": 0/1, "msg": ..., "data": ...}
- 不存在的 ID 一律返回 404 + {"code": 1, "msg": "日程不存在", "data": null}
- 可更新字段以 validator.ALLOWED_UPDATE_FIELDS 白名单为准
"""
from flask import Blueprint, request, jsonify

from backend.db.database import query, execute
from backend.core.validator import ALLOWED_UPDATE_FIELDS
from backend.utils.logger import get_logger

# 创建蓝图
schedule_bp = Blueprint("schedule", __name__)
logger = get_logger("schedule")


def _not_found():
    return jsonify({"code": 1, "msg": "日程不存在", "data": None}), 404


@schedule_bp.route("/api/schedules", methods=["GET"])
def get_schedules():
    """获取日程列表，支持按姓名筛选"""
    name = (request.args.get("name") or "").strip()

    if name:
        # 按姓名查询个人值班日程
        rows = query(
            "SELECT * FROM schedules WHERE name LIKE ? ORDER BY duty_date, start_time",
            (f"%{name}%",),
        )
    else:
        # 查询全部
        rows = query("SELECT * FROM schedules ORDER BY duty_date, start_time")

    return jsonify({"code": 0, "msg": "success", "data": rows, "total": len(rows)})


@schedule_bp.route("/api/schedules/<int:schedule_id>", methods=["GET"])
def get_schedule_detail(schedule_id):
    """获取单条日程详情"""
    row = query("SELECT * FROM schedules WHERE id = ?", (schedule_id,), one=True)
    if not row:
        return _not_found()
    return jsonify({"code": 0, "msg": "success", "data": row})


@schedule_bp.route("/api/schedules", methods=["POST"])
def create_schedule():
    """手动新增日程（姓名、值班日期必填，其余可后补）"""
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    duty_date = (data.get("duty_date") or "").strip()
    if not name or not duty_date:
        return jsonify({"code": 1, "msg": "姓名和值班日期为必填项", "data": None}), 400

    schedule_id = execute(
        """INSERT INTO schedules (name, duty_date, start_time, end_time, location, remark, source_type, original_text)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            name,
            duty_date,
            (data.get("start_time") or "").strip() or None,
            (data.get("end_time") or "").strip() or None,
            (data.get("location") or "").strip() or None,
            (data.get("remark") or "").strip(),
            data.get("source_type", "manual"),
            (data.get("original_text") or "").strip(),
        ),
    )
    logger.info("手动创建日程 id=%s name=%s date=%s", schedule_id, name, duty_date)
    return jsonify({"code": 0, "msg": "创建成功", "data": {"id": schedule_id}}), 201


@schedule_bp.route("/api/schedules/<int:schedule_id>", methods=["PUT"])
def update_schedule(schedule_id):
    """更新日程信息（补充修改后调用）"""
    row = query("SELECT id FROM schedules WHERE id = ?", (schedule_id,), one=True)
    if not row:
        return _not_found()

    data = request.get_json(silent=True) or {}

    # 动态拼接更新字段，仅允许白名单字段
    fields, values = [], []
    for key in ALLOWED_UPDATE_FIELDS:
        if key in data:
            if key == "is_confirmed":
                values.append(1 if data[key] else 0)
            else:
                values.append(("" if data[key] is None else str(data[key])).strip())
            fields.append(f"{key} = ?")

    if not fields:
        return jsonify({"code": 1, "msg": "无有效更新字段", "data": None}), 400

    fields.append("updated_at = datetime('now','localtime')")
    values.append(schedule_id)

    execute(f"UPDATE schedules SET {', '.join(fields)} WHERE id = ?", tuple(values))
    logger.info("日程已更新 id=%s 字段=%s", schedule_id, [f.split(" ")[0] for f in fields[:-1]])
    return jsonify({"code": 0, "msg": "更新成功", "data": {"id": schedule_id}})


@schedule_bp.route("/api/schedules/<int:schedule_id>", methods=["DELETE"])
def delete_schedule(schedule_id):
    """删除日程（关联的 QA/提醒通过外键级联删除）"""
    row = query("SELECT id FROM schedules WHERE id = ?", (schedule_id,), one=True)
    if not row:
        return _not_found()

    execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    logger.info("日程已删除 id=%s", schedule_id)
    return jsonify({"code": 0, "msg": "删除成功", "data": None})


@schedule_bp.route("/api/schedules/<int:schedule_id>/confirm", methods=["POST"])
def confirm_schedule(schedule_id):
    """确认日程（信息补充完毕后用户确认）"""
    row = query("SELECT id FROM schedules WHERE id = ?", (schedule_id,), one=True)
    if not row:
        return _not_found()

    execute(
        "UPDATE schedules SET is_confirmed = 1, updated_at = datetime('now','localtime') WHERE id = ?",
        (schedule_id,),
    )
    logger.info("日程已确认 id=%s", schedule_id)
    return jsonify({"code": 0, "msg": "已确认", "data": {"id": schedule_id}})
