# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
排班助手智能体（对话大脑）
多轮会话状态机 + 可解释的"思考"步骤 + 缺失信息对话式追问

设计要点：
- 会话状态持久化在 chat_sessions.context（JSON）
- 每步输出 thinking 步骤数组，前端以"思考中"逐条展示，实现"像智能体一样思考"
- 姓名识别：优先精确匹配已登记用户姓名，其次解析"我是X/我叫X"
- 值班表可能包含多人：先识别"我"的条目，避免把所有人的排班都当成我的
"""
import json
import re
from datetime import datetime

from backend.db.database import query, execute
from backend.core.models import User
from backend.utils.helpers import format_date, format_time

# ===== 会话状态 =====
STATE_IDLE = "idle"                    # 空闲，等待用户发值班表
STATE_AWAITING_NAME = "awaiting_name"  # 等待用户告知姓名
STATE_AWAITING_FIELD = "awaiting_field"  # 等待用户补充缺失字段
STATE_AWAITING_SCOPE = "awaiting_scope"  # 等待用户确认"哪一条是我"

# 字段中文标签
FIELD_LABELS = {
    "name": "值班人姓名",
    "duty_date": "值班日期",
    "start_time": "开始时间",
    "end_time": "结束时间",
    "location": "值班地点",
    "remark": "备注",
}

# "我是张三/我叫李四" 主语句式（非贪婪 + 边界前瞻，避免把"我是张三"整体捕获）
FIRST_PERSON_RE = re.compile(
    r"(?:我是|我叫|本人是|本人)\s*[的]?\s*([一-龥]{2,4}?)(?=[\s，,。:：、；;]|\d|$)"
)

# "保留全部"的确认词
ALL_KEYWORDS = ("全部", "都", "所有", "all", "ALL")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ===== 会话存取 =====

def _get_session(session_id: str, openid: str = None) -> dict:
    """读取会话，不存在则创建"""
    row = query("SELECT * FROM chat_sessions WHERE session_id = ?", (session_id,), one=True)
    if not row:
        execute(
            "INSERT INTO chat_sessions (session_id, openid, state, context) VALUES (?, ?, ?, ?)",
            (session_id, openid, STATE_IDLE, "{}"),
        )
        row = query("SELECT * FROM chat_sessions WHERE session_id = ?", (session_id,), one=True)
    return row


def _update_session(session_id: str, state: str = None, context: dict = None, openid: str = None):
    """更新会话状态/上下文"""
    sets, vals = [], []
    if state is not None:
        sets.append("state = ?")
        vals.append(state)
    if context is not None:
        sets.append("context = ?")
        vals.append(json.dumps(context, ensure_ascii=False))
    if openid is not None:
        sets.append("openid = ?")
        vals.append(openid)
    sets.append("updated_at = ?")
    vals.append(_now())
    vals.append(session_id)
    execute(f"UPDATE chat_sessions SET {', '.join(sets)} WHERE session_id = ?", tuple(vals))


def _load_context(row: dict) -> dict:
    """安全解析会话上下文"""
    try:
        return json.loads(row.get("context") or "{}")
    except (ValueError, TypeError):
        return {}


def _append_msg(session_id: str, role: str, content: str, thinking: list = None):
    """写入一条对话消息"""
    execute(
        "INSERT INTO chat_messages (session_id, role, content, thinking) VALUES (?, ?, ?, ?)",
        (session_id, role, content,
         json.dumps(thinking, ensure_ascii=False) if thinking else None),
    )


def _get_user(openid: str = None, name: str = None) -> dict:
    """按 openid 或姓名查已登记用户"""
    if openid:
        row = query("SELECT * FROM users WHERE openid = ?", (openid,), one=True)
        if row:
            return User.from_db_row(row).to_dict()
    if name:
        row = query("SELECT * FROM users WHERE name = ?", (name,), one=True)
        if row:
            return User.from_db_row(row).to_dict()
    return None


# ===== 姓名识别 =====

def _identify_me(schedule_names: list, my_name: str, text: str):
    """
    识别"我"在值班表中的条目。
    :return: (my_name, matched_names, need_ask)
    """
    # 1. 已有登记姓名：精确匹配
    if my_name:
        hits = [n for n in schedule_names if n and n.strip() == my_name.strip()]
        return my_name, hits, False
    # 2. 从文本解析"我是X/我叫X"
    m = FIRST_PERSON_RE.search(text or "")
    if m:
        cand = m.group(1)
        hits = [n for n in schedule_names if n and n.strip() == cand]
        return cand, hits, False
    # 3. 无法确定 → 需要询问
    return "", [], True


# ===== 回复封装 =====

def _reply(session_id: str, reply: str, thinking: list, ctx: dict,
           options: list = None, state: str = None) -> dict:
    """统一产出：落库消息 + 更新会话 + 返回给前端"""
    _append_msg(session_id, "agent", reply, thinking)
    _update_session(session_id, state=state, context=ctx)
    return {
        "reply": reply,
        "thinking": thinking,
        "options": options or [],
        "state": state,
    }


# ===== 主入口 =====

def handle_message(session_id: str, text: str, openid: str = None) -> dict:
    """
    处理一条用户消息，返回智能体回复。
    返回结构：{reply, thinking, options, state}
    """
    text = (text or "").strip()
    row = _get_session(session_id, openid)
    state = row.get("state") or STATE_IDLE
    ctx = _load_context(row)
    if not ctx.get("my_name"):
        ctx["my_name"] = ""
        # 已登记用户优先补齐姓名
        user = _get_user(openid=openid or row.get("openid"))
        if user:
            ctx["my_name"] = user["name"]

    _append_msg(session_id, "user", text)
    thinking = []

    if not text:
        return _reply(session_id, "我在呢～把值班表文字发给我，我帮你挑出属于你的排班。",
                      thinking, ctx, state=STATE_IDLE)

    # 状态分发
    if state == STATE_AWAITING_NAME:
        return _on_name(text, session_id, ctx, thinking)
    if state == STATE_AWAITING_FIELD:
        return _on_field_answer(text, session_id, ctx, thinking)
    if state == STATE_AWAITING_SCOPE:
        return _on_scope(text, session_id, ctx, thinking)
    return _on_schedule_text(text, session_id, ctx, thinking)


# ===== 分支：收到值班表文本 =====

def _on_schedule_text(text: str, session_id: str, ctx: dict, thinking: list) -> dict:
    from backend.core.extractor import extract_schedules

    thinking.append("正在读取你发来的文本…")
    result = extract_schedules(text, source_type="chat", original_text=text[:500], dry_run=True)
    drafts = result.get("schedules", [])
    thinking.append(f"识别到 {len(drafts)} 条排班记录")

    if not drafts:
        return _reply(session_id,
                      "我没能从这段文字里识别出排班信息。可以按「姓名 日期 时间 地点」的格式再发一次吗？",
                      thinking, ctx, state=STATE_IDLE)

    names = [d.get("name") for d in drafts if d.get("name")]
    uniq = list(dict.fromkeys(names))
    my_name, hits, need_ask = _identify_me(names, ctx.get("my_name", ""), text)

    # 情况A：多人值班表且无法确定"我"是谁 → 反问
    if need_ask and len(uniq) > 1:
        ctx["draft"] = drafts
        thinking.append("这份值班表包含多个人，需要确认哪一条属于你")
        return _reply(session_id,
                      f"这份值班表里有 {len(uniq)} 位同事：{'、'.join(uniq[:8])}。请问哪一位是你？",
                      thinking, ctx, options=uniq[:8], state=STATE_AWAITING_SCOPE)

    # 情况B：确定"我" → 只保留我的条目
    if my_name and hits:
        mine = [d for d in drafts if (d.get("name") or "").strip() == my_name]
        ctx["my_name"] = my_name
    elif len(uniq) == 1:
        mine = drafts
        ctx["my_name"] = uniq[0]
    else:
        mine = drafts

    thinking.append(f"已锁定属于你的排班 {len(mine)} 条（共 {len(drafts)} 条）")
    return _save_and_ask(mine, session_id, ctx, thinking)


def _save_and_ask(mine: list, session_id: str, ctx: dict, thinking: list) -> dict:
    """保存属于"我"的排班，并逐条追问缺失字段"""
    saved = []
    for d in mine:
        sid = execute(
            """INSERT INTO schedules
               (name, duty_date, start_time, end_time, location, remark, source_type, original_text)
               VALUES (?, ?, ?, ?, ?, ?, 'chat', ?)""",
            (d.get("name", ""), d.get("duty_date", ""), d.get("start_time"),
             d.get("end_time"), d.get("location"), d.get("remark", ""),
             d.get("original_text", "")),
        )
        saved.append((sid, d))
    thinking.append(f"已保存 {len(saved)} 条属于你的排班")

    # 汇总缺失字段（逐条追问）
    missing = []
    for sid, d in saved:
        for f in (d.get("missing_fields") or []):
            missing.append({"schedule_id": sid, "field": f, "name": d.get("name", "")})

    if missing:
        first = missing[0]
        ctx["pending"] = {"schedule_id": first["schedule_id"], "field": first["field"],
                          "rest": missing[1:]}
        label = FIELD_LABELS.get(first["field"], first["field"])
        who = f"（{first['name']}）" if first["name"] else ""
        thinking.append(f"发现信息缺失：{label}，需要向你确认")
        return _reply(session_id, f"这条排班还缺少「{label}」{who}，能补充一下吗？",
                      thinking, ctx, state=STATE_AWAITING_FIELD)

    ctx["pending"] = None
    return _reply(session_id,
                  f"完成啦！已为你保存 {len(saved)} 条排班，可以去「排班」页查看 ✅",
                  thinking, ctx, state=STATE_IDLE)


# ===== 分支：等待补充字段 =====

def _on_field_answer(text: str, session_id: str, ctx: dict, thinking: list) -> dict:
    pending = ctx.get("pending") or {}
    sid = pending.get("schedule_id")
    field = pending.get("field")
    if not sid or not field:
        ctx["pending"] = None
        return _reply(session_id, "没有待补充的信息了，你可以继续发值班表给我。",
                      thinking, ctx, state=STATE_IDLE)

    # 按字段类型做格式归一
    value = text
    if field == "duty_date":
        value = format_date(text)
    elif field in ("start_time", "end_time"):
        value = format_time(text)

    thinking.append(f"把你说的内容写入「{FIELD_LABELS.get(field, field)}」")
    execute("UPDATE schedules SET {} = ?, updated_at = ? WHERE id = ?".format(field),
            (value, _now(), sid))

    rest = pending.get("rest") or []
    if rest:
        nxt = rest[0]
        ctx["pending"] = {"schedule_id": nxt["schedule_id"], "field": nxt["field"],
                          "rest": rest[1:]}
        label = FIELD_LABELS.get(nxt["field"], nxt["field"])
        thinking.append(f"还有信息缺失：{label}")
        return _reply(session_id, f"已记录～还有一处缺少「{label}」，请补充：",
                      thinking, ctx, state=STATE_AWAITING_FIELD)

    ctx["pending"] = None
    return _reply(session_id, "补充完成，已更新你的排班 ✅", thinking, ctx, state=STATE_IDLE)


# ===== 分支：等待确认"哪一条是我" =====

def _on_scope(text: str, session_id: str, ctx: dict, thinking: list) -> dict:
    drafts = ctx.get("draft") or []
    names = list(dict.fromkeys([d.get("name") for d in drafts if d.get("name")]))

    # 选择"全部"
    if any(k in text for k in ALL_KEYWORDS):
        thinking.append("你选择保留全部排班")
        ctx["draft"] = None
        return _save_and_ask(drafts, session_id, ctx, thinking)

    # 从回复中匹配姓名
    chosen = ""
    for n in names:
        if n and n in text:
            chosen = n
            break
    if not chosen:
        m = FIRST_PERSON_RE.search(text)
        chosen = m.group(1) if m else text.strip()[:8]

    thinking.append(f"确认你选择的是：{chosen}")
    ctx["my_name"] = chosen
    mine = [d for d in drafts if (d.get("name") or "").strip() == chosen]
    if not mine:
        mine = drafts
    ctx["draft"] = None
    return _save_and_ask(mine, session_id, ctx, thinking)


# ===== 分支：等待姓名 =====

def _on_name(text: str, session_id: str, ctx: dict, thinking: list) -> dict:
    m = FIRST_PERSON_RE.search(text)
    name = (m.group(1) if m else text).strip()[:8]
    if not name:
        return _reply(session_id, "请告诉我你的姓名，例如：张三", thinking, ctx,
                      state=STATE_AWAITING_NAME)
    thinking.append(f"记住你的姓名：{name}")
    ctx["my_name"] = name
    return _reply(session_id,
                  f"好的，{name}。现在把值班表发给我吧，我会自动挑出属于你的排班。",
                  thinking, ctx, state=STATE_IDLE)


# ===== 会话启动与历史 =====

def start_session(session_id: str, openid: str = None) -> dict:
    """打开聊天页时调用：返回欢迎语 + 已登记姓名"""
    row = _get_session(session_id, openid)
    ctx = _load_context(row)
    user = _get_user(openid=openid or row.get("openid"))
    if user:
        ctx["my_name"] = user["name"]
        _update_session(session_id, context=ctx)
    greeting = (
        f"你好，{user['name']}！我是排班助手智能体 🤖\n把值班表发给我，我帮你挑出属于你的排班；"
        "信息不全我会在对话里追问你。"
        if user
        else "你好！我是排班助手智能体 🤖\n先告诉我你的姓名吧（例如：我是张三），"
             "之后发值班表我就能自动识别属于你的排班。"
    )
    return {
        "greeting": greeting,
        "my_name": ctx.get("my_name", ""),
        "registered": bool(user),
        "state": row.get("state") or STATE_IDLE,
    }


def get_history(session_id: str, limit: int = 50) -> list:
    """获取对话历史（按时间正序）"""
    rows = query(
        "SELECT role, content, thinking, created_at FROM chat_messages "
        "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
        (session_id, limit),
    )
    rows = list(reversed(rows))
    for r in rows:
        if r.get("thinking"):
            try:
                r["thinking"] = json.loads(r["thinking"])
            except (ValueError, TypeError):
                r["thinking"] = []
        else:
            r["thinking"] = []
    return rows


def reset_session(session_id: str) -> dict:
    """重置会话（清空上下文与历史）"""
    execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    execute("UPDATE chat_sessions SET state = ?, context = '{}', updated_at = ? WHERE session_id = ?",
            (STATE_IDLE, _now(), session_id))
    return {"success": True}
