# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
日程卡片组件
展示单条日程：时间、名称、地点、确认状态；可点击触发 clicked 信号
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class ScheduleCard(QFrame):
    """可点击的日程卡片"""

    clicked = Signal(int)  # 携带 schedule_id

    def __init__(self, schedule: dict, parent=None):
        super().__init__(parent)
        self.schedule_id = schedule.get("id")
        self.setObjectName("scheduleCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(58)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(14)

        # 左侧时间列
        time_col = QVBoxLayout()
        time_col.setSpacing(2)
        start = schedule.get("start_time") or "--:--"
        end = schedule.get("end_time") or "--:--"
        time_label = QLabel(start)
        time_label.setObjectName("cardTime")
        end_label = QLabel(f"至 {end}")
        end_label.setObjectName("cardTimeSub")
        time_col.addWidget(time_label)
        time_col.addWidget(end_label)
        time_col.addStretch()
        layout.addLayout(time_col)

        # 中间名称 + 地点
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        name_label = QLabel(schedule.get("name") or "未命名日程")
        name_label.setObjectName("cardTitle")
        sub_parts = [p for p in (schedule.get("location") or "", schedule.get("remark") or "") if p]
        sub_label = QLabel(" · ".join(sub_parts) or "无地点备注")
        sub_label.setObjectName("cardSub")
        info_col.addWidget(name_label)
        info_col.addWidget(sub_label)
        info_col.addStretch()
        layout.addLayout(info_col, 1)

        # 右侧状态标记
        if schedule.get("is_confirmed"):
            status_label = QLabel("已确认")
            status_label.setObjectName("statusConfirmed")
        else:
            status_label = QLabel("待确认")
            status_label.setObjectName("statusPending")
        layout.addWidget(status_label, 0, Qt.AlignTop)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.schedule_id)
        super().mousePressEvent(event)
