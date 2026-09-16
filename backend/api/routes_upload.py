# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
文件上传与文本粘贴接口
接收 PDF/Word/文本，调用解析器+AI抽取，返回提取结果
"""
import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from backend.config import UPLOAD_DIR
from backend.core.parser import parse_document
from backend.core.extractor import extract_schedules
from backend.db.database import execute

upload_bp = Blueprint("upload", __name__)

# 允许的文件类型
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt"}


def allowed_file(filename):
    """检查文件类型是否允许"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@upload_bp.route("/api/upload/file", methods=["POST"])
def upload_file():
    """上传文件解析排班（PDF/Word/TXT）"""
    if "file" not in request.files:
        return jsonify({"code": 1, "msg": "未收到文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"code": 1, "msg": "文件名为空"}), 400

    if not allowed_file(file.filename):
        return jsonify({"code": 1, "msg": "不支持的文件类型，请上传 PDF/Word/TXT"}), 400

    # 保存文件
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    try:
        # 解析文档内容
        text = parse_document(filepath)
        # AI 提取排班信息
        result = extract_schedules(text, source_type="upload", original_text=text[:500])

        # 记录解析日志
        execute(
            "INSERT INTO parse_logs (file_name, file_type, total_extracted, has_ambiguity, status) VALUES (?, ?, ?, ?, ?)",
            (filename, filename.rsplit(".", 1)[1].lower(), result.get("total", 0), 1 if result.get("questions") else 0, "success"),
        )

        return jsonify({"code": 0, "msg": "解析成功", "data": result})
    except Exception as e:
        return jsonify({"code": 1, "msg": f"解析失败: {str(e)}"}), 500


@upload_bp.route("/api/upload/text", methods=["POST"])
def upload_text():
    """粘贴文本解析排班"""
    data = request.get_json(force=True)
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"code": 1, "msg": "文本内容为空"}), 400

    try:
        # AI 提取排班信息
        result = extract_schedules(text, source_type="paste", original_text=text[:500])

        # 记录解析日志
        execute(
            "INSERT INTO parse_logs (file_name, file_type, total_extracted, has_ambiguity, status) VALUES (?, ?, ?, ?, ?)",
            ("paste_input", "text", result.get("total", 0), 1 if result.get("questions") else 0, "success"),
        )

        return jsonify({"code": 0, "msg": "解析成功", "data": result})
    except Exception as e:
        return jsonify({"code": 1, "msg": f"解析失败: {str(e)}"}), 500
