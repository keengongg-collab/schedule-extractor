# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
日程列表页
全部日程表格（按日期排序），支持姓名筛选、点击行查看详情
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

HEADERS = ["姓名", "日期", "开始", "结束", "地点", "备注", "状态"]

# 拉取全部日程的时间窗口
RANGE_START = "2000-01-01"
RANGE_END = "2099-12-31"


class SchedulesView(QWidget):
    """全部日程列表页"""

    def __init__(self, provider, on_schedule_clicked, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.on_schedule_clicked = on_schedule_clicked
        self._rows = []
        self._row_ids = []
        self._build_ui()
        self.refresh()

    # ===== UI =====

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("全部日程")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("按姓名筛选…")
        self.filter_edit.setMaximumWidth(220)
        self.filter_edit.textChanged.connect(self._apply_filter)
        header.addWidget(self.filter_edit)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setObjectName("ghostButton")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        self.summary = QLabel()
        self.summary.setObjectName("sectionTitle")
        layout.addWidget(self.summary)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        layout.addWidget(self.table, 1)

    # ===== 数据 =====

    def refresh(self):
        try:
            self._rows = self.provider.get_range(RANGE_START, RANGE_END)
        except Exception as e:
            self.summary.setText(f"加载日程列表失败：{e}")
            self._rows = []
        self._apply_filter()

    def _apply_filter(self):
        keyword = self.filter_edit.text().strip()
        rows = [r for r in self._rows if not keyword or keyword in (r.get("name") or "")]
        self._render(rows)

    def _render(self, rows: list):
        self.summary.setText(f"共 {len(rows)} 条日程（双击行查看详情）" if rows else "暂无日程")
        self.table.setRowCount(len(rows))
        self._row_ids = [r.get("id") for r in rows]
        for row, s in enumerate(rows):
            values = [
                s.get("name") or "",
                s.get("duty_date") or "",
                s.get("start_time") or "",
                s.get("end_time") or "",
                s.get("location") or "",
                s.get("remark") or "",
                "已确认" if s.get("is_confirmed") else "待确认",
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                if col == len(HEADERS) - 1:
                    item.setForeground(Qt.darkGreen if s.get("is_confirmed") else Qt.darkYellow)
                self.table.setItem(row, col, item)
        self.table.resizeColumnsToContents()

    def _on_cell_double_clicked(self, row: int, _col: int):
        if 0 <= row < len(self._row_ids) and self._row_ids[row]:
            self.on_schedule_clicked(self._row_ids[row])
