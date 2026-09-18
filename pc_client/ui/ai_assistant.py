# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
AI 助手页面
聊天式输入自然语言 → /api/ai/intent 解析为结构化预览 → 用户确认后再执行
创建/修改/删除：先预览后执行；多个匹配候选时列出让用户选择（不猜测）
"""
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class _Bubble(QFrame):
    """消息气泡（左侧 AI / 右侧用户）"""

    def __init__(self, text, role, parent=None):
        super().__init__(parent)
        self.setObjectName(f"bubble{role.capitalize()}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(label)
        if role == "user":
            layout.setAlignment(Qt.AlignRight)
        else:
            layout.setAlignment(Qt.AlignLeft)


class AiAssistant(QWidget):
    """AI 日程助手页"""

    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self.provider = provider
        self._selected = {}  # action -> {"id":..., "fields":...} 待确认状态
        self._build_ui()
        self.add_msg("你好，我是 AI 日程助手 👋\n可以直接告诉我：\n· 明天下午三点去图书馆开会\n· 把我明天下午三点的项目会议改到四点\n· 删除我明天的值班\n我会先给你预览，确认后再执行。", "ai")

    # ===== UI =====

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("AI 助手")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # 消息滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._messages = QWidget()
        self._msg_layout = QVBoxLayout(self._messages)
        self._msg_layout.setContentsMargins(4, 4, 8, 4)
        self._msg_layout.setSpacing(10)
        self._msg_layout.addStretch()
        scroll.setWidget(self._messages)
        layout.addWidget(scroll, 1)

        # 输入区
        input_row = QHBoxLayout()
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("输入自然语言指令…")
        self.input.setMaximumHeight(64)
        self.input.setFixedHeight(64)
        send_btn = QPushButton("发送")
        send_btn.setObjectName("primaryButton")
        send_btn.clicked.connect(self._send)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(send_btn, 0, Qt.AlignBottom)
        layout.addLayout(input_row)

    # ===== 消息渲染 =====

    def add_msg(self, text: str, role: str = "ai"):
        bubble = _Bubble(text, role)
        self._msg_layout.insertWidget(self._msg_layout.count() - 1, bubble)
        self._scroll_to_bottom()

    def _add_widget(self, w: QWidget):
        self._msg_layout.insertWidget(self._msg_layout.count() - 1, w)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        scroll = self._msg_layout.itemAt(self._msg_layout.count() - 1).widget()
        # 简单处理：强制滚动到底
        parent = self
        while parent and not isinstance(parent, QScrollArea):
            parent = parent.parentWidget()
        if parent:
            parent.verticalScrollBar().setValue(parent.verticalScrollBar().maximum())

    # ===== 发送与意图处理 =====

    def _send(self):
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.add_msg(text, "user")
        self.input.clear()
        try:
            result = self.provider.parse_intent(text)
        except Exception as e:
            self.add_msg(f"解析失败：{e}", "ai")
            return
        self._render_result(result)

    def _render_result(self, result):
        action = result.get("action")
        self.add_msg(result.get("msg") or "", "ai")
        if action == "create":
            self._render_create(result.get("previews") or [])
        elif action == "delete":
            self._render_candidates(result, confirm_text="确认删除", danger=True)
        elif action == "update":
            self._render_candidates(result, confirm_text="确认修改", danger=False)
        else:  # query
            self._render_candidates(result, confirm_text=None, danger=False)

    def _render_create(self, previews):
        if not previews:
            return
        for s in previews:
            lines = [
                f"📌 {s.get('name') or '未命名'}",
                f"📅 {s.get('duty_date') or '待确认'}",
                f"🕒 {(s.get('start_time') or '--:--')} ~ {(s.get('end_time') or '--:--')}",
                f"📍 {s.get('location') or '未定'}",
            ]
            if s.get("remark"):
                lines.append(f"📝 {s['remark']}")
            self.add_msg("\n".join(lines), "ai")
        self._add_buttons([("确认创建", lambda: self._confirm_create(previews))])

    def _render_candidates(self, result, confirm_text, danger):
        candidates = result.get("candidates") or []
        fields = result.get("fields") or {}
        for i, c in enumerate(candidates, 1):
            line = (f"{i}. {c.get('name')}  {c.get('duty_date')}  "
                    f"{(c.get('start_time') or '--:--')}  {c.get('location') or ''}".rstrip())
            btn = QPushButton(line)
            btn.setObjectName("candidateButton")
            btn.clicked.connect(lambda checked=False, sid=c["id"]: self._pick(sid, result))
            self._add_widget(btn)
        if confirm_text and len(candidates) == 1:
            self._add_buttons([(confirm_text, lambda: self._execute(result, candidates[0]))],
                              danger=danger)
        if fields:
            self.add_msg("将修改：" + "，".join(f"{k}: {v}" for k, v in fields.items()), "ai")

    def _add_buttons(self, pairs, danger=False):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        holder = QWidget()
        holder.setLayout(row)
        for text, handler in pairs:
            btn = QPushButton(text)
            btn.setObjectName("dangerButton" if danger else "primaryButton")
            btn.clicked.connect(handler)
            row.addWidget(btn)
        row.addStretch()
        self._add_widget(holder)

    # ===== 执行（确认后）=====

    def _pick(self, schedule_id, result):
        """多候选时用户选择某一条"""
        for c in result.get("candidates") or []:
            if c["id"] == schedule_id:
                self._execute(result, c)
                return

    def _confirm_create(self, previews):
        try:
            for s in previews:
                self.provider.create_schedule(s)
        except Exception as e:
            self.add_msg(f"创建失败：{e}", "ai")
            return
        self.add_msg(f"✅ 已创建 {len(previews)} 条日程", "ai")

    def _execute(self, result, target):
        action = result.get("action")
        try:
            if action == "delete":
                self.provider.delete_schedule(target["id"])
                self.add_msg(f"✅ 已删除：{target.get('name')}", "ai")
            elif action == "update":
                payload = result.get("fields") or {}
                self.provider.update_schedule(target["id"], payload)
                self.add_msg(f"✅ 已修改：{target.get('name')} {payload}", "ai")
            else:
                self.add_msg(f"{target.get('name')}  {target.get('duty_date')}  "
                             f"{target.get('start_time')}  {target.get('location') or ''}", "ai")
        except Exception as e:
            self.add_msg(f"操作失败：{e}", "ai")
