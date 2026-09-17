-- ============================================================
-- 轻量化AI文档排班日程提取工具 - 数据库建表脚本
-- SQLite 数据库，零配置开箱即用
-- ============================================================

-- 日程表：存储从文档中提取的排班信息
CREATE TABLE IF NOT EXISTS schedules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,   -- 自增主键
    name            TEXT NOT NULL,                        -- 值班人姓名
    duty_date       TEXT NOT NULL,                        -- 值班日期（YYYY-MM-DD）
    start_time      TEXT,                                 -- 起始时间（HH:MM）
    end_time        TEXT,                                 -- 结束时间（HH:MM）
    location        TEXT,                                 -- 值班地点
    remark          TEXT DEFAULT '',                      -- 备注
    source_type     TEXT DEFAULT 'manual',                -- 来源类型：upload/paste/word_selector/manual
    original_text   TEXT,                                 -- 原始文本片段（用于追溯）
    is_confirmed    INTEGER DEFAULT 0,                    -- 是否已确认：0=待确认，1=已确认
    created_at      TEXT DEFAULT (datetime('now','localtime')),  -- 创建时间
    updated_at      TEXT DEFAULT (datetime('now','localtime'))   -- 更新时间
);

-- 提醒配置表：存储自定义提醒设置
CREATE TABLE IF NOT EXISTS reminders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id     INTEGER,                              -- 关联日程ID（外键）
    advance_minutes INTEGER DEFAULT 15,                   -- 提前提醒分钟数
    custom_message  TEXT,                                  -- 自定义提醒文案
    is_active       INTEGER DEFAULT 1,                    -- 是否启用：1=启用，0=停用
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (schedule_id) REFERENCES schedules (id) ON DELETE CASCADE
);

-- AI问答记录表：存储信息缺失时的提问与用户回答
CREATE TABLE IF NOT EXISTS qa_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id     INTEGER,                              -- 关联日程ID
    question        TEXT NOT NULL,                         -- AI提出的问题
    answer          TEXT,                                  -- 用户回答
    field_name      TEXT,                                  -- 涉及的字段名（如 name/date/location）
    status          TEXT DEFAULT 'pending',                -- 状态：pending/answered/applied
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (schedule_id) REFERENCES schedules (id) ON DELETE CASCADE
);

-- 文档解析记录表：记录每次文档解析操作
CREATE TABLE IF NOT EXISTS parse_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name       TEXT,                                  -- 文件名
    file_type       TEXT,                                  -- 文件类型：pdf/word/text
    total_extracted INTEGER DEFAULT 0,                    -- 提取的日程条数
    has_ambiguity   INTEGER DEFAULT 0,                    -- 是否有歧义：0=无，1=有
    status          TEXT DEFAULT 'success',                -- 状态：success/partial/failed
    created_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- 用户信息表：存储用户预收集的个人信息（姓名等），用于关键词识别关联
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,                         -- 用户姓名（关键标识）
    openid          TEXT,                                  -- 微信openid（关联会话/账户）
    student_id      TEXT,                                  -- 学号/工号（可选）
    phone           TEXT,                                  -- 联系电话（可选）
    remark          TEXT DEFAULT '',                       -- 备注
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime'))
);

-- ============================================================
-- 索引：加速常用查询
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_schedules_name ON schedules(name);
CREATE INDEX IF NOT EXISTS idx_schedules_date ON schedules(duty_date);
CREATE INDEX IF NOT EXISTS idx_schedules_confirmed ON schedules(is_confirmed);
CREATE INDEX IF NOT EXISTS idx_reminders_active ON reminders(is_active);
CREATE INDEX IF NOT EXISTS idx_qa_status ON qa_records(status);
CREATE INDEX IF NOT EXISTS idx_users_name ON users(name);
