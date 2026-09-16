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
  },
  globalData: {
    // 后端API地址，开发时用本地IP，上线后替换为线上域名
    apiBase: 'http://127.0.0.1:5000',
    // 用户信息
    userInfo: null,
    // 微信订阅消息模板ID
    templateId: ''
  }
})
