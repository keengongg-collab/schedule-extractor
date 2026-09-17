/**
 * 轻量化AI文档排班日程提取工具
 * Copyright (c) 2026 schedule-extractor Contributors
 * Licensed under MIT License
 * 详见 LICENSE 文件与 PRIVACY.md 隐私声明
 */

// app.js 小程序入口
App({
  onLaunch() {
    console.log('排班助手小程序启动')
    // 读取上次网络诊断切换后缓存的可用地址
    const cached = wx.getStorageSync('api_base')
    if (cached) {
      this.globalData.apiBase = cached
    }
  },
  globalData: {
    // 后端API地址，开发时用电脑局域网IP（手机需与电脑同一WiFi），上线后替换为线上域名
    apiBase: 'http://10.3.13.155:5000',
    // 候选后端地址：电脑有双网卡（WLAN/以太网）时逐个诊断，哪个能通用哪个
    candidateHosts: [
      'http://10.3.13.155:5000',
      'http://10.0.155.4:5000'
    ],
    // 用户信息
    userInfo: null,
    // 微信订阅消息模板ID
    templateId: ''
  }
})
