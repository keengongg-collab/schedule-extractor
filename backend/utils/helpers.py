# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
通用工具函数
"""
from datetime import datetime
import re


def format_date(date_str: str) -> str:
    """
    统一日期格式为 YYYY-MM-DD
    支持多种输入格式：2024/3/1、2024年3月1日、3月1日 等
    """
    if not date_str:
        return ""
    date_str = str(date_str).strip()

    # 已是标准格式
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", date_str):
        parts = date_str.split("-")
        return f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"

    # 带年月日的中文格式
    m = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # 斜杠分隔
    m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # 只有月日（默认补当前年份）
    m = re.match(r"(\d{1,2})月(\d{1,2})日", date_str)
    if m:
        year = datetime.now().year
        return f"{year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"

    # 数字格式：3.1 或 03-01
    m = re.match(r"(\d{1,2})[.\-](\d{1,2})", date_str)
    if m:
        year = datetime.now().year
        return f"{year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"

    return date_str  # 无法识别则原样返回


def format_time(time_str: str) -> str:
    """
    统一时间格式为 HH:MM
    支持：9:00、09:00、上午9点、14:30、下午3点 等
    """
    if not time_str:
        return ""
    time_str = str(time_str).strip()

    # 已是标准格式
    m = re.match(r"^(\d{1,2}):(\d{2})$", time_str)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"

    # 带上午/下午
    is_pm = "下午" in time_str or "PM" in time_str.upper()
    is_am = "上午" in time_str or "AM" in time_str.upper()

    m = re.search(r"(\d{1,2})[:点时](\d{0,2})", time_str)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        if is_pm and hour < 12:
            hour += 12
        return f"{hour:02d}:{minute:02d}"

    return time_str


def is_valid_date(date_str: str) -> bool:
    """检查是否为有效的日期字符串"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def get_weekday(date_str: str) -> str:
    """根据日期获取星期几（中文）"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return weekdays[dt.weekday()]
    except (ValueError, TypeError):
        return ""
