/**
 * 轻量化AI文档排班日程提取工具
 * Copyright (c) 2026 schedule-extractor Contributors
 * Licensed under MIT License
 * 详见 LICENSE 文件与 PRIVACY.md 隐私声明
 */

// utils/api.js 后端API封装
// 注意：不要在文件顶层调用 getApp()，模块加载时机可能早于 App() 注册，
// 在真机上会拿到 undefined。改为每次请求时获取。

/** 安全获取全局 app 实例 */
function getAppInstance() {
  return getApp()
}

/**
 * 把微信原始错误分类成人话，便于真机定位
 */
function classifyError(errMsg) {
  const m = errMsg || ''
  if (m.indexOf('url not in domain list') !== -1) {
    return { type: 'domain', tip: '域名校验未关闭：真机调试需勾选"不校验合法域名"，且手机微信需处于调试模式' }
  }
  if (m.indexOf('timeout') !== -1) {
    return { type: 'timeout', tip: '连接超时：手机与电脑可能不在同一网段，或WiFi开了AP隔离' }
  }
  if (m.indexOf('fail') !== -1 && (m.indexOf('connect') !== -1 || m.indexOf('Network') !== -1)) {
    return { type: 'unreachable', tip: '无法连接服务器：后端未启动/IP错误/防火墙/网段不通' }
  }
  return { type: 'other', tip: '其他网络错误' }
}

/**
 * 封装网络请求
 */
function request(url, method, data) {
  const app = getAppInstance()
  const baseUrl = app.globalData.apiBase
  return new Promise((resolve, reject) => {
    wx.request({
      url: baseUrl + url,
      method: method || 'GET',
      data: data,
      header: { 'Content-Type': 'application/json' },
      // 超时时间10秒，避免手机端长时间无响应
      timeout: 10000,
      success(res) {
        if (res.data && res.data.code === 0) {
          resolve(res.data)
        } else {
          wx.showToast({ title: (res.data && res.data.msg) || '请求失败', icon: 'none' })
          reject(res.data)
        }
      },
      fail(err) {
        // 真机调试时在控制台打印完整失败信息（完整URL + 原始错误）
        const info = classifyError(err.errMsg)
        console.error('[请求失败]', baseUrl + url, err.errMsg, '=>', info.tip)
        wx.showToast({ title: '网络错误', icon: 'none' })
        // 把分类信息挂到错误对象上，供上层使用
        err.errType = info.type
        err.errTip = info.tip
        reject(err)
      }
    })
  })
}

/** 上传文件 */
function uploadFile(filePath) {
  const app = getAppInstance()
  const baseUrl = app.globalData.apiBase
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: baseUrl + '/api/upload/file',
      filePath: filePath,
      name: 'file',
      timeout: 15000,
      success(res) {
        const data = JSON.parse(res.data)
        if (data.code === 0) {
          resolve(data)
        } else {
          wx.showToast({ title: data.msg || '上传失败', icon: 'none' })
          reject(data)
        }
      },
      fail(err) {
        const info = classifyError(err.errMsg)
        console.error('[上传失败]', baseUrl, err.errMsg, '=>', info.tip)
        wx.showToast({ title: '网络错误', icon: 'none' })
        reject(err)
      }
    })
  })
}

/**
 * 网络诊断：在手机端逐个测试候选后端地址，返回每个地址的详细结果。
 * 用于真机网络错误时一键定位是哪一跳的问题。
 * @param {Array<string>} hosts 候选地址，如 ['http://10.3.13.155:5000']
 */
function diagnose(hosts) {
  const results = []
  // 候选地址：传入的 + 全局默认，去重
  const app = getAppInstance()
  const all = []
  ;(hosts || []).concat([app.globalData.apiBase]).forEach(function (h) {
    if (h && all.indexOf(h) === -1) all.push(h)
  })

  // 顺序测试，记录状态码/耗时/原始错误
  const tasks = all.map(function (host) {
    return new Promise(function (resolve) {
      const start = Date.now()
      wx.request({
        url: host + '/api/health',
        method: 'GET',
        timeout: 6000,
        success(res) {
          results.push({
            host: host,
            ok: res.statusCode === 200,
            status: res.statusCode,
            cost: Date.now() - start,
            msg: res.statusCode === 200 ? '可连通' : ('HTTP ' + res.statusCode)
          })
          resolve()
        },
        fail(err) {
          const info = classifyError(err.errMsg)
          results.push({
            host: host,
            ok: false,
            status: '-',
            cost: Date.now() - start,
            msg: info.tip,
            raw: err.errMsg
          })
          resolve()
        }
      })
    })
  })

  return Promise.all(tasks).then(function () {
    return results
  })
}

// ===== API 接口列表 =====

/** 获取排班列表 */
function getSchedules(name) {
  let url = '/api/schedules'
  if (name) url += '?name=' + encodeURIComponent(name)
  return request(url, 'GET')
}

/** 获取单条详情 */
function getScheduleDetail(id) {
  return request('/api/schedules/' + id, 'GET')
}

/** 粘贴文本解析 */
function parseText(text) {
  return request('/api/upload/text', 'POST', { text: text })
}

/** 上传文件解析 */
function uploadScheduleFile(filePath) {
  return uploadFile(filePath)
}

/** 待回答问题列表 */
function getPendingQuestions() {
  return request('/api/qa/pending', 'GET')
}

/** 提交问题回答 */
function submitAnswer(qaId, answer) {
  return request('/api/qa/answer', 'POST', { qa_id: qaId, answer: answer })
}

/** 获取提醒列表 */
function getReminders() {
  return request('/api/reminders', 'GET')
}

/** 确认日程 */
function confirmSchedule(id) {
  return request('/api/schedules/' + id + '/confirm', 'POST')
}

/** 删除日程 */
function deleteSchedule(id) {
  return request('/api/schedules/' + id, 'DELETE')
}

// ===== 用户信息与关键词识别 =====

/** 提交用户信息（预收集） */
function saveUserInfo(userInfo) {
  return request('/api/users', 'POST', userInfo)
}

/** 关键词识别：从文本中识别预收集的用户姓名 */
function recognizeUser(text) {
  return request('/api/users/recognize', 'POST', { text: text })
}

/** 获取值班表可视化数据 */
function getVisualData(days) {
  return request('/api/schedules/visual?days=' + (days || 7), 'GET')
}

// 导出接口
module.exports = {
  getSchedules,
  getScheduleDetail,
  parseText,
  uploadScheduleFile,
  getPendingQuestions,
  submitAnswer,
  getReminders,
  confirmSchedule,
  deleteSchedule,
  saveUserInfo,
  recognizeUser,
  getVisualData,
  diagnose,
  classifyError
}
