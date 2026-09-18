# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
设置页
- 后端连接信息：地址 / 模式（Mock 或真实 API）/ 健康检查
- 导出 Excel（全部日程）
"""
import os
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pc_client.excel_export import export_to_excel

# 导出默认取全部日程的时间窗口
RANGE_START = "2000-01-01"
RANGE_END = "2099-12-31"


class SettingsView(QWidget):
    """设置页"""

    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self.provider = provider
        self._build_ui()
        self.refresh()

    # ===== UI =====

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("设置")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # ---- 连接信息 ----
        conn = QFrame()
        conn.setObjectName("dayPanel")
        conn_layout = QVBoxLayout(conn)
        conn_layout.setContentsMargins(16, 14, 16, 14)
        conn_layout.setSpacing(8)

        section = QLabel("后端连接")
        section.setObjectName("sectionTitle")
        conn_layout.addWidget(section)

        self.mode_label = QLabel()
        self.mode_label.setObjectName("cardSub")
        conn_layout.addWidget(self.mode_label)

        self.addr_label = QLabel()
        self.addr_label.setObjectName("cardSub")
        conn_layout.addWidget(self.addr_label)

        self.health_label = QLabel()
        self.health_label.setObjectName("cardSub")
        conn_layout.addWidget(self.health_label)

        health_btn = QPushButton("重新检测连接")
        health_btn.setObjectName("ghostButton")
        health_btn.clicked.connect(self.refresh)
        conn_layout.addWidget(health_btn, 0, Qt.AlignLeft)

        layout.addWidget(conn)

        # ---- 导出 ----
        export_box = QFrame()
        export_box.setObjectName("dayPanel")
        export_layout = QVBoxLayout(export_box)
        export_layout.setContentsMargins(16, 14, 16, 14)
        export_layout.setSpacing(8)

        section2 = QLabel("数据导出")
        section2.setObjectName("sectionTitle")
        export_layout.addWidget(section2)

        tip = QLabel("将全部日程导出为 Excel（.xlsx）文件，适合存档或打印。")
        tip.setObjectName("cardSub")
        export_layout.addWidget(tip)

        self.export_btn = QPushButton("导出 Excel")
        self.export_btn.setObjectName("primaryButton")
        self.export_btn.clicked.connect(self._export_excel)
        export_layout.addWidget(self.export_btn, 0, Qt.AlignLeft)

        layout.addWidget(export_box)

        # ---- 说明 ----
        note = QFrame()
        note.setObjectName("dayPanel")
        note_layout = QVBoxLayout(note)
        note_layout.setContentsMargins(16, 14, 16, 14)
        note_layout.setSpacing(8)

        section3 = QLabel("运行模式说明")
        section3.setObjectName("sectionTitle")
        note_layout.addWidget(section3)

        note_text = (
            "· 环境变量 USE_MOCK=1（默认）：使用内置示例数据预览界面，不访问后端。\n"
            "· 环境变量 USE_MOCK=0：连接真实后端服务（默认 http://127.0.0.1:5000，"
            "可用 API_BASE 覆盖）。\n"
            "· 桌面通知依赖 Windows 通知中心；提醒轮询间隔由 PC_NOTIFY_INTERVAL 控制（秒）。"
        )
        note_label = QLabel(note_text)
        note_label.setObjectName("cardSub")
        note_label.setWordWrap(True)
        note_layout.addWidget(note_label)

        layout.addWidget(note)
        layout.addStretch()

    # ===== 数据 =====

    def refresh(self):
        is_mock = not hasattr(self.provider, "base_url")
        if is_mock:
            self.mode_label.setText("当前模式：Mock 预览模式（USE_MOCK=1，数据不落库）")
            self.addr_label.setText("数据来源：内置示例数据")
            self.health_label.setText("连接状态：未连接后端（预览模式）")
            return

        self.mode_label.setText("当前模式：真实后端模式（USE_MOCK=0）")
        self.addr_label.setText(f"后端地址：{self.provider.base_url}")
        try:
            info = self.provider.health_check()
            self.health_label.setText(f"连接状态：正常（版本 {info.get('version') or '未知'}）")
        except Exception as e:
            self.health_label.setText(f"连接状态：失败（{e}）")

    # ===== 导出 =====

    def _export_excel(self):
        try:
            schedules = self.provider.get_range(RANGE_START, RANGE_END)
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"获取日程数据失败：{e}")
            return
        if not schedules:
            QMessageBox.information(self, "导出", "当前没有可导出的日程")
            return

        default_name = f"排班表_{date.today().strftime('%Y%m%d')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 Excel 文件", os.path.join(os.path.expanduser("~"), "Desktop", default_name),
            "Excel 文件 (*.xlsx)",
        )
        if not path:
            return
        try:
            filepath = export_to_excel(schedules, os.path.dirname(path) or ".")
            QMessageBox.information(self, "导出完成", f"已导出 {len(schedules)} 条日程到：\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
