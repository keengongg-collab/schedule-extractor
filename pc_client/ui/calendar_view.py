# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
日历页面
支持日/周/月三种视图：月历组件 + 周列表 + 日列表，可切换与翻页
"""
from datetime import date, timedelta

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pc_client.utils.dates import (
    WEEKDAY_CN,
    iso,
    month_start,
    month_end,
    week_start,
    week_end,
)
from pc_client.widgets.calendar import MonthCalendar
from pc_client.widgets.schedule_card import ScheduleCard

VIEW_NAMES = ["日视图", "周视图", "月视图"]


class CalendarView(QWidget):
    """日历页：日/周/月视图切换"""

    scheduleClicked = Signal(int)

    def __init__(self, provider, on_schedule_clicked, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.on_schedule_clicked = on_schedule_clicked
        self.mode = "month"
        self.anchor = date.today()  # 当前聚焦日期（日视图/周视图基准）

        self._build_ui()
        self._refresh()

    # ===== UI =====

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # 顶部工具栏
        toolbar = QHBoxLayout()
        self.prev_btn = QPushButton("‹")
        self.next_btn = QPushButton("›")
        today_btn = QPushButton("今天")
        for b in (self.prev_btn, self.next_btn):
            b.setObjectName("navButton")
        today_btn.setObjectName("ghostButton")
        self.range_label = QLabel()
        self.range_label.setObjectName("rangeTitle")

        self.view_combo = QComboBox()
        self.view_combo.addItems(VIEW_NAMES)
        self.view_combo.setCurrentIndex(2)  # 默认月视图
        self.view_combo.setObjectName("viewCombo")

        toolbar.addWidget(self.prev_btn)
        toolbar.addWidget(self.next_btn)
        toolbar.addWidget(today_btn)
        toolbar.addSpacing(12)
        toolbar.addWidget(self.range_label, 1)
        toolbar.addWidget(QLabel("视图"))
        toolbar.addWidget(self.view_combo)
        layout.addLayout(toolbar)

        # 内容区：月历（左侧）+ 详情列表（右侧）
        content = QHBoxLayout()
        content.setSpacing(16)

        self.calendar = MonthCalendar()
        content.addWidget(self.calendar, 1)

        self.detail_panel = QFrame()
        self.detail_panel.setObjectName("dayPanel")
        panel_layout = QVBoxLayout(self.detail_panel)
        panel_layout.setContentsMargins(14, 12, 14, 12)
        self.detail_title = QLabel()
        self.detail_title.setObjectName("sectionTitle")
        panel_layout.addWidget(self.detail_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.detail_list = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_list)
        self.detail_layout.setContentsMargins(0, 0, 4, 0)
        self.detail_layout.setSpacing(8)
        self.detail_layout.addStretch()
        scroll.setWidget(self.detail_list)
        panel_layout.addWidget(scroll, 1)
        content.addWidget(self.detail_panel, 1)

        layout.addLayout(content, 1)

        # 信号
        self.prev_btn.clicked.connect(lambda: self._shift(-1))
        self.next_btn.clicked.connect(lambda: self._shift(1))
        today_btn.clicked.connect(self._go_today)
        self.view_combo.currentIndexChanged.connect(self._on_mode_change)
        self.calendar.dateClicked.connect(self._on_date_clicked)
        self.calendar.monthChanged.connect(lambda _qd: self._refresh())

    # ===== 数据 =====

    def _refresh(self):
        self.range_label.setText(self._range_title())
        self.calendar.set_events(self._fetch_event_dates())
        self._render_detail()

    def _fetch_event_dates(self) -> list:
        """当月有日程的日期列表（用于月历圆点）"""
        try:
            rows = self.provider.get_range(iso(month_start(self.anchor)), iso(month_end(self.anchor)))
            return sorted({r["duty_date"] for r in rows})
        except Exception:
            return []

    def _current_day(self) -> date:
        """当前聚焦的日期：日视图=anchor，周/月视图=anchor 归位到周一/月首"""
        if self.mode == "day":
            return self.anchor
        if self.mode == "week":
            return week_start(self.anchor)
        return month_start(self.anchor)

    def _load_range(self, start: date, end: date) -> list:
        try:
            return self.provider.get_range(iso(start), iso(end))
        except Exception:
            return []

    def _render_detail(self):
        # 清空
        while self.detail_layout.count():
            item = self.detail_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if self.mode == "day":
            day = self.anchor
            title = f"{day.year}年{day.month}月{day.day}日 · {WEEKDAY_CN(day)}"
            rows = self._load_range(day, day)
        elif self.mode == "week":
            start, end = week_start(self.anchor), week_end(self.anchor)
            title = f"{start.month}月{start.day}日 - {end.month}月{end.day}日"
            rows = self._load_range(start, end)
        else:
            start, end = month_start(self.anchor), month_end(self.anchor)
            title = f"{start.year}年{start.month}月 全部日程"
            rows = self._load_range(start, end)

        self.detail_title.setText(title)

        if not rows:
            empty = QLabel("暂无日程")
            empty.setObjectName("emptyText")
            empty.setAlignment(Qt.AlignCenter)
            self.detail_layout.addWidget(empty)
        else:
            for s in rows:
                card = ScheduleCard(s)
                card.clicked.connect(self.on_schedule_clicked)
                self.detail_layout.addWidget(card)
        self.detail_layout.addStretch()

    # ===== 交互 =====

    def _on_mode_change(self, index):
        self.mode = ["day", "week", "month"][index]
        self.calendar.setVisible(self.mode == "month")
        self._refresh()

    def _on_date_clicked(self, qd: QDate):
        self.anchor = date(qd.year(), qd.month(), qd.day())
        self.mode = "day"
        self.view_combo.setCurrentIndex(0)
        self._refresh()

    def _shift(self, delta: int):
        if self.mode == "day":
            self.anchor += timedelta(days=delta)
        elif self.mode == "week":
            self.anchor += timedelta(weeks=delta)
        else:
            first = month_start(self.anchor)
            if first.month + delta > 12:
                new = date(first.year + 1, first.month + delta - 12, 1)
            elif first.month + delta < 1:
                new = date(first.year - 1, first.month + delta + 12, 1)
            else:
                new = date(first.year, first.month + delta, 1)
            self.anchor = new
            self.calendar.set_month(new.year, new.month)
        self._refresh()

    def _go_today(self):
        self.anchor = date.today()
        self.calendar.set_month(self.anchor.year, self.anchor.month)
        self._refresh()

    def _range_title(self) -> str:
        if self.mode == "day":
            return f"{self.anchor.year}年{self.anchor.month}月"
        if self.mode == "week":
            start, end = week_start(self.anchor), week_end(self.anchor)
            return f"{start.year}年{start.month}月{start.day}日 - {end.month}月{end.day}日"
        first = month_start(self.anchor)
        return f"{first.year}年{first.month}月"
