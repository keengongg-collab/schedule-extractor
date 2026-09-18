# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
AI 排班信息抽取模块
调用大模型（OpenAI 兼容接口）从文本中提取排班信息

处理管线（v1.0）：
    AI 返回 → JSON 解析 → 结构检查 → 字段标准化 → 字段校验 → 业务处理

核心规则：
- 信息模糊/缺失/有歧义时，禁止编造数据
- 缺失字段统一转为空字符串（避免写入 NOT NULL 列报错），并生成 QA 待补充
- AI 返回结构错误时抛出 ExtractionError，由 API 层返回明确错误（不静默返回 0 条）
- AI 网络/服务异常时降级为正则兜底
"""
import json

from backend.config import AI_API_KEY, AI_BASE_URL, AI_MODEL
from backend.db.database import execute
from backend.utils.helpers import format_date, format_time
from backend.utils.logger import get_logger
from backend.core.validator import (
    ExtractionError,
    clean_ai_payload,
    normalize_schedule,
    validate_schedule,
)

logger = get_logger("extractor")

# AI 系统提示词：定义抽取规则
SYSTEM_PROMPT = """你是一个排班信息提取助手。你的任务是从用户提供的文本中提取排班/值班信息。

需要提取的字段：
1. name：值班人姓名
2. duty_date：值班日期（格式 YYYY-MM-DD）
3. start_time：起始时间（格式 HH:MM）
4. end_time：结束时间（格式 HH:MM）
5. location：值班地点
6. remark：备注信息

规则：
- 严格从文本中提取，禁止编造或推测不存在的数据
- 如果某个字段在文本中无法确定（模糊、缺失、有歧义），将该字段值设为 null，并在 missing_fields 中列出
- 多条排班信息分别提取，返回数组
- 日期如只有"月日"无年份，使用当前年份补全

