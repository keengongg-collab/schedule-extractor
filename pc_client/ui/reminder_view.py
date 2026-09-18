# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
提醒管理页面
- 展示提醒列表（日程名称 / 日期时间 / 提前量 / 自定义文案）
- 添加提醒：选择日程 + 提前 5/15/30/60 分钟（或自定义）
- 删除提醒
后台另有 NotificationWorker 轮询到点触发桌面通知（见 services/notification_service.py）
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# 预置提前量选项（分钟）
ADVANCE_PRESETS = [(5, "5 分钟"), (15, "15 分钟"), (30, "30 分钟"), (60, "1 小时")]

# 选择日程的时间窗口（默认拉取较宽范围覆盖全年）
RANGE_START = "2000-01-01"
RANGE_END = "2099-12-31"


class ReminderView(QWidget):
    """提醒管理页"""

    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self.provider = provider
        self._reminders = []
        self._build_ui()
        self.refresh()

    # ===== UI =====

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("提醒管理")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        refresh_btn = QPushButton("刷新")
        refresh_btn.setObjectName("ghostButton")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        self.summary = QLabel()
        self.summary.setObjectName("sectionTitle")
        layout.addWidget(self.summary)

        # 提醒列表（滚动区）
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

        # 添加提醒表单
        form = QFrame()
        form.setObjectName("dayPanel")
        form_layout = QHBoxLayout(form)
        form_layout.setContentsMargins(14, 12, 14, 12)
        form_layout.setSpacing(10)

        form_layout.addWidget(QLabel("添加提醒"))

        self.schedule_combo = QComboBox()
        self.schedule_combo.setMinimumWidth(260)
        form_layout.addWidget(self.schedule_combo, 1)

        form_layout.addWidget(QLabel("提前"))
        self.advance_combo = QComboBox()
        self.advance_combo.addItems([label for _, label in ADVANCE_PRESETS])
        self.advance_combo.addItem("自定义")
        self.advance_combo.currentIndexChanged.connect(self._on_advance_changed)
        form_layout.addWidget(self.advance_combo)

        self.advance_spin = QSpinBox()
        self.advance_spin.setRange(1, 10080)  # 1 分钟 ~ 7 天
        self.advance_spin.setValue(15)
        self.advance_spin.setSuffix(" 分钟")
        self.advance_spin.setVisible(False)
        form_layout.addWidget(self.advance_spin)

        self.message_edit = QLineEdit()
        self.message_edit.setPlaceholderText("自定义提醒文案（可选）")
        self.message_edit.setMinimumWidth(200)
        form_layout.addWidget(self.message_edit)

        add_btn = QPushButton("添加")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._add_reminder)
        form_layout.addWidget(add_btn)

        layout.addWidget(form)

    # ===== 数据 =====

    def _load_schedule_options(self):
        """刷新"选择日程"下拉框"""
        current_id = self.schedule_combo.currentData()
        self.schedule_combo.blockSignals(True)
        self.schedule_combo.clear()
        try:
            schedules = self.provider.get_range(RANGE_START, RANGE_END)
        except Exception as e:
            QMessageBox.warning(self, "加载日程失败", str(e))
            schedules = []
        for s in schedules:
            label = "{} {} {}{}".format(
                s.get("duty_date") or "",
                s.get("start_time") or "--:--",
                s.get("name") or "未命名",
                f" · {s.get('location')}" if s.get("location") else "",
            )
            self.schedule_combo.addItem(label, s.get("id"))
        if current_id is not None:
            idx = self.schedule_combo.findData(current_id)
            if idx >= 0:
                self.schedule_combo.setCurrentIndex(idx)
        self.schedule_combo.blockSignals(False)

    def refresh(self):
        try:
            self._reminders = self.provider.get_reminders()
        except Exception as e:
            self.summary.setText(f"加载提醒列表失败：{e}")
            self._reminders = []
        self._load_schedule_options()
        self._render()

    def _render(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        total = len(self._reminders)
        self.summary.setText(f"共 {total} 条提醒（到点自动弹出桌面通知）" if total else "暂无提醒，可在下方添加")

        if not self._reminders:
            empty = QLabel("还没有设置任何提醒")
            empty.setObjectName("emptyText")
            empty.setAlignment(Qt.AlignCenter)
            self.list_layout.addWidget(empty)
        else:
            for r in self._reminders:
                self.list_layout.addWidget(self._build_reminder_row(r))
        self.list_layout.addStretch()

    def _build_reminder_row(self, r: dict) -> QWidget:
        card = QFrame()
        card.setObjectName("scheduleCard")
        row = QHBoxLayout(card)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(2)
        name_label = QLabel(r.get("name") or "未命名日程")
        name_label.setObjectName("cardTitle")
        info.addWidget(name_label)

        time_text = "{} {} - {}".format(
            r.get("duty_date") or "--", r.get("start_time") or "--:--", r.get("end_time") or "--:--",
        )
        if r.get("location"):
            time_text += f" · {r.get('location')}"
        time_label = QLabel(time_text)
        time_label.setObjectName("cardSub")
        info.addWidget(time_label)

        advance_text = f"提前 {r.get('advance_minutes')} 分钟"
        if r.get("custom_message"):
            advance_text += f"（{r.get('custom_message')}）"
        advance_label = QLabel(advance_text)
        advance_label.setObjectName("cardSub")
        info.addWidget(advance_label)

        row.addLayout(info, 1)

        del_btn = QPushButton("删除")
        del_btn.setObjectName("ghostButton")
        reminder_id = r.get("id")
        del_btn.clicked.connect(lambda checked=False, rid=reminder_id: self._delete_reminder(rid))
        row.addWidget(del_btn, 0, Qt.AlignTop)
        return card

    # ===== 交互 =====

    def _on_advance_changed(self, index):
        """选择"自定义"时显示分钟输入框"""
        is_custom = self.advance_combo.itemText(index) == "自定义"
        self.advance_spin.setVisible(is_custom)

    def _advance_minutes(self) -> int:
        index = self.advance_combo.currentIndex()
        if index < len(ADVANCE_PRESETS):
            return ADVANCE_PRESETS[index][0]
        return self.advance_spin.value()

    def _add_reminder(self):
        schedule_id = self.schedule_combo.currentData()
        if not schedule_id:
            QMessageBox.warning(self, "提示", "请先选择要提醒的日程")
            return
        try:
            self.provider.create_reminder(
                schedule_id,
                advance_minutes=self._advance_minutes(),
                custom_message=self.message_edit.text().strip(),
            )
        except Exception as e:
            QMessageBox.critical(self, "添加失败", str(e))
            return
        self.message_edit.clear()
        self.refresh()

    def _delete_reminder(self, reminder_id: int):
        ret = QMessageBox.question(self, "删除提醒", "确定删除这条提醒吗？", QMessageBox.Yes | QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        try:
            self.provider.delete_reminder(reminder_id)
        except Exception as e:
            QMessageBox.critical(self, "删除失败", str(e))
            return
        self.refresh()
