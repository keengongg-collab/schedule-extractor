# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
用户信息与关键词识别 REST API 路由
1. 用户信息收集：提交/查询用户预收集的个人信息（姓名等）
2. 关键词识别：从用户输入中识别预收集的姓名，实现自动关联
3. 值班表可视化数据：按日期分组、计算值班时长比例
"""
import re
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify

from backend.db.database import query, execute
from backend.core.models import User

# 创建蓝图
user_bp = Blueprint("user", __name__)


# ===== 用户信息收集 =====

@user_bp.route("/api/users", methods=["POST"])
def create_user():
    """提交用户信息（预收集阶段）"""
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"code": 1, "msg": "姓名为必填项"}), 400

    openid = (data.get("openid") or "").strip() or None

    # 若同一 openid 已存在则更新，否则新增
    existing = None
    if openid:
        existing = query("SELECT * FROM users WHERE openid = ?", (openid,), one=True)

    if existing:
        user_id = existing["id"]
        execute(
            """UPDATE users SET name = ?, student_id = ?, phone = ?, remark = ?,
               updated_at = datetime('now','localtime') WHERE id = ?""",
            (name, data.get("student_id"), data.get("phone"), data.get("remark", ""), user_id),
        )
    else:
        user_id = execute(
            """INSERT INTO users (name, openid, student_id, phone, remark)
               VALUES (?, ?, ?, ?, ?)""",
            (name, openid, data.get("student_id"), data.get("phone"), data.get("remark", "")),
        )

    user = query("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    return jsonify({"code": 0, "msg": "保存成功", "data": User.from_db_row(user).to_dict()})


@user_bp.route("/api/users/<string:openid>", methods=["GET"])
def get_user_by_openid(openid):
    """按 openid 查询用户信息"""
    row = query("SELECT * FROM users WHERE openid = ?", (openid,), one=True)
    if not row:
        return jsonify({"code": 1, "msg": "用户未注册"}), 404
    return jsonify({"code": 0, "data": User.from_db_row(row).to_dict()})


# ===== 关键词识别系统 =====

# 中文姓名识别正则：常见姓 + 1~2 个字（宽松匹配）
_CN_NAME_PATTERN = re.compile(r"[\u4e00-\u9fa5]{2,4}")


def recognize_name_from_text(text: str) -> list:
    """
    从用户输入中提取疑似中文姓名。
    优先匹配"我是XX""我叫XX"等主语句式，其次匹配预收集用户库中的姓名。
    返回命中的用户列表（与预收集信息关联）。
    """
    if not text:
        return []

    # 1. 主语句式优先："我是张三" / "我叫李四" / "我是社团的王五"
    first_person = re.search(r"(?:我是|我叫|本人是|本人)[的]?([\u4e00-\u9fa5]{2,4})", text)
    candidates = []
    if first_person:
        candidates.append(first_person.group(1))

    # 2. 全量提取候选姓名
    candidates += _CN_NAME_PATTERN.findall(text)

    # 3. 与预收集用户库比对（去掉重复）
    seen = set()
    matched_users = []
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        row = query("SELECT * FROM users WHERE name = ?", (cand,), one=True)
        if row:
            matched_users.append(User.from_db_row(row).to_dict())
            # 命中预收集用户后即可返回，避免误匹配
            break
    return matched_users


@user_bp.route("/api/users/recognize", methods=["POST"])
def recognize_user():
    """
    关键词识别接口：
    输入如"我是张三，我把一个组的值班表发上去"，
    自动识别"张三"为用户标识，并关联到预收集的用户信息。
    """
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"code": 1, "msg": "文本内容为空"}), 400

    matched = recognize_name_from_text(text)

    if not matched:
        # 未命中预收集用户：返回候选姓名列表，提示用户先完成信息收集
        candidates = list(dict.fromkeys(_CN_NAME_PATTERN.findall(text)))[:5]
        return jsonify({
            "code": 0,
            "matched": False,
            "msg": "未匹配到已登记用户，请先完善个人信息或确认姓名",
            "data": {
                "user": None,
                "candidates": candidates,
            },
        })

    user = matched[0]
    return jsonify({
        "code": 0,
        "matched": True,
        "msg": f"已识别用户：{user['name']}",
        "data": {
            "user": user,
            # 关联该用户的个人排班
            "schedules": query(
                "SELECT * FROM schedules WHERE name = ? ORDER BY duty_date, start_time",
                (user["name"],),
            ),
        },
    })


# ===== 值班表可视化数据 =====

def _parse_time(t: str):
    """解析 HH:MM 时间为分钟数，非法返回 None"""
    try:
        h, m = t.split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def _weekday_cn(d: str) -> str:
    """日期转周几中文，如 2026-09-14 -> 周一"""
    try:
        dt = datetime.strptime(d, "%Y-%m-%d")
        return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][dt.weekday()]
    except ValueError:
        return ""


@user_bp.route("/api/schedules/visual", methods=["GET"])
def get_visual_data():
    """
    值班表可视化数据接口：
    返回按日期（周）分组的日程，附带每个日程的时长（分钟）与
    相对当天最大时长的比例（0~1），供前端纵向高度绘制。
    参数：?days=7 控制显示天数（默认7天）
    """
    days = int(request.args.get("days", 7))
    name = (request.args.get("name") or "").strip()

    # 计算起始日期：最近一周
    today = datetime.now().date()
    start_date = today - timedelta(days=days - 1)

    if name:
        rows = query(
            """SELECT * FROM schedules WHERE name LIKE ? AND duty_date >= ?
               ORDER BY duty_date, start_time""",
            (f"%{name}%", start_date.strftime("%Y-%m-%d")),
        )
    else:
        rows = query(
            "SELECT * FROM schedules WHERE duty_date >= ? ORDER BY duty_date, start_time",
            (start_date.strftime("%Y-%m-%d"),),
        )

    # 按日期分组
    day_map = {}
    for r in rows:
        d = r["duty_date"]
        day_map.setdefault(d, []).append(r)

    # 生成连续的日期列（保证横向表头完整）
    columns = []
    for i in range(days):
        d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        items = []
        for r in day_map.get(d, []):
            start_min = _parse_time(r["start_time"])
            end_min = _parse_time(r["end_time"])
            duration = 0
            if start_min is not None and end_min is not None and end_min > start_min:
                duration = end_min - start_min
            items.append({
                "id": r["id"],
                "name": r["name"],
                "start_time": r["start_time"],
                "end_time": r["end_time"],
                "location": r["location"],
                "duration": duration,          # 时长（分钟）
                "is_confirmed": bool(r["is_confirmed"]),
            })
        columns.append({
            "date": d,
            "weekday": _weekday_cn(d),
            "items": items,
            "count": len(items),
        })

    # 计算全局最大时长，用于跨天一致缩放
    max_duration = 0
    for col in columns:
        for it in col["items"]:
            max_duration = max(max_duration, it["duration"])

    # 计算每条的相对高度比例（0~1），无时间则给默认 0.15
    for col in columns:
        for it in col["items"]:
            if max_duration > 0 and it["duration"] > 0:
                it["ratio"] = round(it["duration"] / max_duration, 3)
            else:
                it["ratio"] = 0.15

    return jsonify({
        "code": 0,
        "data": {
            "columns": columns,
            "max_duration": max_duration,
            "scale_unit": "比例=时长/最大时长" if max_duration > 0 else "暂无时长数据",
        },
        "total": sum(c["count"] for c in columns),
    })
