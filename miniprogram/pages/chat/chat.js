/**
 * 轻量化AI文档排班日程提取工具
 * Copyright (c) 2026 schedule-extractor Contributors
 * Licensed under MIT License
 * 详见 LICENSE 文件与 PRIVACY.md 隐私声明
 */

// pages/chat/chat.js 对话式排班智能体
const api = require('../../utils/api.js')

function genSessionId() {
  return 's_' + Date.now() + '_' + Math.floor(Math.random() * 100000)
}

Page({
  data: {
    sessionId: '',
    openid: '',
    messages: [],   // {role, content, thinking, thinkingOpen, options, loading}
    inputText: '',
    sending: false,
    scrollTo: ''
  },

  onLoad() {
    let sid = wx.getStorageSync('chat_session_id')
    if (!sid) {
      sid = genSessionId()
      wx.setStorageSync('chat_session_id', sid)
    }
    const myUser = wx.getStorageSync('my_user') || {}
    this.setData({ sessionId: sid, openid: myUser.openid || '' })
    this.loadHistory()
  },

  // 读取历史，无历史则展示欢迎语
  async loadHistory() {
    try {
      const res = await api.chatHistory(this.data.sessionId, 50)
      const history = (res.data || []).map(m => ({
        role: m.role,
        content: m.content,
        thinking: m.thinking || [],
        thinkingOpen: false,
        options: [],
        loading: false
      }))
      if (history.length > 0) {
        this.setData({ messages: history })
        this.scrollToBottom()
      } else {
        this.startChat()
      }
    } catch (e) {
      console.error('加载历史失败', e)
      this.startChat()
    }
  },

  // 拉取欢迎语
  async startChat() {
    try {
      const res = await api.chatStart(this.data.sessionId, this.data.openid)
      this.pushMessage({
        role: 'agent',
        content: res.data.greeting,
        thinking: [],
        thinkingOpen: false,
        options: [],
        loading: false
      })
    } catch (e) {
      console.error('启动会话失败', e)
      this.pushMessage({
        role: 'agent',
        content: '连接智能体失败，请检查网络或后端服务是否已启动。',
        thinking: [], options: [], loading: false
      })
    }
  },

  // 输入
  onInput(e) {
    this.setData({ inputText: e.detail.value })
  },

  // 发送消息
  async onSend() {
    const text = this.data.inputText.trim()
    if (!text || this.data.sending) return

    this.pushMessage({ role: 'user', content: text, thinking: [], options: [], loading: false })
    this.setData({ inputText: '', sending: true })

    // 占位"思考中"气泡
    const idx = this.data.messages.length
    this.pushMessage({ role: 'agent', content: '', thinking: [], options: [], loading: true })

    try {
      const res = await api.chatSend(this.data.sessionId, text, this.data.openid)
      const d = res.data
      this.setData({
        ['messages[' + idx + ']']: {
          role: 'agent',
          content: d.reply,
          thinking: d.thinking || [],
          thinkingOpen: true,
          options: d.options || [],
          loading: false
        }
      })
    } catch (e) {
      console.error('发送失败', e)
      this.setData({
        ['messages[' + idx + ']']: {
          role: 'agent',
          content: '抱歉，出了点问题，请稍后再试。',
          thinking: [], options: [], loading: false
        }
      })
    } finally {
      this.setData({ sending: false })
      this.scrollToBottom()
    }
  },

  // 点击快捷选项（如候选姓名）
  onOptionTap(e) {
    const val = e.currentTarget.dataset.value
    if (this.data.sending) return
    this.setData({ inputText: val }, () => this.onSend())
  },

  // 折叠/展开思考过程
  onToggleThinking(e) {
    const i = e.currentTarget.dataset.index
    this.setData({ ['messages[' + i + '].thinkingOpen']: !this.data.messages[i].thinkingOpen })
  },

  // 重置会话
  async onReset() {
    const r = await new Promise(resolve => {
      wx.showModal({ title: '重置对话', content: '确定清空当前对话吗？', success: resolve })
    })
    if (!r.confirm) return
    try {
      await api.chatReset(this.data.sessionId)
    } catch (e) {
      console.error('重置失败', e)
    }
    const sid = genSessionId()
    wx.setStorageSync('chat_session_id', sid)
    this.setData({ messages: [], sessionId: sid })
    this.startChat()
  },

  // 追加消息并滚动到底部
  pushMessage(msg) {
    this.setData({ messages: this.data.messages.concat([msg]) })
    this.scrollToBottom()
  },

  scrollToBottom() {
    this.setData({ scrollTo: 'msg-' + (this.data.messages.length - 1) })
  }
})
