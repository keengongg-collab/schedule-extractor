# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
Streamlit PC 端管理工具
管理员批量上传文档解析、预览排班表格、Excel 导出

启动方式：streamlit run app_streamlit.py
"""
import streamlit as st
import requests
import pandas as pd
import sys
import os

# 添加项目根目录到路径，方便导入 pc_client 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pc_client.excel_export import export_to_excel
from pc_client.notifier import send_test_notification, send_schedule_reminder

# 后端 API 地址（可通过环境变量 API_BASE 覆盖）
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:5000")

# ===== 页面配置 =====
st.set_page_config(
    page_title="排班管理工具",
    page_icon="📅",
    layout="wide",
)


def main():
    """主页面"""
    st.title("📅 轻量化AI排班日程提取工具 - 管理端")
    st.markdown("---")

    # 侧边栏导航
    st.sidebar.title("功能菜单")
    st.sidebar.caption(f"后端地址：`{API_BASE}`\n\n若页面报连接错误，请先启动后端（start.bat 或 `python backend/app.py`）。")
    menu = st.sidebar.radio("选择功能", [
        "📋 排班总览",
        "📤 上传文档解析",
        "✏️ 手动添加日程",
        "❓ 待补充信息",
        "🔔 提醒管理",
        "📤 导出 Excel",
    ])

    # 根据选择渲染不同页面
    if menu == "📋 排班总览":
        page_schedule_overview()
    elif menu == "📤 上传文档解析":
        page_upload_parse()
    elif menu == "✏️ 手动添加日程":
        page_manual_add()
    elif menu == "❓ 待补充信息":
        page_pending_questions()
    elif menu == "🔔 提醒管理":
        page_reminder_management()
    elif menu == "📤 导出 Excel":
        page_export_excel()


def page_schedule_overview():
    """排班总览页面"""
    st.header("📋 排班总览")

    # 搜索框
    name_filter = st.text_input("按姓名筛选（留空查看全部）", "")

    # 调用 API 获取数据
    try:
        params = {"name": name_filter} if name_filter else {}
        resp = requests.get(f"{API_BASE}/api/schedules", params=params, timeout=10)
        data = resp.json()
        schedules = data.get("data", [])

        if not schedules:
            st.info("暂无排班数据")
            return

        st.success(f"共 {len(schedules)} 条排班记录")

        # 表格展示
        df = pd.DataFrame(schedules)
        # 选择展示列
        display_cols = ["name", "duty_date", "start_time", "end_time", "location", "remark", "is_confirmed"]
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        # 单条详情查看
        st.subheader("查看单条详情")
        selected_id = st.selectbox(
            "选择日程",
            options=[s["id"] for s in schedules],
            format_func=lambda x: f"#{x} - {next((s['name'] for s in schedules if s['id']==x), '')} ({next((s['duty_date'] for s in schedules if s['id']==x), '')})"
        )
        if selected_id:
            detail = next((s for s in schedules if s["id"] == selected_id), None)
            if detail:
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**姓名**: {detail.get('name', '')}")
                    st.write(f"**日期**: {detail.get('duty_date', '')}")
                    st.write(f"**时间**: {detail.get('start_time', '')} - {detail.get('end_time', '')}")
                with col2:
                    st.write(f"**地点**: {detail.get('location', '')}")
                    st.write(f"**备注**: {detail.get('remark', '')}")
                    st.write(f"**确认状态**: {'已确认' if detail.get('is_confirmed') else '待确认'}")

                # 删除按钮
                if st.button("删除此条日程", type="secondary"):
                    resp = requests.delete(f"{API_BASE}/api/schedules/{selected_id}", timeout=10)
                    if resp.json().get("code") == 0:
                        st.success("删除成功")
                        st.rerun()

    except requests.ConnectionError:
        st.error(f"无法连接后端服务（{API_BASE}），请先启动后端：python backend/app.py 或双击 start.bat")


def page_upload_parse():
    """上传文档解析页面"""
    st.header("📤 上传文档解析")

    # 文件上传
    uploaded_files = st.file_uploader(
        "选择排班文档（支持 PDF / Word / TXT）",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        for file in uploaded_files:
            st.write(f"**文件**: {file.name}")

        if st.button("开始解析", type="primary"):
            progress = st.progress(0)
            all_results = []

            for i, file in enumerate(uploaded_files):
                files = {"file": (file.name, file.getvalue())}
                try:
                    resp = requests.post(f"{API_BASE}/api/upload/file", files=files, timeout=60)
                    data = resp.json()
                    if data.get("code") == 0:
                        result = data.get("data", {})
                        total = result.get("total", 0)
                        questions = result.get("questions", [])
                        st.success(f"{file.name}: 提取 {total} 条日程")
                        if questions:
                            st.warning(f"{file.name}: {len(questions)} 条信息不完整，需补充")
                        all_results.extend(result.get("schedules", []))
                    else:
                        st.error(f"{file.name}: {data.get('msg', '解析失败')}")
                except Exception as e:
                    st.error(f"{file.name}: 请求失败 - {e}")

                progress.progress((i + 1) / len(uploaded_files))

            if all_results:
                st.subheader("解析结果预览")
                st.dataframe(pd.DataFrame(all_results), use_container_width=True)

    # 文本粘贴解析
    st.markdown("---")
    st.subheader("或粘贴文本解析")
    text_input = st.text_area("粘贴排班文本", height=200, placeholder="例如：张三 2024-03-15 08:00-12:00 图书馆一楼")

    if st.button("解析文本") and text_input.strip():
        try:
            resp = requests.post(f"{API_BASE}/api/upload/text", json={"text": text_input}, timeout=30)
            data = resp.json()
            if data.get("code") == 0:
                result = data.get("data", {})
                st.success(f"提取 {result.get('total', 0)} 条日程")
                if result.get("schedules"):
                    st.dataframe(pd.DataFrame(result["schedules"]), use_container_width=True)
                if result.get("questions"):
                    st.warning(f"{len(result['questions'])} 条信息不完整，请在「待补充信息」中处理")
            else:
                st.error(data.get("msg", "解析失败"))
        except requests.ConnectionError:
            st.error(f"无法连接后端服务（{API_BASE}），请确认后端已启动")


def page_manual_add():
    """手动添加日程页面"""
    st.header("✏️ 手动添加日程")

    with st.form("add_schedule"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("姓名 *")
            duty_date = st.date_input("值班日期 *")
            start_time = st.time_input("开始时间")
        with col2:
            location = st.text_input("值班地点")
            end_time = st.time_input("结束时间")
            remark = st.text_input("备注")

        submitted = st.form_submit_button("添加日程")

        if submitted:
            if not name:
                st.error("姓名为必填项")
            else:
                payload = {
                    "name": name,
                    "duty_date": str(duty_date),
                    "start_time": start_time.strftime("%H:%M") if start_time else None,
                    "end_time": end_time.strftime("%H:%M") if end_time else None,
                    "location": location,
                    "remark": remark,
                    "source_type": "manual",
                }
                try:
                    resp = requests.post(f"{API_BASE}/api/schedules", json=payload, timeout=10)
                    if resp.json().get("code") == 0:
                        st.success("日程添加成功")
                    else:
                        st.error("添加失败")
                except requests.ConnectionError:
                    st.error(f"无法连接后端服务（{API_BASE}），请确认后端已启动")


def page_pending_questions():
    """待补充信息页面"""
    st.header("❓ 待补充信息")
    st.write("以下排班信息不完整，需要您补充确认。")

    try:
        resp = requests.get(f"{API_BASE}/api/qa/pending", timeout=10)
        data = resp.json()
        questions = data.get("data", [])

        if not questions:
            st.info("没有待补充的信息")
            return

        for q in questions:
            with st.expander(f"{q.get('question', '')} - {q.get('name', '')} {q.get('duty_date', '')}"):
                answer = st.text_input("请输入补充信息", key=f"answer_{q['id']}")
                if st.button("提交补充", key=f"submit_{q['id']}"):
                    if answer.strip():
                        resp = requests.post(
                            f"{API_BASE}/api/qa/answer",
                            json={"qa_id": q["id"], "answer": answer.strip()},
                            timeout=10,
                        )
                        if resp.json().get("code") == 0:
                            st.success("已补充，日程已更新")
                            st.rerun()
                    else:
                        st.error("请输入补充内容")

    except requests.ConnectionError:
                    st.error(f"无法连接后端服务（{API_BASE}），请确认后端已启动")


def page_reminder_management():
    """提醒管理页面"""
    st.header("🔔 提醒管理")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("创建提醒")
        with st.form("create_reminder"):
            schedule_id = st.number_input("日程ID", min_value=1, step=1)
            advance = st.number_input("提前提醒（分钟）", min_value=1, value=15, step=5)
            custom_msg = st.text_input("自定义提醒文案", "")
            if st.form_submit_button("创建提醒"):
                payload = {
                    "schedule_id": schedule_id,
                    "advance_minutes": advance,
                    "custom_message": custom_msg,
                }
                try:
                    resp = requests.post(f"{API_BASE}/api/reminders", json=payload, timeout=10)
                    if resp.json().get("code") == 0:
                        st.success("提醒已创建")
                    else:
                        st.error("创建失败")
                except requests.ConnectionError:
                    st.error(f"无法连接后端服务（{API_BASE}），请确认后端已启动")

    with col2:
        st.subheader("测试通知")
        if st.button("发送测试通知"):
            send_test_notification()
            st.info("已发送桌面通知")

        st.subheader("现有提醒列表")
        try:
            resp = requests.get(f"{API_BASE}/api/reminders", timeout=10)
            reminders = resp.json().get("data", [])
            if reminders:
                st.dataframe(pd.DataFrame(reminders), use_container_width=True, hide_index=True)
            else:
                st.info("暂无提醒配置")
        except requests.ConnectionError:
            st.error(f"无法连接后端服务（{API_BASE}），请确认后端已启动")


def page_export_excel():
    """Excel 导出页面"""
    st.header("📤 导出 Excel")

    try:
        resp = requests.get(f"{API_BASE}/api/schedules", timeout=10)
        schedules = resp.json().get("data", [])

        if not schedules:
            st.info("暂无排班数据可导出")
            return

        st.dataframe(pd.DataFrame(schedules), use_container_width=True, hide_index=True)

        if st.button("导出为 Excel", type="primary"):
            filepath = export_to_excel(schedules)
            if filepath:
                with open(filepath, "rb") as f:
                    st.download_button(
                        label="下载 Excel 文件",
                        data=f,
                        file_name=os.path.basename(filepath),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                st.success(f"已生成: {filepath}")
            else:
                st.error("导出失败")

    except requests.ConnectionError:
                    st.error(f"无法连接后端服务（{API_BASE}），请确认后端已启动")


if __name__ == "__main__":
    main()
