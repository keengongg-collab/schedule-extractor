# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
主窗口
左侧导航 + 右侧 QStackedWidget 内容区；负责页面注册与统一样式
"""
import pathlib

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from pc_client.ui.ai_assistant import AiAssistant
from pc_client.ui.calendar_view import CalendarView
from pc_client.ui.import_view import ImportView
from pc_client.ui.reminder_view import ReminderView
from pc_client.ui.schedule_detail import ScheduleDetailDialog
from pc_client.ui.schedules_view import SchedulesView
from pc_client.ui.settings_view import SettingsView
from pc_client.ui.sidebar import Sidebar
from pc_client.ui.today_view import TodayView

# ===== 全局样式（现代桌面软件风格）=====
APP_QSS = """
* {
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    color: #2b2f36;
}
QMainWindow, QWidget#root {
    background: #f5f7fa;
}
/* ---- 侧边栏 ---- */
QWidget#sidebar {
    background: #ffffff;
    border-right: 1px solid #e6e9ef;
}
QLabel#brand {
    font-size: 19px;
    font-weight: 700;
    color: #1e5eff;
    padding-left: 6px;
}
QLabel#brandSub {
    font-size: 12px;
    color: #8a94a6;
    padding-left: 6px;
}
QPushButton#navButton {
    text-align: left;
    padding: 9px 12px;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: #4a5261;
}
QPushButton#navButton:hover {
    background: #f0f3f9;
}
QPushButton#navButton:checked {
    background: #e8f0ff;
    color: #1e5eff;
    font-weight: 600;
}
/* ---- 标题 ---- */
QLabel#pageTitle {
    font-size: 24px;
    font-weight: 700;
    color: #1f2430;
}
QLabel#weekdayTitle {
    font-size: 15px;
    color: #8a94a6;
}
QLabel#rangeTitle {
    font-size: 16px;
    font-weight: 600;
    color: #1f2430;
}
QLabel#sectionTitle {
    font-size: 15px;
    font-weight: 600;
    color: #1f2430;
}
QLabel#emptyText {
    color: #a0a8b8;
    padding: 24px;
    font-size: 14px;
}
/* ---- 日程卡片 ---- */
QFrame#scheduleCard {
    background: #ffffff;
    border: 1px solid #e6e9ef;
    border-radius: 10px;
}
QFrame#scheduleCard:hover {
    border-color: #bcd2ff;
    background: #fbfdff;
}
QLabel#cardTime { font-size: 14px; font-weight: 600; color: #1e5eff; }
QLabel#cardTimeSub { font-size: 11px; color: #a0a8b8; }
QLabel#cardTitle { font-size: 14px; font-weight: 600; color: #1f2430; }
QLabel#cardSub { font-size: 12px; color: #8a94a6; }
QLabel#statusConfirmed { color: #1f9d55; font-size: 12px; }
QLabel#statusPending { color: #d97706; font-size: 12px; }
/* ---- 下一项卡片 ---- */
QWidget#nextCard {
    background: linear-gradient(120deg, #1e5eff, #5b8cff);
    border-radius: 12px;
}
QLabel#nextHint { color: #cfe0ff; font-size: 12px; }
QLabel#nextTitle { color: #ffffff; font-size: 20px; font-weight: 700; }
QLabel#nextSub { color: #dbe8ff; font-size: 13px; }
/* ---- 月历 ---- */
QPushButton#navButton {
    border: 1px solid #e6e9ef;
    border-radius: 6px;
    background: #ffffff;
    min-width: 28px;
    min-height: 26px;
}
QPushButton#navButton:hover { border-color: #1e5eff; color: #1e5eff; }
QLabel#monthTitle { font-size: 16px; font-weight: 700; color: #1f2430; }
QLabel#weekdayHeader { color: #8a94a6; font-size: 12px; }
QPushButton#dateButton {
    border: none;
    border-radius: 6px;
    background: transparent;
    color: #2b2f36;
}
QPushButton#dateButton:hover { background: #eef3ff; }
QPushButton#dateButton[isToday="true"] {
    background: #1e5eff;
    color: #ffffff;
    font-weight: 700;
}
QPushButton#dateButton[hasEvent="true"] {
    border-bottom: 3px solid #5b8cff;
}
QPushButton#dateButton[isToday="true"][hasEvent="true"] {
    border-bottom: 3px solid #ffffff;
}
/* ---- 按钮 ---- */
QPushButton#ghostButton {
    border: 1px solid #d5dbe6;
    border-radius: 8px;
    background: #ffffff;
    padding: 6px 16px;
    color: #4a5261;
}
QPushButton#ghostButton:hover { border-color: #1e5eff; color: #1e5eff; }
QPushButton#primaryButton {
    border: none;
    border-radius: 8px;
    background: #1e5eff;
    color: #ffffff;
    padding: 7px 18px;
    font-weight: 600;
}
QPushButton#primaryButton:hover { background: #0f4be0; }
QPushButton#primaryButton:disabled { background: #c6d4f5; color: #eef3ff; }
/* ---- 导入页 ---- */
QFrame#dropZone {
    border: 2px dashed #c3d2ef;
    border-radius: 12px;
    background: #fbfdff;
}
QFrame#dropZone:hover { border-color: #1e5eff; }
QLabel#dropTip { font-size: 15px; color: #4a5261; }
QLabel#dropSub { font-size: 12px; color: #a0a8b8; }
QLabel#importSummary { font-size: 14px; font-weight: 600; color: #1e5eff; }
QTableWidget {
    background: #ffffff;
    border: 1px solid #e6e9ef;
    border-radius: 10px;
    gridline-color: #eef1f6;
}
QTableWidget::item { padding: 4px 6px; }
QHeaderView::section {
    background: #f0f3f9;
    border: none;
    border-bottom: 1px solid #e6e9ef;
    padding: 7px 6px;
    font-weight: 600;
    color: #4a5261;
}
QListWidget {
    background: #ffffff;
    border: 1px solid #e6e9ef;
    border-radius: 10px;
    padding: 4px;
}
/* ---- AI 助手 ---- */
QFrame#bubbleAi {
    background: #ffffff;
    border: 1px solid #e6e9ef;
    border-radius: 10px;
    max-width: 520px;
}
QFrame#bubbleUser {
    background: #e8f0ff;
    border: 1px solid #d6e4ff;
    border-radius: 10px;
}
QPushButton#candidateButton {
    text-align: left;
    border: 1px solid #d5dbe6;
    border-radius: 8px;
    background: #ffffff;
    padding: 8px 12px;
    color: #2b2f36;
}
QPushButton#candidateButton:hover { border-color: #1e5eff; }
QPushButton#dangerButton {
    border: none;
    border-radius: 8px;
    background: #e5484d;
    color: #ffffff;
    padding: 7px 18px;
    font-weight: 600;
}
QPushButton#dangerButton:hover { background: #cf3a3f; }
QPlainTextEdit {
    border: 1px solid #d5dbe6;
    border-radius: 10px;
    padding: 8px 12px;
    background: #ffffff;
}
QPlainTextEdit:focus { border-color: #1e5eff; }
QComboBox#viewCombo {
    border: 1px solid #d5dbe6;
    border-radius: 8px;
    padding: 5px 10px;
    background: #ffffff;
}
/* ---- 详情弹窗 ---- */
QLabel#detailTitle { font-size: 20px; font-weight: 700; color: #1f2430; }
QLabel#detailStatus { color: #8a94a6; }
QFrame#dayPanel {
    background: #ffffff;
    border: 1px solid #e6e9ef;
    border-radius: 12px;
}
QLineEdit, QTextEdit {
    border: 1px solid #d5dbe6;
    border-radius: 8px;
    padding: 6px 10px;
    background: #ffffff;
    selection-background-color: #1e5eff;
}
QLineEdit:focus, QTextEdit:focus { border-color: #1e5eff; }
QLineEdit:read-only, QTextEdit:read-only { background: #f5f7fa; color: #4a5261; }
QScrollBar:vertical { background: transparent; width: 8px; }
QScrollBar::handle:vertical { background: #c9d2e0; border-radius: 4px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #a9b6c9; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
"""


class MainWindow(QMainWindow):
    """应用主窗口"""

    def __init__(self, provider):
        super().__init__()
        self.provider = provider
        self.setWindowTitle("AI Schedule · 轻量化AI日程管理")
        self.resize(1120, 720)
        self.setMinimumSize(940, 620)

        self._build_ui()
        self._go_to("today")

    # ===== UI =====

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 左侧导航 + 内容区
        self.sidebar = Sidebar()
        self.stack = QStackedWidget()

        self.today_view = TodayView(self.provider, self._open_detail, self._export_excel)
        self.calendar_view = CalendarView(self.provider, self._open_detail)
        self.schedules_view = SchedulesView(self.provider, self._open_detail)
        self.import_view = ImportView(self.provider)
        self.reminder_view = ReminderView(self.provider)
        self.ai_assistant = AiAssistant(self.provider)
        self.settings_view = SettingsView(self.provider)

        self.stack.addWidget(self.today_view)        # 0 today
        self.stack.addWidget(self.calendar_view)     # 1 calendar
        self.stack.addWidget(self.schedules_view)    # 2 schedules
        self.stack.addWidget(self.import_view)       # 3 import
        self.stack.addWidget(self.reminder_view)     # 4 reminder
        self.stack.addWidget(self.ai_assistant)      # 5 ai
        self.stack.addWidget(self.settings_view)     # 6 settings

        page_index = {
            "today": 0, "calendar": 1, "schedules": 2, "import": 3,
            "reminder": 4, "ai": 5, "settings": 6,
        }
        self._page_index = page_index

        self.sidebar.pageSelected.connect(self._go_to)

        body = QHBoxLayoutWrapper()
        self._body_layout = body.layout
        self._body_layout.addWidget(self.sidebar)
        self._body_layout.addWidget(self.stack, 1)

        root_layout.addLayout(self._body_layout)
        self.setCentralWidget(root)

    # ===== 页面切换 =====

    def _go_to(self, key: str):
        index = self._page_index.get(key, 0)
        self.stack.setCurrentIndex(index)
        self.sidebar.set_current(key)
        # 进入页面时刷新数据
        if key == "today":
            self.today_view.refresh()
        elif key == "calendar":
            self.calendar_view._refresh()
        elif key == "schedules":
            self.schedules_view.refresh()
        elif key == "reminder":
            self.reminder_view.refresh()
        elif key == "settings":
            self.settings_view.refresh()

    # ===== 日程详情 =====

    def _open_detail(self, schedule_id: int):
        try:
            schedule = self.provider.get_schedule(schedule_id)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "加载失败", str(e))
            return
        dialog = ScheduleDetailDialog(self.provider, schedule, self)
        dialog.exec()
        # 详情可能修改/删除数据，刷新当前页
        self._refresh_current()

    def _refresh_current(self):
        current = self.stack.currentIndex()
        if current == 0:
            self.today_view.refresh()
        elif current == 1:
            self.calendar_view._refresh()
        elif current == 2:
            self.schedules_view.refresh()
        elif current == 4:
            self.reminder_view.refresh()

    # ===== 导出 Excel =====

    def _export_excel(self):
        """导出日程到 Excel（今日页/设置页共用）：导出当月全部日程"""
        from datetime import date

        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from pc_client.excel_export import export_to_excel

        today = date.today()
        start = f"{today.year:04d}-{today.month:02d}-01"
        if today.month == 12:
            end = f"{today.year + 1:04d}-01-01"
        else:
            end = f"{today.year:04d}-{today.month + 1:02d}-01"
        try:
            schedules = self.provider.get_range(start, end)
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"获取日程数据失败：{e}")
            return
        if not schedules:
            QMessageBox.information(self, "导出", "本月暂无日程可导出")
            return

        default_name = f"排班表_{today.strftime('%Y%m')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 Excel 文件",
            str(pathlib.Path.home() / "Desktop" / default_name),
            "Excel 文件 (*.xlsx)",
        )
        if not path:
            return
        try:
            filepath = export_to_excel(schedules, str(pathlib.Path(path).parent))
            QMessageBox.information(self, "导出完成", f"已导出 {len(schedules)} 条日程到：\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))


class QHBoxLayoutWrapper:
    """轻量包装：横向布局（避免顶部额外 import）"""

    def __init__(self):
        from PySide6.QtWidgets import QHBoxLayout
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
