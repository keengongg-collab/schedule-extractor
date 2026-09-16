# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
数据模型定义
使用 dataclass 定义排班日程、提醒配置、问答记录等核心数据结构
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Schedule:
    """排班日程模型"""
    id: Optional[int] = None
    name: str = ""                        # 值班人姓名
    duty_date: str = ""                   # 值班日期 YYYY-MM-DD
    start_time: Optional[str] = None      # 起始时间 HH:MM
    end_time: Optional[str] = None        # 结束时间 HH:MM
    location: Optional[str] = None        # 值班地点
    remark: str = ""                     # 备注
    source_type: str = "manual"          # 来源：upload/paste/word_selector/manual
    original_text: Optional[str] = None   # 原始文本
    is_confirmed: bool = False           # 是否已确认

    def to_dict(self) -> dict:
        """转为字典（用于 API 响应）"""
        return {
            "id": self.id,
            "name": self.name,
            "duty_date": self.duty_date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "location": self.location,
            "remark": self.remark,
            "source_type": self.source_type,
            "original_text": self.original_text,
            "is_confirmed": self.is_confirmed,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "Schedule":
        """从数据库行构建对象"""
        return cls(
            id=row.get("id"),
            name=row.get("name", ""),
            duty_date=row.get("duty_date", ""),
            start_time=row.get("start_time"),
            end_time=row.get("end_time"),
            location=row.get("location"),
            remark=row.get("remark", ""),
            source_type=row.get("source_type", "manual"),
            original_text=row.get("original_text"),
            is_confirmed=bool(row.get("is_confirmed", 0)),
        )


@dataclass
class Reminder:
    """提醒配置模型"""
    id: Optional[int] = None
    schedule_id: Optional[int] = None
    advance_minutes: int = 15            # 提前提醒分钟数
    custom_message: Optional[str] = None  # 自定义提醒文案
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "schedule_id": self.schedule_id,
            "advance_minutes": self.advance_minutes,
            "custom_message": self.custom_message,
            "is_active": self.is_active,
        }


@dataclass
class QARecord:
    """AI问答记录模型"""
    id: Optional[int] = None
    schedule_id: Optional[int] = None
    question: str = ""                   # AI提出的问题
    answer: Optional[str] = None          # 用户回答
    field_name: Optional[str] = None     # 涉及字段名
    status: str = "pending"              # pending/answered/applied

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "schedule_id": self.schedule_id,
            "question": self.question,
            "answer": self.answer,
            "field_name": self.field_name,
            "status": self.status,
        }
