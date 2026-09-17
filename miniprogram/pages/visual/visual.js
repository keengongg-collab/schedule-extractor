/**
 * 轻量化AI文档排班日程提取工具
 * Copyright (c) 2026 schedule-extractor Contributors
 * Licensed under MIT License
 * 详见 LICENSE 文件与 PRIVACY.md 隐私声明
 */

// pages/visual/visual.js 值班表可视化：横向日期表头 + 纵向时间列 + 时长比例
const api = require('../../utils/api.js')

Page({
  data: {
    columns: [],       // 日期列（横向表头）
    maxDuration: 0,    // 最大时长（分钟），用于跨天一致缩放
    loading: false,
    days: 7,
    daysOptions: [3, 5, 7, 14],
    daysIndex: 2,
    scaleUnit: '',
    selected: null     // 点击查看的日程详情
  },

  onShow() {
    this.loadVisual()
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadVisual().then(() => wx.stopPullDownRefresh())
  },

  // 加载可视化数据
  async loadVisual() {
    this.setData({ loading: true })
    try {
      const res = await api.getVisualData(this.data.days)
      this.setData({
        columns: res.data.columns || [],
        maxDuration: res.data.max_duration || 0,
        scaleUnit: res.data.scale_unit || ''
      })
    } catch (e) {
      console.error('加载可视化数据失败', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 点击日程块查看详情
  onTapItem(e) {
    const idx = e.currentTarget.dataset.index
    const colIdx = e.currentTarget.dataset.col
    const item = this.data.columns[colIdx].items[idx]
    this.setData({
      selected: {
        ...item,
        date: this.data.columns[colIdx].date,
        weekday: this.data.columns[colIdx].weekday
      }
    })
  },

  // 关闭详情弹层
  onCloseDetail() {
    this.setData({ selected: null })
  },

  // 切换显示天数
  onDaysChange(e) {
    const idx = parseInt(e.detail.value, 10) || 2
    this.setData({
      days: this.data.daysOptions[idx] || 7,
      daysIndex: idx
    })
    this.loadVisual()
  }
})
