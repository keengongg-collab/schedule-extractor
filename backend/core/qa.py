# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
问答模块
处理信息缺失时的提问与用户回答逻辑

流程（v1.0 保持"直接更新字段"的简单方案，不重新调用 AI）：
1. AI 提取排班 → validator 发现缺失字段 → 生成提问存入 qa_records
2. 前端展示待回答问题
3. 用户补充回答 → 校验 QA/日程存在性与字段白名单
   → 更新 qa_records 状态 → 更新日程对应字段

安全：
- field_name 必须在 validator.ALLOWED_QA_FIELDS 白名单内
- 禁止通过回答接口修改 id / created_at / source_type / is_confirmed 等字段
"""
from backend.db.database import query, execute
from backend.core.validator import ALLOWED_QA_FIELDS
from backend.utils.helpers import format_date, format_time
from backend.utils.logger import get_logger

logger = get_logger("qa")


def get_pending_questions() -> list:
    """获取所有待回答的提问"""
    return query(
        """SELECT q.*, s.name, s.duty_date, s.start_time
           FROM qa_records q
           LEFT JOIN schedules s ON q.schedule_id = s.id
           WHERE q.status = 'pending'
           ORDER BY q.created_at"""
    )


def submit_answer(qa_id: int, answer: str) -> dict:
    """
    提交用户回答，更新日程信息

    :param qa_id: 问答记录ID
    :param answer: 用户回答内容
    :return: {"success": bool, "status": int, "msg": str, ...}
             status 对应 HTTP 状态码（404/400/200）
    """
    # 1. QA 记录必须存在
    qa = query("SELECT * FROM qa_records WHERE id = ?", (qa_id,), one=True)
    if not qa:
        return {"success": False, "status": 404, "msg": "问题不存在"}

    # 2. 防重复回答
    if qa["status"] != "pending":
        return {"success": False, "status": 400, "msg": "该问题已回答，请勿重复提交"}

    field_name = qa.get("field_name")
    schedule_id = qa.get("schedule_id")

    # 3. 字段必须在白名单内（防止 SQL 注入与越权改字段）
    if field_name not in ALLOWED_QA_FIELDS:
        logger.warning("拒绝非法字段更新 qa_id=%s field=%s", qa_id, field_name)
        return {"success": False, "status": 400, "msg": f"字段 {field_name} 不允许通过回答接口修改"}

    # 4. 关联日程必须存在
    schedule = query("SELECT id FROM schedules WHERE id = ?", (schedule_id,), one=True)
    if not schedule:
        return {"success": False, "status": 404, "msg": "关联的日程不存在"}

    # 5. 按字段类型做格式归一
    value = answer.strip()
    if field_name == "duty_date":
        value = format_date(value)
    elif field_name in ("start_time", "end_time"):
        value = format_time(value)

    # 6. 更新日程字段，再更新 QA 状态
    execute(
        f"UPDATE schedules SET {field_name} = ?, updated_at = datetime('now','localtime') WHERE id = ?",
        (value, schedule_id),
    )
    execute("UPDATE qa_records SET answer = ?, status = 'answered' WHERE id = ?", (value, qa_id))
    logger.info("QA 已回答 id=%s schedule_id=%s field=%s", qa_id, schedule_id, field_name)

    return {
        "success": True,
        "status": 200,
        "msg": "回答已提交，日程已更新",
        "data": {"qa_id": qa_id, "schedule_id": schedule_id, "field": field_name, "value": value},
    }
