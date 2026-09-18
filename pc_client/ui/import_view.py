# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
文件拖拽导入页面
拖入 PDF / DOCX / TXT → 调 /api/upload/file(dry_run) 预览 → 表格展示
→ 缺失字段提示 → 用户「全部确认」→ /api/upload/apply 落库并生成 QA
"""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

ALLOWED_EXTS = {".pdf", ".docx", ".txt"}

TABLE_HEADERS = ["姓名", "日期", "开始", "结束", "地点", "备注", "状态"]


class DropZone(QFrame):
    """拖拽放置区"""

    def __init__(self, on_files, parent=None):
        super().__init__(parent)
        self.on_files = on_files
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(96)

        layout = QVBoxLayout(self)
        tip = QLabel("将 PDF / DOCX / TXT 文件拖到此处")
        tip.setObjectName("dropTip")
        tip.setAlignment(Qt.AlignCenter)
        sub = QLabel("或点击下方按钮选择文件")
        sub.setObjectName("dropSub")
        sub.setAlignment(Qt.AlignCenter)
        layout.addStretch()
        layout.addWidget(tip)
        layout.addWidget(sub)
        layout.addStretch()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            if os.path.isfile(path) and ext in ALLOWED_EXTS:
                files.append(path)
        if files:
            self.on_files(files)


class ImportView(QWidget):
    """文件拖拽导入页"""

    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self.provider = provider
        self._files = []        # 待解析文件路径
        self._previews = []     # 解析预览结果（含 id=None）
        self._build_ui()

    # ===== UI =====

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("文件导入")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self.drop_zone = DropZone(self._add_files)
        layout.addWidget(self.drop_zone)

        btn_row = QHBoxLayout()
        self.pick_btn = QPushButton("选择文件…")
        self.pick_btn.setObjectName("ghostButton")
        self.pick_btn.clicked.connect(self._pick_files)
        self.parse_btn = QPushButton("开始解析")
        self.parse_btn.setObjectName("primaryButton")
        self.parse_btn.setEnabled(False)
        self.parse_btn.clicked.connect(self._parse)
        btn_row.addWidget(self.pick_btn)
        btn_row.addWidget(self.parse_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(110)
        layout.addWidget(self.file_list)

        # 提示条（解析结果摘要）
        self.summary = QLabel("尚未解析文件")
        self.summary.setObjectName("importSummary")
        layout.addWidget(self.summary)

        # 预览表格
        self.table = QTableWidget(0, len(TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        # 确认按钮行
        action_row = QHBoxLayout()
        self.apply_btn = QPushButton("全部确认，写入日历")
        self.apply_btn.setObjectName("primaryButton")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setObjectName("ghostButton")
        self.clear_btn.clicked.connect(self._clear)
        action_row.addWidget(self.apply_btn)
        action_row.addWidget(self.clear_btn)
        action_row.addStretch()
        layout.addLayout(action_row)

    # ===== 文件收集 =====

    def _add_files(self, paths: list):
        for p in paths:
            if p not in self._files:
                self._files.append(p)
                self.file_list.addItem(os.path.basename(p))
        self.parse_btn.setEnabled(bool(self._files))
        self.summary.setText(f"已选择 {len(self._files)} 个文件，点击「开始解析」")

    def _pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择排班文档", "",
            "文档文件 (*.pdf *.docx *.txt);;所有文件 (*)",
        )
        if paths:
            self._add_files(paths)

    # ===== 解析 =====

    def _parse(self):
        self.parse_btn.setEnabled(False)
        self.summary.setText("正在解析…")
        previews, questions = [], 0
        try:
            for path in self._files:
                result = self.provider.upload_file(path, dry_run=True)
                for s in result.get("schedules", []):
                    s["missing_fields"] = s.get("missing_fields") or []
                    previews.append(s)
                questions += len(result.get("questions", []))
        except Exception as e:
            QMessageBox.critical(self, "解析失败", str(e))
            self.summary.setText("解析失败")
            self.parse_btn.setEnabled(True)
            return

        self._previews = previews
        missing_count = sum(1 for s in previews if s.get("missing_fields"))
        self._render_table(previews)
        if previews:
            msg = f"AI 已识别 {len(previews)} 条日程"
            if missing_count:
                msg += f"，其中 {missing_count} 条信息不完整，确认后可在「提醒」页补充"
            self.summary.setText(msg)
        else:
            self.summary.setText("未识别出日程，请检查文档格式")
        self.apply_btn.setEnabled(bool(previews))

    def _render_table(self, previews: list):
        self.table.setRowCount(len(previews))
        for row, s in enumerate(previews):
            values = [
                s.get("name", ""), s.get("duty_date", ""),
                s.get("start_time") or "", s.get("end_time") or "",
                s.get("location") or "", s.get("remark") or "",
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
            status = "缺失" if s.get("missing_fields") else "完整"
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(Qt.red if status == "缺失" else Qt.darkGreen)
            self.table.setItem(row, len(TABLE_HEADERS) - 1, status_item)
        self.table.resizeColumnsToContents()

    # ===== 确认导入 =====

    def _apply(self):
        if not self._previews:
            return
        ret = QMessageBox.question(
            self, "确认导入",
            f"将把 {len(self._previews)} 条日程写入日历，确定继续吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        try:
            result = self.provider.apply_schedules(self._previews, source_type="upload")
        except Exception as e:
            QMessageBox.critical(self, "确认失败", str(e))
            return
        saved = result.get("total", 0)
        questions = len(result.get("questions", []))
        msg = f"已写入 {saved} 条日程"
        if questions:
            msg += f"，另有 {questions} 条缺失信息待补充（见「提醒」页）"
        QMessageBox.information(self, "导入完成", msg)
        self._clear()

    def _clear(self):
        self._files = []
        self._previews = []
        self.file_list.clear()
        self.table.setRowCount(0)
        self.summary.setText("尚未解析文件")
        self.parse_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
