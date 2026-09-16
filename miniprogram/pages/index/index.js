/**
 * 轻量化AI文档排班日程提取工具
 * Copyright (c) 2026 schedule-extractor Contributors
 * Licensed under MIT License
 * 详见 LICENSE 文件与 PRIVACY.md 隐私声明
 */

// pages/index/index.js 首页：上传/粘贴文本
const api = require('../../utils/api.js')

Page({
  data: {
    textInput: '',
    parsing: false,
    parseResult: null,
    questions: []
  },

  // 文本输入
  onInput(e) {
    this.setData({ textInput: e.detail.value })
  },

  // 粘贴文本解析
  async onParseText() {
    const text = this.data.textInput.trim()
    if (!text) {
      wx.showToast({ title: '请输入排班文本', icon: 'none' })
      return
    }
    this.setData({ parsing: true })
    try {
      const res = await api.parseText(text)
      this.setData({
        parseResult: res.data,
        questions: res.data.questions || []
      })
      const total = res.data.total || 0
      if (total > 0) {
        wx.showToast({ title: `提取${total}条日程`, icon: 'success' })
      } else {
        wx.showToast({ title: '未提取到日程', icon: 'none' })
      }
    } catch (e) {
      console.error('解析失败', e)
    } finally {
      this.setData({ parsing: false })
    }
  },

  // 选择文件上传
  onChooseFile() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['pdf', 'docx', 'doc', 'txt'],
      success: async (res) => {
        const filePath = res.tempFiles[0].path
        wx.showLoading({ title: '解析中...' })
        try {
          const result = await api.uploadScheduleFile(filePath)
          this.setData({
            parseResult: result.data,
            questions: result.data.questions || []
          })
          const total = result.data.total || 0
          wx.showToast({ title: `提取${total}条日程`, icon: 'success' })
        } catch (e) {
          console.error('上传失败', e)
        } finally {
          wx.hideLoading()
        }
      }
    })
  },

  // 跳转到排班列表
  goSchedule() {
    wx.switchTab({ url: '/pages/schedule/schedule' })
  },

  // 跳转到待补充
  goPending() {
    if (this.data.questions.length > 0) {
      wx.navigateTo({ url: '/pages/mine/mine?tab=pending' })
    }
  }
})
