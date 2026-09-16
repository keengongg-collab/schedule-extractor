# 轻量化AI文档排班日程提取工具

> 软件工程课程大作业项目 — 从 Word/PDF/纯文本中自动提取排班信息，支持微信小程序和 PC 双端使用。

## 项目简介

本工具通过 AI 自动解析排班文档（Word、PDF、纯文本），提取**姓名、值班日期、起止时间、值班地点、备注**等关键信息，并持久化存储。当信息模糊或缺失时，工具会主动提问让用户补充，而非编造数据。

## 功能特性

### 公共功能（双端共用）
- 解析 Word / PDF / 纯文本排班文档
- AI 自动提取排班关键字段
- 信息缺失时主动提问，补充后重新解析
- 日程表格展示与单条详情查看
- SQLite 本地持久化存储

### 微信小程序（普通成员）
- 上传 PDF/Word/图片 或粘贴文本解析排班
- 表格查看全部排班与个人值班日程
- 微信订阅消息推送提醒
- 日程表格导出

### PC 附属工具（管理员）
- Streamlit 网页批量上传解析、预览、Excel 导出
- Windows 划词插件：选中文本按快捷键捕获，弹窗确认新增日程
- 自定义桌面通知：提前提醒时长与文案可配置

## 技术栈

| 端 | 技术 |
|----|------|
| 后端 | Python + Flask + SQLite + REST API |
| PC 端 | Streamlit + pynput + pyperclip + plyer + pandas |
| 小程序 | 原生微信小程序 |

## 项目结构

```
schedule-extractor/
├── backend/          # Python 后端核心引擎
│   ├── core/         # 核心业务逻辑（抽取、解析、问答）
│   ├── api/          # REST API 路由
│   ├── db/           # SQLite 数据库层
│   └── utils/        # 工具函数
├── pc_client/        # PC 附属管理工具
│   ├── app_streamlit.py   # Streamlit 网页
│   ├── word_selector.py   # 划词插件
│   ├── notifier.py        # 桌面通知
│   └── excel_export.py    # Excel 导出
├── miniprogram/      # 微信小程序前端
│   ├── pages/        # 页面（首页/排班/详情/我的）
│   └── utils/        # API 封装
├── README.md
├── .gitignore
└── requirements.txt
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动后端

```bash
cd backend
python app.py
```
后端默认运行在 `http://127.0.0.1:5000`

### 3. 启动 PC 端

```bash
cd pc_client
streamlit run app_streamlit.py
```

### 4. 小程序

使用微信开发者工具打开 `miniprogram` 目录即可。

## 开发说明

- 代码分层清晰：`core`（业务逻辑）、`api`（路由）、`db`（存储）三层解耦
- 关键位置均有中文注释
- 数据库使用 SQLite，零配置开箱即用

## License

MIT
