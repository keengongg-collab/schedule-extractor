"""
日程相关 REST API 路由
提供日程的增删改查、确认、按姓名查询等接口
"""
from flask import Blueprint, request, jsonify
from backend.db.database import query, execute

# 创建蓝图
schedule_bp = Blueprint("schedule", __name__)


@schedule_bp.route("/api/schedules", methods=["GET"])
def get_schedules():
    """获取日程列表，支持按姓名筛选"""
    name = request.args.get("name", "").strip()

    if name:
        # 按姓名查询个人值班日程
        rows = query(
            "SELECT * FROM schedules WHERE name LIKE ? ORDER BY duty_date, start_time",
            (f"%{name}%",),
        )
    else:
        # 查询全部
        rows = query("SELECT * FROM schedules ORDER BY duty_date, start_time")

    return jsonify({"code": 0, "data": rows, "total": len(rows)})


@schedule_bp.route("/api/schedules/<int:schedule_id>", methods=["GET"])
def get_schedule_detail(schedule_id):
    """获取单条日程详情"""
    row = query("SELECT * FROM schedules WHERE id = ?", (schedule_id,), one=True)
    if not row:
        return jsonify({"code": 1, "msg": "日程不存在"}), 404
    return jsonify({"code": 0, "data": row})


@schedule_bp.route("/api/schedules", methods=["POST"])
def create_schedule():
    """手动新增日程"""
    data = request.get_json(force=True)
    # 必填字段校验
    if not data.get("name") or not data.get("duty_date"):
        return jsonify({"code": 1, "msg": "姓名和值班日期为必填项"}), 400

    schedule_id = execute(
        """INSERT INTO schedules (name, duty_date, start_time, end_time, location, remark, source_type, original_text)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("name"),
            data.get("duty_date"),
            data.get("start_time"),
            data.get("end_time"),
            data.get("location"),
            data.get("remark", ""),
            data.get("source_type", "manual"),
            data.get("original_text", ""),
        ),
    )
    return jsonify({"code": 0, "msg": "创建成功", "data": {"id": schedule_id}})


@schedule_bp.route("/api/schedules/<int:schedule_id>", methods=["PUT"])
def update_schedule(schedule_id):
    """更新日程信息（补充修改后调用）"""
    data = request.get_json(force=True)
    # 动态拼接更新字段
    fields = []
    values = []
    for key in ["name", "duty_date", "start_time", "end_time", "location", "remark", "is_confirmed"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])

    if not fields:
        return jsonify({"code": 1, "msg": "无更新字段"}), 400

    fields.append("updated_at = datetime('now','localtime')")
    values.append(schedule_id)

    execute(f"UPDATE schedules SET {', '.join(fields)} WHERE id = ?", tuple(values))
    return jsonify({"code": 0, "msg": "更新成功"})


@schedule_bp.route("/api/schedules/<int:schedule_id>", methods=["DELETE"])
def delete_schedule(schedule_id):
    """删除日程"""
    execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    return jsonify({"code": 0, "msg": "删除成功"})


@schedule_bp.route("/api/schedules/<int:schedule_id>/confirm", methods=["POST"])
def confirm_schedule(schedule_id):
    """确认日程（信息补充完毕后用户确认）"""
    execute("UPDATE schedules SET is_confirmed = 1, updated_at = datetime('now','localtime') WHERE id = ?", (schedule_id,))
    return jsonify({"code": 0, "msg": "已确认"})
