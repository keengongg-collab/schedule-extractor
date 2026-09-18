# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
AI 自然语言日程指令解析
把用户自然语言解析为结构化意图（create / update / delete / query），
并在数据库中匹配候选日程，返回预览。

安全约定：本模块只做「解析 + 匹配 + 预览」，绝不执行任何写操作。
真正的增删改由 PC 端在用户确认后调用 schedules API 完成。

解析策略：配置 AI_API_KEY 时走大模型；否则正则兜底。
"""
import json
import re
from datetime import date, timedelta

from backend.config import AI_API_KEY, AI_BASE_URL, AI_MODEL
from backend.db.database import query
from backend.utils.helpers import format_date, format_time
from backend.utils.logger import get_logger

logger = get_logger("ai_intent")

SYSTEM_PROMPT = """你是日程管理助手。把用户的中文指令解析为 JSON，严格按文本提取，禁止编造：
{
  "action": "create | update | delete | query",
  "schedules": [{"name": "", "duty_date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM", "location": "", "remark": ""}],
  "match": {"name": "", "duty_date": "YYYY-MM-DD", "start_time": "HH:MM"},
  "fields": {"name": "", "duty_date": "", "start_time": "", "end_time": "", "location": ""}
}
规则：
- create：新增日程；值班表类多行文本也归 create（schedules 数组多条）；识别不出任何日程信息时 schedules 为 []
- update：修改日程；match 用于定位原日程（name/日期/时间），fields 为要修改的内容
- delete：删除日程；match 用于定位
- query：查询日程；match 用于定位
- 日期换算：今天/未提=今天，明天=明天，后天=后天，昨天=昨天；格式 YYYY-MM-DD
- 时间换算：下午3点=15:00，三点无上下文按当天 15:00，晚上7点=19:00；格式 HH:MM
- 会议/日程名：如"项目会议""图书馆开会"等提取为 name
输出纯 JSON，不要输出其他内容。"""

# ============================================================
# 日期时间换算
# ============================================================

def _offset_date(offset: int) -> str:
    return (date.today() + timedelta(days=offset)).isoformat()


def _cn_to_arabic(text: str) -> str:
    """把中文数字（一二三…十）替换为阿拉伯数字"""
    CN = {"零": "0", "一": "1", "二": "2", "两": "2", "三": "3", "四": "4",
          "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}

    def repl(m):
        s = m.group(0)
        if "十" in s:
            parts = list(s)
            if len(parts) == 1:
                return "10"
            left, right = parts[0], parts[-1]
            if left in CN and right in CN:
                return str(int(CN[left]) * 10 + int(CN[right]))
            if left in CN:
                return str(int(CN[left]) * 10)
            if right in CN:
                return str(10 + int(CN[right]))
            return "10"
        return CN.get(s, s)

    return re.sub(r"[零一二两三四五六七八九十]+", repl, text)


def _parse_cn_time(text: str) -> str | None:
    """从文本提取中文时间 → HH:MM（下午3点→15:00，三点→15:00）"""
    text = _cn_to_arabic(text)
    m = re.search(r"(上午|中午|下午|晚上|凌晨)?\s*(\d{1,2})\s*(?:[点:：])\s*(\d{1,2})?", text)
    if not m:
        m = re.search(r"\b(\d{1,2}):(\d{2})\b", text)
        if m:
            return f"{int(m.group(1)):02d}:{m.group(2)}"
        return None
    prefix, hour, minute = m.group(1), int(m.group(2)), m.group(3) or "00"
    if prefix in ("下午", "晚上") and hour < 12:
        hour += 12
    if prefix == "中午" and hour < 11:
        hour += 12
    return f"{hour:02d}:{minute}"


# ============================================================
# 意图解析
# ============================================================

def _ai_parse(text: str) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)
    resp = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.1,
    )
    content = (resp.choices[0].message.content or "").strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return json.loads(content)


def _clean_name(raw: str) -> str:
    """清洗日程名：去掉代词/时间/方位修饰词"""
    for word in ("我", "你", "他的", "我的", "今天", "明天", "后天", "昨天",
                 "上午", "下午", "晚上", "凌晨", "中午", "的", "那个", "这个"):
        raw = raw.replace(word, "")
    return raw.strip()


def _fallback_parse(text: str) -> dict:
    """无 AI Key 时的正则兜底（识别常见改/删/查指令）"""
    # 删除：删除/删掉/取消 XXX（的）会议/日程/值班
    m = re.search(r"(?:删除|删掉|取消)\s*(?:我)?(.+?)(?:的)?(?:会议|日程|值班|安排)", text)
    if m:
        match = {"name": _clean_name(m.group(1))}
        if "明天" in text:
            match["duty_date"] = _offset_date(1)
        elif "后天" in text:
            match["duty_date"] = _offset_date(2)
        elif "昨天" in text:
            match["duty_date"] = _offset_date(-1)
        return {"action": "delete", "match": match,
                "schedules": [], "fields": {}}
    # 修改：把/将 XXX（改到|改成）时间
    m = re.search(r"(?:把|将)?(.{1,16}?)(?:会议|日程|值班|安排)?(?:改到|改成|调到|调整到)", text)
    if m:
        # 名称：先剔除文本中的时间短语（如"下午三点"），再清洗代词
        name_raw = re.sub(
            r"(?:上午|下午|晚上|凌晨|中午)?\s*[零一二两三四五六七八九十\d]{1,3}\s*点\s*(?:分)?",
            "", m.group(1),
        )
        match = {"name": _clean_name(name_raw)}
        # 原时间：取"改到"之前的时间（用于定位）
        before = text.split("改到")[0] if "改到" in text else text.split("改成")[0]
        old_t = _parse_cn_time(before)
        if old_t:
            match["start_time"] = old_t
        # 新时间：取"改到"之后的时间（用于修改）
        after_text = _cn_to_arabic(text)
        after_m = re.search(r"(?:改到|改成|调到|调整到)\s*(?:下午|上午|晚上|中午|凌晨)?\s*(\d{1,2})\s*(?:[点:：])\s*(\d{1,2})?", after_text)
        fields = {}
        if after_m:
            hour = int(after_m.group(1))
            suffix = after_text.split("改到")[-1] if "改到" in after_text else after_text.split("改成")[-1]
            if re.search(r"(下午|晚上)", suffix) and hour < 12:
                hour += 12
            fields["start_time"] = f"{hour:02d}:{after_m.group(2) or '00'}"
        if "明天" in text:
            match["duty_date"] = _offset_date(1)
        elif "后天" in text:
            match["duty_date"] = _offset_date(2)
        elif "昨天" in text:
            match["duty_date"] = _offset_date(-1)
        return {"action": "update", "match": match, "schedules": [], "fields": fields}
    # 查询：今天/明天/本周/下周 ... 日程/安排/会议
    if re.search(r"(日程|安排|会议|有什么)", text) and re.search(r"(今天|明天|后天|本周|下周|这个月|下个月)", text):
        match = {}
        if "明天" in text:
            match["duty_date"] = _offset_date(1)
        elif "后天" in text:
            match["duty_date"] = _offset_date(2)
        else:
            match["duty_date"] = _offset_date(0)
        return {"action": "query", "match": match, "schedules": [], "fields": {}}
    # 默认按创建解析（值班表文本行）
    schedules = []
    for line in text.splitlines():
        m = re.match(
            r"([\u4e00-\u9fa5]{2,4})\s+(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+"
            r"(\d{1,2}:\d{2})\s*[-~至到]\s*(\d{1,2}:\d{2})\s*(.*)",
            line.strip(),
        )
        if m:
            schedules.append({
                "name": m.group(1), "duty_date": m.group(2).replace("/", "-"),
                "start_time": m.group(3), "end_time": m.group(4),
                "location": m.group(5).strip(), "remark": "",
            })
    if not schedules:
        # 自然语言单条："明天下午三点去图书馆开会"
        name_m = re.search(r"(?:去|到)?([\u4e00-\u9fa5]{2,6}?)(?:开会|值班|会议|吃饭|健身|上课|面试)?$", text)
        t = _parse_cn_time(text)
        location_m = re.search(r"(?:去|到)([\u4e00-\u9fa5]{2,6}(?:馆|室|楼|中心|公司|部))", text)
        schedule = {"name": (name_m.group(1) if name_m else "新日程").strip(),
                    "duty_date": _offset_date(1) if "明天" in text else _offset_date(0),
                    "start_time": t, "end_time": None,
                    "location": location_m.group(1) if location_m else None, "remark": ""}
        schedules.append(schedule)
    return {"action": "create", "match": {}, "schedules": schedules, "fields": {}}


def parse_intent(text: str) -> dict:
    """解析自然语言 → 结构化意图（纯解析，不执行任何写操作）"""
    if AI_API_KEY:
        try:
            return _ai_parse(text)
        except Exception as e:
            logger.warning("AI 意图解析失败，降级正则: %s", e)
    return _fallback_parse(text)


# ============================================================
# 候选匹配
# ============================================================

def match_candidates(match: dict, limit: int = 5) -> list:
    """按 match 条件查询匹配日程（只读）"""
    if not match:
        return []
    conds, params = [], []

    name = (match.get("name") or "").strip()
    if name:
        conds.append("name LIKE ?")
        params.append(f"%{name}%")

    duty = (match.get("duty_date") or "").strip()
    if duty:
        try:
            conds.append("duty_date = ?")
            params.append(format_date(duty))
        except ValueError:
            pass

    time = (match.get("start_time") or "").strip()
    if time and ":" in time:
        hour = time.split(":")[0]
        conds.append("(start_time LIKE ? OR end_time LIKE ?)")
        params.extend([f"{hour}:%", f"{hour}:%"])

    if not conds:
        return []
    sql = f"SELECT * FROM schedules WHERE {' AND '.join(conds)} ORDER BY duty_date, start_time LIMIT {limit}"
    return query(sql, tuple(params))


# ============================================================
# 对外主入口
# ============================================================

def _normalize_preview(s: dict) -> dict:
    """预览字段标准化（空字段转 None/空串，时间归一）"""
    item = {
        "id": None,
        "name": (s.get("name") or "").strip(),
        "duty_date": "",
        "start_time": None,
        "end_time": None,
        "location": None,
        "remark": "",
        "is_confirmed": False,
        "missing_fields": [],
    }
    if s.get("duty_date"):
        try:
            item["duty_date"] = format_date(s["duty_date"])
        except ValueError:
            item["missing_fields"].append("duty_date")
    if s.get("start_time"):
        try:
            item["start_time"] = format_time(s["start_time"])
        except ValueError:
            item["missing_fields"].append("start_time")
    if s.get("end_time"):
        try:
            item["end_time"] = format_time(s["end_time"])
        except ValueError:
            item["missing_fields"].append("end_time")
    if s.get("location"):
        item["location"] = str(s["location"]).strip()
    item["remark"] = str(s.get("remark") or "").strip()
    if not item["duty_date"]:
        item["missing_fields"].append("duty_date")
    return item


def resolve_intent(text: str) -> dict:
    """完整意图解析 + 候选匹配，返回 PC 端可直接展示的预览结果"""
    try:
        intent = parse_intent(text)
    except Exception as e:
        logger.exception("意图解析异常")
        return {"action": "create", "previews": [], "candidates": [],
                "ambiguous": False, "msg": f"解析失败：{e}"}

    action = intent.get("action") or "create"

    if action == "create":
        previews = [_normalize_preview(s) for s in (intent.get("schedules") or [])]
        if not previews:
            return {"action": action, "previews": [], "candidates": [], "ambiguous": False,
                    "msg": "未识别出要创建的日程信息，请说得更具体些（如：明天下午三点去图书馆开会）"}
        return {"action": action, "previews": previews, "candidates": [], "ambiguous": False,
                "msg": f"准备创建 {len(previews)} 条日程"}

    # update / delete / query
    match = intent.get("match") or {}
    candidates = match_candidates(match)
    fields = intent.get("fields") or {}

    if not candidates:
        return {"action": action, "previews": [], "candidates": [], "ambiguous": False,
                "msg": "没有找到匹配的日程，请补充姓名、日期或时间" if match else "未识别出要操作的日程，请提供姓名、日期或时间"}

    msg = f"找到 {len(candidates)} 条匹配日程，请选择要操作的日程" if len(candidates) > 1 else "找到 1 条匹配日程"
    return {
        "action": action,
        "previews": [],
        "candidates": candidates,
        "fields": fields,
        "ambiguous": len(candidates) > 1,
        "msg": msg,
    }
