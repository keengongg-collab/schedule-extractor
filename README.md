# 轻量化AI文档排班日程提取工具

> 软件工程课程大作业项目 — 从 PDF / DOCX / 纯文本中自动提取排班信息，支持微信小程序和 PC 双端使用。

> **版权声明**：本项目采用 [MIT 许可证](./LICENSE) 开源，详见 [隐私保护与数据脱敏声明](./PRIVACY.md)。所有源代码中的个人敏感信息已进行脱敏处理，不包含任何真实姓名、身份证号、联系方式或地址等隐私数据。

## 项目介绍

本工具通过 AI 自动解析排班文档（PDF、DOCX、纯文本），提取**姓名、值班日期、起止时间、值班地点、备注**等关键信息并持久化存储。当信息模糊或缺失时，工具会主动生成待补充问题，用户回答后直接更新对应日程，而非编造数据。

v1.0 完整业务闭环：

```text
上传 PDF / DOCX / TXT → 提取文本 → AI 识别排班 → 字段完整性校验
   ├─ 完整 → 保存日程
   └─ 不完整 → 生成 QA 待补充 → 用户回答 → 更新日程
PC 管理端：查看 / 修改 / 删除 / 确认 / Excel 导出
```

## 支持的文件格式

| 格式 | 支持情况 | 说明 |
|------|----------|------|
| PDF | ✅ | pdfplumber 提取文本与表格 |
| DOCX | ✅ | python-docx 提取段落与表格（OOXML 格式） |
| TXT | ✅ | 自动尝试 UTF-8 / GBK 等编码 |
| DOC（旧版二进制 Word） | ❌ | python-docx 无法解析，需先另存为 .docx |

未配置 AI API Key 时自动降级为正则规则兜底（只能识别"姓名 日期 时间 地点"格式规整的文本）。

## 环境要求

- Python 3.10+（开发环境为 Python 3.14）
- Windows 10/11（一键启动脚本与桌面通知面向 Windows；后端跨平台可用）
- 依赖见 `requirements.txt`（Flask、pdfplumber、python-docx、openai、Streamlit、pandas、openpyxl 等）

## 安装

```bash
pip install -r requirements.txt
```

## 环境变量配置

复制 `.env.example` 为 `.env` 并按需修改（`.env` 已在 `.gitignore` 中，真实 API Key 不会提交）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEBUG` | `false` | 调试模式，开发时可设 `true`，**生产环境必须 false** |
| `HOST` | `0.0.0.0` | 监听地址；仅本机访问用 `127.0.0.1`，小程序真机调试用 `0.0.0.0` |
| `PORT` | `5000` | 后端端口 |
| `MAX_UPLOAD_MB` | `10` | 上传文件大小上限（MB） |
| `API_BASE` | `http://127.0.0.1:5000` | PC 端（Streamlit/划词插件）访问后端的地址 |
| `AI_API_KEY` | 空 | OpenAI 兼容大模型 Key，留空走正则兜底 |
| `AI_BASE_URL` | DeepSeek | OpenAI 兼容接口地址 |
| `AI_MODEL` | `deepseek-chat` | 模型名称 |
| `WECHAT_TEMPLATE_ID` | 空 | 微信订阅消息模板 ID |

## 启动后端

方式一（Windows 推荐）：双击项目根目录的 **`start.bat`**，会分别启动 Flask 后端与 Streamlit 管理端。

方式二（手动）：

```bash
# 在项目根目录执行
py backend\app.py
# 或 python backend/app.py
```

首次启动会在 `backend/data/schedule.db` 自动创建 SQLite 数据库与全部表结构。

健康检查：<http://127.0.0.1:5000/api/health>

## 启动 PC 客户端

```bash
py -m streamlit run pc_client/app_streamlit.py
```

浏览器打开 <http://localhost:8501>，侧边栏包含：排班总览、上传文档解析、手动添加、待补充信息、提醒管理、Excel 导出。
若页面提示无法连接后端，请先启动后端；侧边栏会显示当前使用的 `API_BASE`。

## 微信小程序

使用微信开发者工具打开 `miniprogram/` 目录。真机局域网调试需将后端 `HOST=0.0.0.0`，小程序 `app.js` 中 API 地址改为电脑局域网 IPv4，并勾选"不校验合法域名"。

## API 简介

所有响应统一为 `{"code": 0, "msg": "...", "data": ...}`，`code=1` 表示错误；不存在的资源返回 HTTP 404。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET/POST | `/api/schedules` | 日程列表 / 新建 |
| GET/PUT/DELETE | `/api/schedules/<id>` | 详情 / 更新 / 删除（白名单字段） |
| POST | `/api/schedules/<id>/confirm` | 确认日程 |
| POST | `/api/upload/file` | 上传 PDF/DOCX/TXT 解析（UUID 临时文件，解析后清理） |
| POST | `/api/upload/text` | 粘贴文本解析 |
| GET | `/api/qa/pending` | 待补充问题列表 |
| POST | `/api/qa/answer` | 提交回答并更新日程（字段白名单校验） |
| GET/POST | `/api/reminders` | 提醒列表 / 新建 |
| PUT/DELETE | `/api/reminders/<id>` | 修改 / 删除提醒 |
| POST/GET | `/api/users`、`/api/users/<openid>` | 用户信息收集与查询 |
| POST | `/api/users/recognize` | 关键词识别（"我是张三"） |
| GET | `/api/schedules/visual` | 值班表可视化数据 |
| GET/POST | `/api/chat/start`、`/api/chat` 等 | 对话式排班智能体 |

## 测试

测试数据库通过环境变量 `SCHEDULE_DB_FILE` 自动重定向到临时文件，与开发库隔离；AI 用例全部使用 mock fixtures（`tests/fixtures/`），不消耗真实 API。

```bash
py -m pytest tests/ -q
```

## 项目结构

```text
schedule-extractor/
├── backend/
│   ├── app.py                  # Flask 入口：建库、注册蓝图、统一错误处理
│   ├── config.py               # 环境变量配置
│   ├── api/
│   │   ├── routes_schedule.py  # 日程 CRUD + 确认
│   │   ├── routes_upload.py    # 文件/文本上传解析
│   │   ├── routes_qa.py        # 待补充问答
│   │   ├── routes_reminder.py  # 提醒配置
│   │   ├── routes_user.py      # 用户信息 + 关键词识别
│   │   └── routes_chat.py      # 对话智能体
│   ├── core/
│   │   ├── extractor.py        # AI 抽取（解析→结构检查→标准化→校验）
│   │   ├── validator.py        # 统一字段校验 / 白名单 / AI 结构清洗
│   │   ├── parser.py           # PDF/DOCX/TXT 解析
│   │   ├── agent.py            # 对话智能体状态机
│   │   ├── qa.py               # 问答业务逻辑
│   │   └── models.py           # 数据模型
│   ├── db/
│   │   ├── database.py         # SQLite 连接与初始化
│   │   └── schema.sql          # 建表脚本
│   └── utils/                  # 日志、日期时间工具
├── pc_client/
│   ├── app_streamlit.py        # Streamlit 管理端
│   ├── excel_export.py         # Excel 导出
│   ├── notifier.py             # Windows 桌面通知
│   └── word_selector.py        # 划词插件
├── miniprogram/                # 微信小程序前端
├── tests/                      # pytest 自动化测试
│   ├── conftest.py
│   ├── fixtures/               # AI mock 返回样例
│   └── test_*.py
├── .env.example
├── start.bat
├── requirements.txt
├── README.md
├── LICENSE
└── PRIVACY.md
```

## License

MIT
