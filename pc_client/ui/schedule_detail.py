# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
日程详情弹窗
展示日程全部字段，支持：编辑、删除、确认、修改提醒
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

FIELDS = [
    ("name", "名称"),
    ("duty_date", "日期"),
    ("start_time", "开始"),
    ("end_time", "结束"),
    ("location", "地点"),
    ("remark", "备注"),
]


class ScheduleDetailDialog(QDialog):
    """日程详情/编辑对话框"""

    def __init__(self, provider, schedule: dict, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.schedule_id = schedule.get("id")
        self._schedule = dict(schedule)
        self._editing = False
        self._init_ui()
        self._load(self._schedule)
        self.setWindowTitle("日程详情")
        self.setMinimumWidth(420)

    # ===== UI 构建 =====

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title_row = QVBoxLayout()
        self.title_label = QLabel()
        self.title_label.setObjectName("detailTitle")
        title_row.addWidget(self.title_label)
        status_label = QLabel("状态")
        status_label.setObjectName("detailStatus")
        title_row.addWidget(status_label)
        layout.addLayout(title_row)

        form = QFormLayout()
        form.setSpacing(8)
        self.inputs = {}
        for key, label in FIELDS:
            if key == "remark":
                w = QTextEdit()
                w.setFixedHeight(60)
            else:
                w = QLineEdit()
            w.setReadOnly(True)
            self.inputs[key] = w
            form.addRow(QLabel(label), w)
        layout.addLayout(form)

        # 提醒设置（简化：仅显示当前提前分钟数，修改走后续 Phase 6）
        reminder_row = QFormLayout()
        self.reminder_combo = QComboBox()
        self.reminder_combo.addItems(["5 分钟", "15 分钟", "30 分钟", "1 小时", "自定义"])
        self.reminder_combo.setEnabled(False)
        reminder_row.addRow(QLabel("提醒"), self.reminder_combo)
        layout.addLayout(reminder_row)

        # 操作按钮
        btn_box = QDialogButtonBox()
        self.btn_edit = btn_box.addButton("编辑", QDialogButtonBox.ButtonRole.ActionRole)
        self.btn_confirm = btn_box.addButton("确认", QDialogButtonBox.ButtonRole.ActionRole)
        self.btn_remind = btn_box.addButton("修改提醒", QDialogButtonBox.ButtonRole.ActionRole)
        self.btn_delete = btn_box.addButton("删除", QDialogButtonBox.ButtonRole.DestructiveRole)
        self.btn_save = btn_box.addButton("保存修改", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_cancel = btn_box.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        self.btn_save.hide()
        self.btn_cancel.hide()
        layout.addWidget(btn_box)

        self.btn_edit.clicked.connect(self._enter_edit)
        self.btn_confirm.clicked.connect(self._confirm)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_save.clicked.connect(self._save)
        self.btn_cancel.clicked.connect(self._exit_edit)

    # ===== 数据加载 =====

    def _load(self, s: dict):
        self.title_label.setText(s.get("name") or "未命名日程")
        self.inputs["name"].setText(s.get("name") or "")
        self.inputs["duty_date"].setText(s.get("duty_date") or "")
        self.inputs["start_time"].setText(s.get("start_time") or "")
        self.inputs["end_time"].setText(s.get("end_time") or "")
        self.inputs["location"].setText(s.get("location") or "")
        self.inputs["remark"].setText(s.get("remark") or "")
        confirmed = bool(s.get("is_confirmed"))
        self.btn_confirm.setEnabled(not confirmed)
        self.btn_confirm.setText("已确认 ✓" if confirmed else "确认")

    # ===== 操作 =====

    def _enter_edit(self):
        self._editing = True
        for w in self.inputs.values():
            w.setReadOnly(False)
        self.btn_edit.hide()
        self.btn_confirm.hide()
        self.btn_remind.hide()
        self.btn_delete.hide()
        self.btn_save.show()
        self.btn_cancel.show()

    def _exit_edit(self):
        self._editing = False
        self._load(self._schedule)
        for w in self.inputs.values():
            w.setReadOnly(True)
        self.btn_edit.show()
        self.btn_confirm.show()
        self.btn_remind.show()
        self.btn_delete.show()
        self.btn_save.hide()
        self.btn_cancel.hide()

    def _save(self):
        payload = {
            "name": self.inputs["name"].text().strip(),
            "duty_date": self.inputs["duty_date"].text().strip(),
            "start_time": self.inputs["start_time"].text().strip() or None,
            "end_time": self.inputs["end_time"].text().strip() or None,
            "location": self.inputs["location"].text().strip() or None,
            "remark": self.inputs["remark"].toPlainText().strip(),
        }
        if not payload["name"] or not payload["duty_date"]:
            QMessageBox.warning(self, "提示", "名称和日期为必填项")
            return
        try:
            self.provider.update_schedule(self.schedule_id, payload)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
            return
        self._schedule.update(payload)
        self._exit_edit()
        QMessageBox.information(self, "完成", "日程已更新")

    def _confirm(self):
        try:
            self.provider.confirm_schedule(self.schedule_id)
        except Exception as e:
            QMessageBox.critical(self, "确认失败", str(e))
            return
        self._schedule["is_confirmed"] = True
        self._load(self._schedule)
        QMessageBox.information(self, "完成", "日程已确认")

    def _delete(self):
        ret = QMessageBox.question(self, "删除日程", "确定要删除这条日程吗？", QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            try:
                self.provider.delete_schedule(self.schedule_id)
            except Exception as e:
                QMessageBox.critical(self, "删除失败", str(e))
                return
            self.accept()