返回 JSON 格式：
{
  "schedules": [
    {
      "name": "张三",
      "duty_date": "2024-03-15",
      "start_time": "08:00",
      "end_time": "12:00",
      "location": "图书馆一楼",
      "remark": "注意提前到岗",
      "missing_fields": []
    }
  ]
}"""


def extract_schedules(text: str, source_type: str = "manual", original_text: str = "", dry_run: bool = False) -> dict:
    """
    从文本中提取排班信息
    :param text: 待解析的文本
    :param source_type: 来源类型 upload/paste/word_selector/manual/chat
    :param original_text: 原始文本（用于存储追溯）
    :param dry_run: 只抽取预览、不落库（对话智能体先确认归属再保存）
    :return: {"schedules": [...], "questions": [...], "total": int}
    :raises ExtractionError: AI 返回内容无法解析或结构错误
    """
    # 如果没有配置 AI API Key，使用规则匹配兜底
    if not AI_API_KEY:
        logger.info("未配置 AI_API_KEY，使用正则规则匹配")
        return _fallback_extract(text, source_type, original_text, dry_run)

    try:
        schedules = _call_ai_extract(text)
    except ExtractionError:
        # AI 返回格式错误：不静默吞掉，交给 API 层返回明确错误
        logger.error("AI 返回内容解析或结构校验失败")
        raise
    except Exception as e:
        # AI 网络/服务异常：降级为规则匹配，保证流程可用
        logger.warning("AI 服务调用失败，降级为规则匹配: %s", e)
        return _fallback_extract(text, source_type, original_text, dry_run)

    logger.info("AI 抽取完成，共 %d 条候选记录", len(schedules))

    questions = []
    saved_ids = []

    # 逐条处理：标准化 → 日期时间归一 → 统一字段校验
    for item in schedules:
        item = normalize_schedule(item)

        # 日期/时间格式归一（非空才处理，空串保留）
        if item["duty_date"]:
            item["duty_date"] = format_date(item["duty_date"])
        if item["start_time"]:
            item["start_time"] = format_time(item["start_time"])
        if item["end_time"]:
            item["end_time"] = format_time(item["end_time"])

        # 缺失字段一律以本地统一校验为准，不直接采信 AI 的 missing_fields
        missing = validate_schedule(item)["missing_fields"]
        item["missing_fields"] = missing
        item["original_text"] = original_text

        # dry_run：只做抽取预览，不落库、不生成提问记录
        if dry_run:
            saved_ids.append(None)
            questions.extend(_build_question_objs(None, item, missing))
            continue

        schedule_id = _insert_schedule(item, source_type)
        logger.info("日程已创建 id=%s name=%s date=%s 缺失字段=%s",
                    schedule_id, item["name"], item["duty_date"], missing or "无")
        saved_ids.append(schedule_id)

        if missing:
            questions.extend(_create_qa_records(schedule_id, item, missing))

    return {
        "schedules": [dict(item, id=sid) for item, sid in zip(schedules, saved_ids)],
        "questions": questions,
        "total": len(schedules),
    }


def _call_ai_extract(text: str) -> list:
    """
    调用 AI 大模型提取排班信息。
    完成：请求 → JSON 解析（兼容 ```json 包裹）→ 结构检查 → 字段标准化
    :raises ExtractionError: JSON 解析失败或结构不符合约定
    """
    from openai import OpenAI

    client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)

    logger.info("发起 AI 抽取请求 model=%s 文本长度=%d", AI_MODEL, len(text or ""))
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请从以下文本中提取排班信息：\n\n{text}"},
        ],
        temperature=0.1,  # 低温度，减少随机性
    )

    content = (response.choices[0].message.content or "").strip()
    logger.info("AI 返回内容长度=%d", len(content))

    # 解析 JSON（兼容可能包裹在 ```json ... ``` 中的情况）
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        raw = json.loads(content)
    except json.JSONDecodeError as e:
        raise ExtractionError(f"AI 返回的内容不是合法 JSON：{e}") from e

    # 结构检查 + 字段标准化（内部会在异常时抛 ExtractionError）
    return clean_ai_payload(raw)


def _insert_schedule(item: dict, source_type: str) -> int:
    """插入一条日程（缺失字段已是空字符串，不会违反 NOT NULL 约束）"""
    return execute(
        """INSERT INTO schedules
           (name, duty_date, start_time, end_time, location, remark, source_type, original_text)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            item.get("name", ""),
            item.get("duty_date", ""),
            item.get("start_time") or None,
            item.get("end_time") or None,
            item.get("location") or None,
            item.get("remark", ""),
            source_type,
            item.get("original_text", ""),
        ),
    )


def _build_question_objs(schedule_id, item: dict, missing: list) -> list:
    """构造返回给调用方的问题对象（dry_run 时 schedule_id 为 None）"""
    return [
        {
            "qa_id": None,
            "schedule_id": schedule_id,
            "name": item.get("name", ""),
            "duty_date": item.get("duty_date", ""),
            "field": field,
            "question": f"排班信息中缺少「{_get_field_label(field)}」，请补充：",
        }
        for field in missing
    ]


def _create_qa_records(schedule_id: int, item: dict, missing: list) -> list:
    """为缺失字段创建 QA 待补充记录，并返回问题对象列表"""
    questions = []
    for field in missing:
        field_label = _get_field_label(field)
        question_text = f"排班信息中缺少「{field_label}」，请补充："
        qa_id = execute(
            """INSERT INTO qa_records (schedule_id, question, field_name, status)
               VALUES (?, ?, ?, 'pending')""",
            (schedule_id, question_text, field),
        )
        logger.info("QA 已创建 id=%s schedule_id=%s 缺失字段=%s", qa_id, schedule_id, field)
        questions.append({
            "qa_id": qa_id,
            "schedule_id": schedule_id,
            "name": item.get("name", ""),
            "duty_date": item.get("duty_date", ""),
            "field": field,
            "question": question_text,
        })
    return questions


def _fallback_extract(text: str, source_type: str, original_text: str, dry_run: bool = False) -> dict:
    """
    规则匹配兜底方案（无 AI Key 或 AI 服务不可用时使用）
    只保存能完整识别为排班的行；无法识别的行直接跳过，不制造空日程垃圾数据。
    """
    import re

    schedules = []
    questions = []
    saved_ids = []
    skipped = 0

    # 按行分割处理
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 匹配 "姓名 日期 时间 地点" 格式
    # 示例：张三 2024-03-15 08:00-12:00 图书馆一楼
    pattern = re.compile(
        r"([\u4e00-\u9fa5]{2,4})\s+"           # 姓名（2-4个汉字）
        r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+"     # 日期
        r"(\d{1,2}:\d{2})\s*[-~至到]\s*"        # 起始时间
        r"(\d{1,2}:\d{2})\s+"                   # 结束时间
        r"(.+)",                                # 地点（剩余部分）
    )
    # 行首"我是张三 / 我叫李四"前缀（对话智能体常见输入）
    # 注意：姓名 token 用非贪婪 + 边界前瞻，避免把"我是张三"整体捕获为姓名
    first_person_prefix = re.compile(
        r"^\s*(?:我是|我叫|本人是|本人)\s*[的]?\s*"
        r"([一-龥]{2,4}?)(?=[\s，,。:：、；;]|\d|$)"
    )
    date_head = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}")

    def match_line(raw_line):
        """先剥离"我是X"前缀再匹配（避免主正则贪婪吞掉"我是张三"），必要时补齐姓名"""
        fm = first_person_prefix.match(raw_line)
        if fm:
            rest = raw_line[fm.end():].lstrip("，,。:： \t")
            m = pattern.match(rest)
            if m:
                return m  # 形如"我是张三 张三 2026-..."，剥离后即标准格式
            if date_head.match(rest):
                # 形如"我是张三 2026-..."（姓名未重复），用捕获姓名补齐
                return pattern.match(f"{fm.group(1)} {rest}")
            return None
        return pattern.match(raw_line)

    for line in lines:
        m = match_line(line)
        if not m:
            # 非排班行（说明文字、标题等）直接跳过
            skipped += 1
            continue

        item = normalize_schedule({
            "name": m.group(1),
            "duty_date": format_date(m.group(2)),
            "start_time": format_time(m.group(3)),
            "end_time": format_time(m.group(4)),
            "location": m.group(5).strip(),
            "remark": "",
        })
        item["missing_fields"] = validate_schedule(item)["missing_fields"]
        item["original_text"] = original_text
        schedules.append(item)

        if dry_run:
            saved_ids.append(None)
            questions.extend(_build_question_objs(None, item, item["missing_fields"]))
            continue

        schedule_id = _insert_schedule(item, source_type)
        saved_ids.append(schedule_id)
        if item["missing_fields"]:
            questions.extend(_create_qa_records(schedule_id, item, item["missing_fields"]))

    if skipped:
        logger.info("规则匹配跳过 %d 行非排班文本", skipped)
    logger.info("规则匹配完成，识别 %d 条排班", len(schedules))

    return {
        "schedules": [dict(item, id=sid) for item, sid in zip(schedules, saved_ids)],
        "questions": questions,
        "total": len(schedules),
    }


def _get_field_label(field: str) -> str:
    """字段名转中文标签"""
    labels = {
        "name": "姓名",
        "duty_date": "值班日期",
        "start_time": "起始时间",
        "end_time": "结束时间",
        "location": "值班地点",
        "remark": "备注",
    }
    return labels.get(field, field)


def apply_schedules(schedules: list, source_type: str = "upload", original_text: str = "") -> dict:
    """
    将预览（dry_run）结果正式落库，并为缺失字段生成 QA 待补充记录。
    PC 端导入流程：extract_schedules(dry_run=True) 预览 → 用户确认 → 本函数落库。

    :param schedules: dry_run 预览返回的 schedules 列表（可带 id=None）
    :param source_type: 来源类型 upload/paste/word_selector/chat
    :param original_text: 原始文本（预览未携带时补传）
    :return: {"schedules": [带真实 id], "questions": [...], "total": int}
    """
    questions, applied = [], []

    for item in schedules:
        item = normalize_schedule(item)

        if item["duty_date"]:
            item["duty_date"] = format_date(item["duty_date"])
        if item["start_time"]:
            item["start_time"] = format_time(item["start_time"])
        if item["end_time"]:
            item["end_time"] = format_time(item["end_time"])

        missing = validate_schedule(item)["missing_fields"]
        item["missing_fields"] = missing
        item["original_text"] = original_text or item.get("original_text", "")

        schedule_id = _insert_schedule(item, source_type)
        logger.info("导入日程已创建 id=%s name=%s date=%s 缺失字段=%s",
                    schedule_id, item["name"], item["duty_date"], missing or "无")
        applied.append(dict(item, id=schedule_id))

        if missing:
            questions.extend(_create_qa_records(schedule_id, item, missing))

    return {"schedules": applied, "questions": questions, "total": len(applied)}
