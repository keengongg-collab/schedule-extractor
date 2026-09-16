"""
AI 排班信息抽取模块
调用大模型（OpenAI 兼容接口）从文本中提取排班信息

核心规则：
- 信息模糊/缺失/有歧义时，禁止编造数据
- 主动生成提问，让用户补充
- 用户回答后重新解析更新日程
"""
import json
import os
from typing import List

from backend.config import AI_API_KEY, AI_BASE_URL, AI_MODEL
from backend.db.database import execute, query
from backend.utils.helpers import format_date, format_time

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
      "missing_fields": []  // 缺失的字段名列表
    }
  ]
}"""


def extract_schedules(text: str, source_type: str = "manual", original_text: str = "") -> dict:
    """
    从文本中提取排班信息
    :param text: 待解析的文本
    :param source_type: 来源类型 upload/paste/word_selector/manual
    :param original_text: 原始文本（用于存储追溯）
    :return: {"schedules": [...], "questions": [...], "total": int}
    """
    # 如果没有配置 AI API Key，使用规则匹配兜底
    if not AI_API_KEY:
        return _fallback_extract(text, source_type, original_text)

    try:
        result = _call_ai_extract(text)
    except Exception as e:
        print(f"[AI抽取] 调用失败，降级为规则匹配: {e}")
        return _fallback_extract(text, source_type, original_text)

    schedules = result.get("schedules", [])
    questions = []  # 待回答的问题列表
    saved_ids = []

    # 逐条处理提取结果
    for item in schedules:
        missing = item.get("missing_fields", [])

        # 格式化日期和时间
        if item.get("duty_date"):
            item["duty_date"] = format_date(item["duty_date"])
        if item.get("start_time"):
            item["start_time"] = format_time(item["start_time"])
        if item.get("end_time"):
            item["end_time"] = format_time(item["end_time"])

        # 存入数据库
        schedule_id = execute(
            """INSERT INTO schedules
               (name, duty_date, start_time, end_time, location, remark, source_type, original_text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.get("name", ""),
                item.get("duty_date", ""),
                item.get("start_time"),
                item.get("end_time"),
                item.get("location"),
                item.get("remark", ""),
                source_type,
                original_text,
            ),
        )
        saved_ids.append(schedule_id)

        # 如果有缺失字段，生成提问记录
        if missing:
            for field in missing:
                field_label = _get_field_label(field)
                qa_id = execute(
                    """INSERT INTO qa_records (schedule_id, question, field_name, status)
                       VALUES (?, ?, ?, 'pending')""",
                    (schedule_id, f"排班信息中缺少「{field_label}」，请补充：", field),
                )
                questions.append({
                    "qa_id": qa_id,
                    "schedule_id": schedule_id,
                    "name": item.get("name", ""),
                    "duty_date": item.get("duty_date", ""),
                    "field": field,
                    "question": f"排班信息中缺少「{field_label}」，请补充：",
                })

    return {
        "schedules": [dict(item, id=sid) for item, sid in zip(schedules, saved_ids)],
        "questions": questions,
        "total": len(schedules),
    }


def _call_ai_extract(text: str) -> dict:
    """调用 AI 大模型提取排班信息"""
    from openai import OpenAI

    client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)

    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请从以下文本中提取排班信息：\n\n{text}"},
        ],
        temperature=0.1,  # 低温度，减少随机性
    )

    content = response.choices[0].message.content.strip()

    # 解析 JSON（兼容可能包裹在 ```json ... ``` 中的情况）
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    return json.loads(content)


def _fallback_extract(text: str, source_type: str, original_text: str) -> dict:
    """
    规则匹配兜底方案（无 AI Key 时使用）
    用正则表达式简单匹配排班信息
    """
    import re

    schedules = []
    questions = []
    saved_ids = []

    # 按行分割处理
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        # 简单规则：匹配 "姓名 日期 时间 地点" 格式
        # 示例：张三 2024-03-15 08:00-12:00 图书馆一楼
        m = re.match(
            r"([\u4e00-\u9fa5]{2,4})\s+"           # 姓名（2-4个汉字）
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+"     # 日期
            r"(\d{1,2}:\d{2})\s*[-~至到]\s*"        # 起始时间
            r"(\d{1,2}:\d{2})\s+"                   # 结束时间
            r"(.+)",                                # 地点（剩余部分）
            line,
        )

        if m:
            item = {
                "name": m.group(1),
                "duty_date": format_date(m.group(2)),
                "start_time": format_time(m.group(3)),
                "end_time": format_time(m.group(4)),
                "location": m.group(5).strip(),
                "remark": "",
                "missing_fields": [],
            }
        else:
            # 无法匹配，标记为缺失信息
            item = {
                "name": "",
                "duty_date": "",
                "start_time": None,
                "end_time": None,
                "location": "",
                "remark": line,
                "missing_fields": ["name", "duty_date"],
            }

        # 存入数据库
        schedule_id = execute(
            """INSERT INTO schedules
               (name, duty_date, start_time, end_time, location, remark, source_type, original_text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (item["name"], item["duty_date"], item["start_time"], item["end_time"],
             item["location"], item["remark"], source_type, original_text),
        )
        saved_ids.append(schedule_id)

        # 缺失字段生成提问
        for field in item["missing_fields"]:
            field_label = _get_field_label(field)
            qa_id = execute(
                """INSERT INTO qa_records (schedule_id, question, field_name, status)
                   VALUES (?, ?, ?, 'pending')""",
                (schedule_id, f"排班信息中缺少「{field_label}」，请补充：", field),
            )
            questions.append({
                "qa_id": qa_id,
                "schedule_id": schedule_id,
                "field": field,
                "question": f"排班信息中缺少「{field_label}」，请补充：",
            })

    return {
        "schedules": [dict(item, id=sid) for item, sid in zip(schedules if schedules else [{}]*len(saved_ids), saved_ids)],
        "questions": questions,
        "total": len(saved_ids),
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
