"""
数据库连接与初始化模块
SQLite 零配置，数据库文件存放在 backend/data/ 目录下
"""
import sqlite3
import os

# 数据库文件路径
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "schedule.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_connection():
    """获取 SQLite 数据库连接（每次请求新建，用完关闭）"""
    conn = sqlite3.connect(DB_PATH)
    # 让查询结果可以用列名访问，如 row['name']
    conn.row_factory = sqlite3.Row
    # 开启外键约束
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """初始化数据库：创建目录、执行建表脚本"""
    # 确保 data 目录存在
    os.makedirs(DB_DIR, exist_ok=True)

    conn = get_connection()
    try:
        # 读取并执行建表 SQL
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            sql_script = f.read()
        conn.executescript(sql_script)
        conn.commit()
        print(f"[数据库] 初始化完成，数据库文件: {DB_PATH}")
    except Exception as e:
        print(f"[数据库] 初始化失败: {e}")
        raise
    finally:
        conn.close()


def query(sql, params=(), one=False):
    """
    查询数据（SELECT）
    :param sql: SQL 语句
    :param params: 参数元组
    :param one: 是否只取一条
    :return: dict 列表 或 单个 dict
    """
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        # 转为 dict 列表
        result = [dict(row) for row in rows]
        return (result[0] if result else None) if one else result
    finally:
        conn.close()


def execute(sql, params=()):
    """
    执行写操作（INSERT/UPDATE/DELETE）
    :param sql: SQL 语句
    :param params: 参数元组
    :return: lastrowid（插入时）或 rowcount（更新/删除时）
    """
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.lastrowid or cursor.rowcount
    finally:
        conn.close()


# 模块导入时自动初始化数据库
if __name__ != "__main__":
    init_db()
