/**
 * 轻量化AI文档排班日程提取工具
 * Copyright (c) 2026 schedule-extractor Contributors
 * Licensed under MIT License
 * 详见 LICENSE 文件与 PRIVACY.md 隐私声明
 */

// pages/mine/mine.js 我的：个人值班 + 待补充信息
const api = require('../../utils/api.js')

Page({
  data: {
    currentTab: 'mySchedule',  // mySchedule | pending
    mySchedules: [],
    pendingQuestions: [],
    loading: false
  },

  onLoad(options) {
    if (options.tab === 'pending') {
      this.setData({ currentTab: 'pending' })
    }
  },

  onShow() {
    if (this.data.currentTab === 'mySchedule') {
      this.loadMySchedules()
    } else {
      this.loadPendingQuestions()
    }
  },

  // 切换Tab
  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ currentTab: tab })
    if (tab === 'mySchedule') this.loadMySchedules()
    else this.loadPendingQuestions()
  },

  // 加载我的排班（展示全部，实际可按用户筛选）
  async loadMySchedules() {
    this.setData({ loading: true })
    try {
      const res = await api.getSchedules()
      this.setData({ mySchedules: res.data || [] })
    } catch (e) {
      console.error('加载失败', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 加载待补充问题
  async loadPendingQuestions() {
    this.setData({ loading: true })
    try {
      const res = await api.getPendingQuestions()
      this.setData({ pendingQuestions: res.data || [] })
    } catch (e) {
      console.error('加载失败', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 提交补充回答
  async onSubmitAnswer(e) {
    const qaId = e.currentTarget.dataset.id
    const answer = e.detail.value.answer
    if (!answer || !answer.trim()) {
      wx.showToast({ title: '请输入补充内容', icon: 'none' })
      return
    }
    try {
      await api.submitAnswer(qaId, answer.trim())
      wx.showToast({ title: '已提交', icon: 'success' })
      this.loadPendingQuestions()
    } catch (e) {
      console.error('提交失败', e)
    }
  }
})
