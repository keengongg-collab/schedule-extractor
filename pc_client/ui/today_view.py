# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
今日页面
显示：当前日期/星期、下一项日程、今日日程列表（含待确认标记）
"""
from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from pc_client.widgets.schedule_card import ScheduleCard

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class TodayView(QWidget):
    """今日日程页"""

    def __init__(self, provider, on_schedule_clicked, on_export=None, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.on_schedule_clicked = on_schedule_clicked
        self.on_export = on_export
        self._build_ui()
        self.refresh()

    # ===== UI =====

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # 头部：日期 + 刷新
        header = QVBoxLayout()
        self.today_label = QLabel()
        self.today_label.setObjectName("pageTitle")
        header.addWidget(self.today_label)
        self.weekday_label = QLabel()
        self.weekday_label.setObjectName("weekdayTitle")
        header.addWidget(self.weekday_label)

        # 导出 Excel 按钮（回调由主窗口提供）
        if self.on_export:
            export_btn = QPushButton("导出 Excel")
            export_btn.setObjectName("ghostButton")
            export_btn.clicked.connect(self.on_export)
            header.addWidget(export_btn, 0, Qt.AlignRight)

        layout.addLayout(header)

        # 下一项日程
        self.next_box = QWidget()
        self.next_box.setObjectName("nextCard")
        next_layout = QVBoxLayout(self.next_box)
        next_layout.setContentsMargins(18, 14, 18, 14)
        next_layout.setSpacing(4)
        hint = QLabel("下一项")
        hint.setObjectName("nextHint")
        self.next_title = QLabel()
        self.next_title.setObjectName("nextTitle")
        self.next_sub = QLabel()
        self.next_sub.setObjectName("nextSub")
        next_layout.addWidget(hint)
        next_layout.addWidget(self.next_title)
        next_layout.addWidget(self.next_sub)
        layout.addWidget(self.next_box)

        # 今日安排列表（滚动区）
        list_title = QLabel("今日安排")
        list_title.setObjectName("sectionTitle")
        layout.addWidget(list_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 8, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()
        scroll.setWidget(self.list_widget)
        layout.addWidget(scroll, 1)

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setObjectName("ghostButton")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn, 0, Qt.AlignRight)

    # ===== 数据 =====

    def refresh(self):
        today = date.today()
        self.today_label.setText(f"{today.year}年{today.month}月{today.day}日")
        self.weekday_label.setText(WEEKDAYS[today.weekday()])

        try:
            schedules = self.provider.get_day(today.isoformat())
        except Exception as e:
            self.today_label.setText(f"{today.year}年{today.month}月{today.day}日（加载失败：{e}）")
            schedules = []

        # 下一项：取今天尚未开始的最近日程
        now = datetime.now().strftime("%H:%M")
        upcoming = [s for s in schedules if (s.get("start_time") or "99:99") >= now]
        if upcoming:
            first = upcoming[0]
            self.next_title.setText(f"{first.get('start_time') or '--:--'}  {first.get('name') or ''}")
            sub = " · ".join([p for p in (first.get("location"), first.get("remark")) if p])
            self.next_sub.setText(sub or "—")
        else:
            self.next_title.setText("今天没有剩余日程")
            self.next_sub.setText("可以安排点新事情 ✨")

        # 清空旧卡片
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not schedules:
            empty = QLabel("今天没有日程安排")
            empty.setObjectName("emptyText")
            self.list_layout.addWidget(empty)
        else:
            for s in schedules:
                card = ScheduleCard(s)
                card.clicked.connect(self.on_schedule_clicked)
                self.list_layout.addWidget(card)
        self.list_layout.addStretch()
