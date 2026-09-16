"""
问答模块
处理信息缺失时的提问与用户回答逻辑

流程：
1. AI 提取排班 → 发现缺失字段 → 生成提问存入 qa_records
2. 前端展示待回答问题
3. 用户补充回答 → 更新 qa_records 状态 → 更新日程数据
4. 可选：用户回答后重新调用 AI 解析
"""
from backend.db.database import query, execute


def get_pending_questions() -> list:
    """获取所有待回答的提问"""
    rows = query(
        """SELECT q.*, s.name, s.duty_date, s.start_time
           FROM qa_records q
           LEFT JOIN schedules s ON q.schedule_id = s.id
           WHERE q.status = 'pending'
           ORDER BY q.created_at"""
    )
    return rows


def submit_answer(qa_id: int, answer: str) -> dict:
    """
    提交用户回答，更新日程信息
    :param qa_id: 问答记录ID
    :param answer: 用户回答内容
    :return: 更新结果
    """
    # 获取问答记录
    qa = query("SELECT * FROM qa_records WHERE id = ?", (qa_id,), one=True)
    if not qa:
        return {"success": False, "msg": "问答记录不存在"}

    if qa["status"] != "pending":
        return {"success": False, "msg": "该问题已回答"}

    # 更新问答记录状态
    execute("UPDATE qa_records SET answer = ?, status = 'answered' WHERE id = ?", (answer, qa_id))

    # 如果有对应字段名，更新日程
    field_name = qa.get("field_name")
    schedule_id = qa.get("schedule_id")

    if field_name and schedule_id:
        # 安全地更新对应字段（field_name 已在生成时限定）
        execute(
            f"UPDATE schedules SET {field_name} = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (answer, schedule_id),
        )
        return {"success": True, "msg": "回答已提交，日程已更新", "schedule_id": schedule_id}

    return {"success": True, "msg": "回答已提交"}


def resolve_ambiguity(schedule_id: int, user_clarification: str) -> dict:
    """
    用户对歧义信息进行澄清说明，重新解析
    :param schedule_id: 日程ID
    :param user_clarification: 用户的澄清文本
    """
    # 获取原始日程
    schedule = query("SELECT * FROM schedules WHERE id = ?", (schedule_id,), one=True)
    if not schedule:
        return {"success": False, "msg": "日程不存在"}

    # 将用户澄清内容追加到原始文本，重新解析
    combined_text = f"{schedule.get('original_text', '')}\n用户补充：{user_clarification}"

    # 重新调用 AI 解析（此处简化处理，直接更新字段）
    # 实际可调用 extractor 重新解析
    from backend.core.extractor import extract_schedules
    result = extract_schedules(combined_text, source_type="clarify", original_text=combined_text[:500])

    return {"success": True, "msg": "已根据补充信息重新解析", "data": result}
