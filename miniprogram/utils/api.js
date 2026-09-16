// utils/api.js 后端API封装
const app = getApp()

/**
 * 封装网络请求
 */
function request(url, method, data) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: app.globalData.apiBase + url,
      method: method || 'GET',
      data: data,
      header: { 'Content-Type': 'application/json' },
      success(res) {
        if (res.data.code === 0) {
          resolve(res.data)
        } else {
          wx.showToast({ title: res.data.msg || '请求失败', icon: 'none' })
          reject(res.data)
        }
      },
      fail(err) {
        wx.showToast({ title: '网络错误', icon: 'none' })
        reject(err)
      }
    })
  })
}

/** 上传文件 */
function uploadFile(filePath) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: app.globalData.apiBase + '/api/upload/file',
      filePath: filePath,
      name: 'file',
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
        wx.showToast({ title: '网络错误', icon: 'none' })
        reject(err)
      }
    })
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
  deleteSchedule
}
