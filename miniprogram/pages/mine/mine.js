/**
 * 轻量化AI文档排班日程提取工具
 * Copyright (c) 2026 schedule-extractor Contributors
 * Licensed under MIT License
 * 详见 LICENSE 文件与 PRIVACY.md 隐私声明
 */

// pages/mine/mine.js 我的：个人信息 + 个人值班 + 待补充信息
const api = require('../../utils/api.js')

Page({
  data: {
    currentTab: 'profile',     // profile | mySchedule | pending
    // 个人信息表单
    profileName: '',
    profileStudentId: '',
    profileSaving: false,
    myUser: null,
    // 关键词识别演示
    recognizeText: '',
    recognizeResult: null,
    recognizing: false,
    // 网络诊断
    diagnosing: false,
    diagnoseResults: [],
    currentApiBase: '',
    // 排班
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
    this.setData({ currentApiBase: getApp().globalData.apiBase })
    if (this.data.currentTab === 'profile') {
      this.loadMyProfile()
    } else if (this.data.currentTab === 'mySchedule') {
      this.loadMySchedules()
    } else {
      this.loadPendingQuestions()
    }
  },

  // 切换Tab
  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ currentTab: tab })
    if (tab === 'profile') this.loadMyProfile()
    else if (tab === 'mySchedule') this.loadMySchedules()
    else this.loadPendingQuestions()
  },

  // ===== 用户信息收集 =====

  // 加载本地已保存的用户信息
  loadMyProfile() {
    const local = wx.getStorageSync('my_user')
    if (local) {
      this.setData({ myUser: local })
    }
  },

  // 姓名输入
  onProfileName(e) {
    this.setData({ profileName: e.detail.value })
  },

  // 学号输入
  onProfileStudentId(e) {
    this.setData({ profileStudentId: e.detail.value })
  },

  // 保存个人信息（预收集阶段）
  async onSaveProfile() {
    const name = this.data.profileName.trim()
    if (!name) {
      wx.showToast({ title: '请输入姓名', icon: 'none' })
      return
    }
    this.setData({ profileSaving: true })
    try {
      const res = await api.saveUserInfo({
        name: name,
        student_id: this.data.profileStudentId.trim(),
        // 演示用本地标识作为会话关联，生产环境替换为微信 openid
        openid: 'local_' + (wx.getStorageSync('device_id') || 'demo')
      })
      // 本地缓存，用于会话/账户关联
      wx.setStorageSync('my_user', res.data)
      wx.setStorageSync('device_id', 'demo')
      this.setData({ myUser: res.data, profileSaving: false })
      wx.showToast({ title: '保存成功', icon: 'success' })
    } catch (e) {
      console.error('保存失败', e)
      this.setData({ profileSaving: false })
    }
  },

  // ===== 关键词识别系统 =====

  // 识别文本输入
  onRecognizeText(e) {
    this.setData({ recognizeText: e.detail.value })
  },

  // 执行关键词识别："我是张三，我把一个组的值班表发上去" → 识别张三
  async onRecognize() {
    const text = this.data.recognizeText.trim()
    if (!text) {
      wx.showToast({ title: '请输入文本', icon: 'none' })
      return
    }
    this.setData({ recognizing: true, recognizeResult: null })
    try {
      const res = await api.recognizeUser(text)
      this.setData({ recognizeResult: res, recognizing: false })
      if (res.matched) {
        wx.showToast({ title: '已识别：' + res.data.user.name, icon: 'success' })
      }
    } catch (e) {
      console.error('识别失败', e)
      this.setData({ recognizing: false })
    }
  },

  // 跳转可视化
  goVisual() {
    wx.navigateTo({ url: '/pages/visual/visual' })
  },

  // ===== 网络诊断（真机网络错误专用）=====
  async onDiagnose() {
    this.setData({ diagnosing: true, diagnoseResults: [] })
    try {
      const app = getApp()
      const results = await api.diagnose(app.globalData.candidateHosts || [])
      this.setData({ diagnoseResults: results })
      // 若当前地址不通但存在可用地址，自动切换并缓存
      const current = app.globalData.apiBase
      const currentOk = results.some(function (r) { return r.host === current && r.ok })
      const firstOk = results.find(function (r) { return r.ok })
      if (!currentOk && firstOk) {
        app.globalData.apiBase = firstOk.host
        wx.setStorageSync('api_base', firstOk.host)
        this.setData({ currentApiBase: firstOk.host })
        wx.showModal({
          title: '已自动切换地址',
          content: '当前地址不通，已切换到：' + firstOk.host,
          showCancel: false
        })
      } else if (currentOk) {
        wx.showToast({ title: '当前地址可正常访问', icon: 'success' })
      } else {
        wx.showModal({
          title: '所有地址均不通',
          content: '请检查：1.手机与电脑是否同一WiFi 2.路由器是否开启AP隔离 3.手机浏览器能否直接访问该地址',
          showCancel: false
        })
      }
    } catch (e) {
      console.error('诊断失败', e)
    } finally {
      this.setData({ diagnosing: false })
    }
  },

  // 手动切换后端地址
  onSwitchHost(e) {
    const host = e.currentTarget.dataset.host
    getApp().globalData.apiBase = host
    wx.setStorageSync('api_base', host)
    this.setData({ currentApiBase: host })
    wx.showToast({ title: '已切换', icon: 'success' })
  },

  // 加载我的排班（按识别到的用户姓名筛选）
  async loadMySchedules() {
    this.setData({ loading: true })
    try {
      const myUser = wx.getStorageSync('my_user')
      const res = await api.getSchedules(myUser ? myUser.name : '')
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
