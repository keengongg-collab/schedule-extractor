# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
左侧导航栏
垂直按钮列表：今日/日历/日程/导入/提醒/AI 助手/设置
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QLabel, QPushButton, QVBoxLayout, QWidget

NAV_ITEMS = [
    ("today", "🏠  今日"),
    ("calendar", "📅  日历"),
    ("schedules", "📋  日程"),
    ("import", "📥  导入"),
    ("reminder", "🔔  提醒"),
    ("ai", "🤖  AI 助手"),
    ("settings", "⚙️  设置"),
]


class Sidebar(QWidget):
    """左侧导航栏"""

    pageSelected = Signal(str)  # 携带页面 key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(190)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 16)
        layout.setSpacing(6)

        # 品牌标题
        brand = QLabel("AI Schedule")
        brand.setObjectName("brand")
        layout.addWidget(brand)
        sub = QLabel("AI 日程管理")
        sub.setObjectName("brandSub")
        layout.addWidget(sub)
        layout.addSpacing(16)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons = {}

        for key, text in NAV_ITEMS:
            btn = QPushButton(text)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, k=key: self.pageSelected.emit(k))
            self._group.addButton(btn)
            self._buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch()

    def set_current(self, key: str):
        """高亮当前页面对应的导航项"""
        if key in self._buttons:
            self._buttons[key].setChecked(True)
