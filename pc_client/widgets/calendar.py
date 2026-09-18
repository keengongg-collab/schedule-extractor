# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
月历组件
传统月历网格：可翻月、今天高亮、有日程的日期显示圆点、点击日期发信号
"""
from datetime import date

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

WEEKDAY_HEADERS = ["一", "二", "三", "四", "五", "六", "日"]


class MonthCalendar(QWidget):
    """月历组件"""

    dateClicked = Signal(QDate)   # 点击某个日期
    monthChanged = Signal(QDate)  # 切换月份（参数为当月 1 号）

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display = QDate.currentDate()          # 当前展示的月份
        self._event_dates = set()                    # 有日程的日期集合 "YYYY-MM-DD"
        self._date_buttons = {}

        self._build_ui()
        self._refresh()

    # ===== 对外接口 =====

    def set_events(self, dates: list):
        """设置存在日程的日期列表（YYYY-MM-DD 字符串列表），刷新圆点标记"""
        self._event_dates = set(dates)
        self._refresh_dots()

    def current_month(self) -> QDate:
        return self._display

    def set_month(self, year: int, month: int):
        """跳转到指定年月（用于外部翻页联动）"""
        self._display = QDate(year, month, 1)
        self._refresh()

    # ===== UI 构建 =====

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 顶部：上翻月 + 年月标题 + 下翻月
        header = QVBoxLayout()
        nav = QGridLayout()
        self.prev_btn = QPushButton("‹")
        self.next_btn = QPushButton("›")
        self.prev_btn.setObjectName("navButton")
        self.next_btn.setObjectName("navButton")
        self.month_label = QLabel()
        self.month_label.setObjectName("monthTitle")
        self.month_label.setAlignment(Qt.AlignCenter)

        nav.addWidget(self.prev_btn, 0, 0)
        nav.addWidget(self.month_label, 0, 1)
        nav.addWidget(self.next_btn, 0, 2)
        header.addLayout(nav)
        layout.addLayout(header)

        # 星期表头
        weekday_row = QGridLayout()
        for i, name in enumerate(WEEKDAY_HEADERS):
            label = QLabel(name)
            label.setObjectName("weekdayHeader")
            label.setAlignment(Qt.AlignCenter)
            weekday_row.addWidget(label, 0, i)
        layout.addLayout(weekday_row)

        # 日期网格（7 列，最多 6 行）
        self.grid = QGridLayout()
        self.grid.setSpacing(4)
        layout.addLayout(self.grid)

        self.prev_btn.clicked.connect(lambda: self._shift_month(-1))
        self.next_btn.clicked.connect(lambda: self._shift_month(1))

    # ===== 渲染 =====

    def _refresh(self):
        # 清空旧网格
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._date_buttons.clear()

        month_label = f"{self._display.year()} 年 {self._display.month()} 月"
        self.month_label.setText(month_label)

        first = QDate(self._display.year(), self._display.month(), 1)
        # 周一为每周第一天：Qt 周一=1
        offset = (first.dayOfWeek() - 1) % 7
        days_in_month = first.daysInMonth()

        for day in range(1, days_in_month + 1):
            qd = QDate(self._display.year(), self._display.month(), day)
            btn = QPushButton(str(day))
            btn.setObjectName("dateButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(36, 30)
            if qd == QDate.currentDate():
                btn.setProperty("isToday", True)
                btn.setStyleSheet(self.styleSheet())  # 触发属性样式刷新
            row, col = divmod(offset + day - 1, 7)
            self.grid.addWidget(btn, row, col)
            self._date_buttons[day] = btn
            btn.clicked.connect(lambda checked=False, d=qd: self.dateClicked.emit(d))

        self._refresh_dots()

    def _refresh_dots(self):
        for day, btn in self._date_buttons.items():
            key = f"{self._display.year():04d}-{self._display.month():02d}-{day:02d}"
            has_event = key in self._event_dates
            btn.setProperty("hasEvent", has_event)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _shift_month(self, delta: int):
        new_date = self._display.addMonths(delta)
        self._display = QDate(new_date.year(), new_date.month(), 1)
        self._refresh()
        self.monthChanged.emit(self._display)
