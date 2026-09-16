"""
Excel 导出模块
使用 pandas 将排班数据导出为 Excel 文件
"""
import pandas as pd
import os
from datetime import datetime


def export_to_excel(schedules: list, output_dir: str = ".") -> str:
    """
    将排班数据导出为 Excel 文件
    :param schedules: 排班数据列表（dict 列表）
    :param output_dir: 输出目录
    :return: 生成的文件路径
    """
    if not schedules:
        return ""

    # 转为 DataFrame
    df = pd.DataFrame(schedules)

    # 选择并重命名列（只导出有意义的字段）
    column_map = {
        "id": "序号",
        "name": "姓名",
        "duty_date": "值班日期",
        "start_time": "开始时间",
        "end_time": "结束时间",
        "location": "值班地点",
        "remark": "备注",
        "is_confirmed": "已确认",
    }

    # 只保留存在的列
    export_cols = [col for col in column_map.keys() if col in df.columns]
    df = df[export_cols].rename(columns=column_map)

    # 确认状态转为中文
    if "已确认" in df.columns:
        df["已确认"] = df["已确认"].map({True: "已确认", False: "待确认", 1: "已确认", 0: "待确认"})

    # 生成文件名
    filename = f"排班表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(output_dir, filename)

    # 写入 Excel
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="排班表", index=False)

        # 自动调整列宽
        worksheet = writer.sheets["排班表"]
        for column in worksheet.columns:
            max_length = max(len(str(cell.value)) for cell in column if cell.value)
            worksheet.column_dimensions[column[0].column_letter].width = max_length + 4

    return filepath
