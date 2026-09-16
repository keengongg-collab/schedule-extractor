/**
 * 轻量化AI文档排班日程提取工具
 * Copyright (c) 2026 schedule-extractor Contributors
 * Licensed under MIT License
 * 详见 LICENSE 文件与 PRIVACY.md 隐私声明
 */

// pages/detail/detail.js 单条详情
const api = require('../../utils/api.js')

Page({
  data: {
    schedule: null,
    loading: true
  },

  onLoad(options) {
    if (options.id) {
      this.loadDetail(options.id)
    }
  },

  async loadDetail(id) {
    try {
      const res = await api.getScheduleDetail(id)
      this.setData({ schedule: res.data })
    } catch (e) {
      console.error('加载失败', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 确认日程
  async onConfirm() {
    try {
      await api.confirmSchedule(this.data.schedule.id)
      wx.showToast({ title: '已确认', icon: 'success' })
      this.loadDetail(this.data.schedule.id)
    } catch (e) {
      console.error('确认失败', e)
    }
  },

  // 删除日程
  onDelete() {
    wx.showModal({
      title: '确认删除',
      content: '确定删除这条排班记录吗？',
      success: async (res) => {
        if (res.confirm) {
          await api.deleteSchedule(this.data.schedule.id)
          wx.showToast({ title: '已删除', icon: 'success' })
          setTimeout(() => wx.navigateBack(), 1000)
        }
      }
    })
  },

  // 订阅提醒
  onSubscribe() {
    const app = getApp()
    if (app.globalData.templateId) {
      wx.requestSubscribeMessage({
        tmplIds: [app.globalData.templateId],
        success(res) {
          if (res[app.globalData.templateId] === 'accept') {
            wx.showToast({ title: '提醒已订阅', icon: 'success' })
          } else {
            wx.showToast({ title: '已取消订阅', icon: 'none' })
          }
        }
      })
    } else {
      wx.showToast({ title: '订阅模板未配置', icon: 'none' })
    }
  }
})
