# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
文件上传与文本粘贴接口
接收 PDF / DOCX / TXT，调用解析器 + AI 抽取，返回提取结果

安全要点（v1.0）：
- 服务端使用 UUID 随机文件名落盘，不直接使用用户原始文件名作为存储路径
- parse_logs 中仍记录原始文件名，便于追溯
- 解析完成（或失败）后在 finally 中删除临时文件
- 限制扩展名、空文件与文件大小（MAX_CONTENT_LENGTH 在 app 中配置）
"""
import os
import uuid

from flask import Blueprint, request, jsonify

from backend.config import UPLOAD_DIR
from backend.core.parser import parse_document
from backend.core.extractor import extract_schedules, apply_schedules
from backend.core.validator import ExtractionError
from backend.db.database import execute
from backend.utils.logger import get_logger

upload_bp = Blueprint("upload", __name__)
logger = get_logger("upload")

# v1.0 正式支持的文件类型（旧版 .doc 无法用 python-docx 解析，暂不支持）
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}


def _parse_dry_run(request) -> bool:
    """解析 dry_run 参数：为 True 时只预览不落库（PC 端导入确认前预览）"""
    raw = (request.args.get("dry_run") or request.form.get("dry_run") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def allowed_file(filename):
    """检查文件类型是否允许"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _log_parse(file_name, file_type, total, has_ambiguity, status):
    """写入解析日志（失败不影响主流程）"""
    try:
        execute(
            "INSERT INTO parse_logs (file_name, file_type, total_extracted, has_ambiguity, status) "
            "VALUES (?, ?, ?, ?, ?)",
            (file_name, file_type, total, has_ambiguity, status),
        )
    except Exception as e:
        logger.warning("解析日志写入失败: %s", e)


@upload_bp.route("/api/upload/file", methods=["POST"])
def upload_file():
    """上传文件解析排班（PDF / DOCX / TXT）"""
    if "file" not in request.files:
        return jsonify({"code": 1, "msg": "未收到文件", "data": None}), 400

    file = request.files["file"]
    original_name = file.filename or ""
    if original_name == "":
        return jsonify({"code": 1, "msg": "文件名为空", "data": None}), 400

    ext = original_name.rsplit(".", 1)[1].lower() if "." in original_name else ""
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "code": 1,
            "msg": f"不支持的文件类型 .{ext or '未知'}，v1.0 仅支持 PDF / DOCX / TXT（暂不支持旧版 .doc）",
            "data": None,
        }), 400

    # 空文件检查
    file.stream.seek(0, os.SEEK_END)
    file_size = file.stream.tell()
    file.stream.seek(0)
    if file_size == 0:
        return jsonify({"code": 1, "msg": "文件内容为空", "data": None}), 400

    # UUID 随机文件名落盘（仅保留扩展名），避免覆盖与路径风险
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    file.save(filepath)
    logger.info("收到上传文件 原始名=%s 类型=%s 大小=%dB 临时文件=%s",
                original_name, ext, file_size, safe_name)

    try:
        # 解析文档内容
        text = parse_document(filepath)
        if not text.strip():
            _log_parse(original_name, ext, 0, 0, "failed")
            return jsonify({"code": 1, "msg": "未能从文件中解析出文本内容", "data": None}), 422

        logger.info("文件解析完成 原始名=%s 提取文本长度=%d", original_name, len(text))

        dry_run = _parse_dry_run(request)
        # AI 提取排班信息（dry_run=True 时只预览不落库，PC 端确认后再 apply）
        result = extract_schedules(text, source_type="upload", original_text=text[:500], dry_run=dry_run)
        _log_parse(original_name, ext, result.get("total", 0),
                   1 if result.get("questions") else 0, "preview" if dry_run else "success")

        return jsonify({"code": 0, "msg": "解析成功", "data": result})
    except ExtractionError as e:
        # AI 返回结构异常：明确告知，不静默返回 0 条
        logger.error("AI 抽取结果异常 原始名=%s 原因=%s", original_name, e)
        _log_parse(original_name, ext, 0, 0, "failed")
        return jsonify({"code": 1, "msg": f"AI 识别结果格式异常：{e}", "data": None}), 502
    except Exception as e:
        logger.exception("文件解析失败 原始名=%s", original_name)
        _log_parse(original_name, ext, 0, 0, "failed")
        return jsonify({"code": 1, "msg": f"解析失败: {e}", "data": None}), 500
    finally:
        # 无论成功失败都清理临时文件
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info("临时文件已清理 %s", safe_name)
        except OSError as e:
            logger.warning("临时文件清理失败 %s: %s", safe_name, e)


@upload_bp.route("/api/upload/text", methods=["POST"])
def upload_text():
    """粘贴文本解析排班"""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()

    if not text:
        return jsonify({"code": 1, "msg": "文本内容为空", "data": None}), 400

    try:
        logger.info("收到粘贴文本解析 长度=%d", len(text))
        dry_run = bool((data.get("dry_run") or "").strip().lower() in ("1", "true", "yes", "on"))
        result = extract_schedules(text, source_type="paste", original_text=text[:500], dry_run=dry_run)

        _log_parse("paste_input", "text", result.get("total", 0),
                   1 if result.get("questions") else 0, "preview" if dry_run else "success")
        return jsonify({"code": 0, "msg": "解析成功", "data": result})
    except ExtractionError as e:
        logger.error("AI 抽取结果异常: %s", e)
        _log_parse("paste_input", "text", 0, 0, "failed")
        return jsonify({"code": 1, "msg": f"AI 识别结果格式异常：{e}", "data": None}), 502
    except Exception as e:
        logger.exception("文本解析失败")
        _log_parse("paste_input", "text", 0, 0, "failed")
        return jsonify({"code": 1, "msg": f"解析失败: {e}", "data": None}), 500


@upload_bp.route("/api/upload/apply", methods=["POST"])
def apply_upload():
    """
    确认导入：把 dry_run 预览结果正式落库，并为缺失字段生成 QA 待补充记录。
    body: {"schedules": [预览列表], "source_type": "upload", "original_text": "..."}
    """
    data = request.get_json(silent=True) or {}
    schedules = data.get("schedules")

    if not isinstance(schedules, list) or not schedules:
        return jsonify({"code": 1, "msg": "缺少待确认的日程列表", "data": None}), 400

    try:
        result = apply_schedules(
            schedules,
            source_type=data.get("source_type") or "upload",
            original_text=data.get("original_text") or "",
        )
        _log_parse("apply_confirm", "preview", result.get("total", 0),
                   1 if result.get("questions") else 0, "success")
        logger.info("确认导入完成 共 %d 条日程", result.get("total", 0))
        return jsonify({"code": 0, "msg": f"已确认 {result['total']} 条日程", "data": result})
    except Exception as e:
        logger.exception("确认导入失败")
        return jsonify({"code": 1, "msg": f"确认导入失败: {e}", "data": None}), 500
