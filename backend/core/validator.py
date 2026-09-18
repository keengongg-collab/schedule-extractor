# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
排班字段统一校验模块

所有入口（AI 抽取、手动新增、QA 回答更新）共用同一套字段定义与校验逻辑，
避免不同 API 各自实现不同的"字段是否完整"判断。
"""

# 核心必填字段（缺一即视为信息不完整，需要生成 QA 追问）
REQUIRED_FIELDS = [
    "name",
    "duty_date",
    "start_time",
    "end_time",
    "location",
]

# 全部业务字段（含可选的备注）
ALL_FIELDS = REQUIRED_FIELDS + ["remark"]

# QA 回答允许修改的字段白名单
# 禁止通过 field_name 修改 id / created_at / source_type / is_confirmed 等字段
ALLOWED_QA_FIELDS = {
    "name",
    "duty_date",
    "start_time",
    "end_time",
    "location",
    "remark",
}

# 日程 PUT 接口允许修改的字段（比 QA 多一个确认状态）
ALLOWED_UPDATE_FIELDS = ALLOWED_QA_FIELDS | {"is_confirmed"}


class ExtractionError(Exception):
    """AI 抽取异常：返回内容无法解析或结构不符合约定（区别于网络错误）"""


def normalize_schedule(item: dict) -> dict:
    """
    字段标准化：AI/规则结果统一处理，缺失值一律转为空字符串。
    解决 None 写入 SQLite NOT NULL 字段导致 IntegrityError 的问题。
    """
    if not isinstance(item, dict):
        raise ExtractionError(f"排班记录格式错误，应为对象，实际为：{type(item).__name__}")

    return {
        "name": str(item.get("name") or "").strip(),
        "duty_date": str(item.get("duty_date") or "").strip(),
        "start_time": str(item.get("start_time") or "").strip(),
        "end_time": str(item.get("end_time") or "").strip(),
        "location": str(item.get("location") or "").strip(),
        "remark": str(item.get("remark") or "").strip(),
    }


def validate_schedule(schedule: dict) -> dict:
    """
    校验单条排班的必填字段完整性。

    :return: {"valid": bool, "missing_fields": [...]}
    """
    missing = [
        field for field in REQUIRED_FIELDS
        if not str(schedule.get(field) or "").strip()
    ]
    return {"valid": len(missing) == 0, "missing_fields": missing}


def clean_ai_payload(raw) -> list:
    """
    校验并清洗 AI 返回的整体结构：
        AI 返回 → JSON 解析（在 extractor 中完成）→ 结构检查 → 字段标准化

    约定结构：{"schedules": [...]}（questions 可带但不采信，缺失字段由本地校验得出）

    :return: 标准化后的 schedule dict 列表
    :raises ExtractionError: 结构不符合约定
    """
    if not isinstance(raw, dict):
        raise ExtractionError("AI 返回格式错误：顶层应为 JSON 对象")

    schedules = raw.get("schedules")
    if not isinstance(schedules, list):
        raise ExtractionError("AI 返回格式错误：缺少 schedules 数组")

    cleaned = []
    for idx, item in enumerate(schedules):
        if not isinstance(item, dict):
            raise ExtractionError(f"AI 返回格式错误：第 {idx + 1} 条排班不是对象")
        cleaned.append(normalize_schedule(item))
    return cleaned
