// pages/schedule/schedule.js 排班列表
const api = require('../../utils/api.js')

Page({
  data: {
    schedules: [],
    loading: false,
    searchName: ''
  },

  onShow() {
    this.loadSchedules()
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadSchedules().then(() => wx.stopPullDownRefresh())
  },

  // 加载排班列表
  async loadSchedules() {
    this.setData({ loading: true })
    try {
      const res = await api.getSchedules(this.data.searchName)
      this.setData({ schedules: res.data || [] })
    } catch (e) {
      console.error('加载失败', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  // 搜索
  onSearch(e) {
    this.setData({ searchName: e.detail.value })
  },

  // 执行搜索
  doSearch() {
    this.loadSchedules()
  },

  // 跳转详情
  goDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/detail/detail?id=' + id })
  }
})
