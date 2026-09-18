# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
文件上传与解析测试
覆盖：TXT / DOCX / PDF / 非法格式 / 空文件 / 超大文件 / 粘贴文本 / AI 异常
AI 相关用例全部使用 mock，不调用真实 API。
"""
import io
import os
import glob

from backend.config import UPLOAD_DIR


# ===== 测试文件构造辅助 =====

def _minimal_pdf(text: str) -> bytes:
    """手工构造一个结构完整、带 xref 表的单页 PDF（pdfplumber 可解析）"""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    ]
    stream = b"BT /F1 12 Tf 72 720 Td (%b) Tj ET" % text.encode("ascii")
    objects.append(b"<< /Length %d >>\nstream\n%b\nendstream" % (len(stream), stream))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%b\nendobj\n" % (i, obj)

    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF"
            % (len(objects) + 1, xref_pos))
    return out


def _minimal_docx(paragraph: str) -> bytes:
    """用 python-docx 在内存中生成 docx"""
    from docx import Document
    doc = Document()
    doc.add_paragraph(paragraph)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _upload(client, filename, content: bytes):
    return client.post(
        "/api/upload/file",
        data={"file": (io.BytesIO(content), filename)},
        content_type="multipart/form-data",
    )


# ===== TXT（走正则兜底，无需 AI）=====

def test_upload_txt(client):
    """TXT 文件可解析并提取排班"""
    content = "张三 2026-03-15 08:00-12:00 图书馆一楼".encode("utf-8")
    resp = _upload(client, "排班.txt", content)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["schedules"][0]["name"] == "张三"
    assert body["data"]["schedules"][0]["location"] == "图书馆一楼"


def test_upload_txt_non_schedule_text(client):
    """TXT 中没有排班行时正常返回 0 条，不制造垃圾日程"""
    content = "这是一份普通通知，没有任何排班信息。".encode("utf-8")
    resp = _upload(client, "通知.txt", content)
    assert resp.status_code == 200
    assert resp.get_json()["data"]["total"] == 0


def test_temp_file_cleanup_after_parse(client):
    """解析完成后临时文件必须被清理（upload 目录不应残留）"""
    content = "李四 2026-03-16 09:00-13:00 行政楼".encode("utf-8")
    _upload(client, "待删除.txt", content)
    leftovers = glob.glob(os.path.join(UPLOAD_DIR, "*.txt"))
    assert leftovers == []


# ===== DOCX =====

def test_upload_docx(client):
    """DOCX 文件可解析（python-docx 真实读取）"""
    content = _minimal_docx("王五 2026-03-17 14:00-18:00 行政楼201")
    resp = _upload(client, "值班表.docx", content)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["data"]["total"] == 1
    assert body["data"]["schedules"][0]["name"] == "王五"


# ===== PDF（AI 使用 mock，真实走 pdfplumber 解析）=====

def test_upload_pdf_with_mock_ai(client, mock_ai):
    """PDF 真实解析 + mock AI 提取，返回正常结果"""
    mock_ai("normal_schedule.json")
    pdf_bytes = _minimal_pdf("Zhang San 2026-03-15 08:00-12:00 Library")
    resp = _upload(client, "schedule.pdf", pdf_bytes)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["schedules"][0]["name"] == "张三"


# ===== 非法与边界情况 =====

def test_upload_doc_rejected(client):
    """旧版 .doc 暂不支持，返回 400"""
    resp = _upload(client, "旧版.doc", b"fake doc binary")
    assert resp.status_code == 400
    assert "PDF / DOCX / TXT" in resp.get_json()["msg"]


def test_upload_exe_rejected(client):
    """非法扩展名一律拒绝"""
    resp = _upload(client, "virus.exe", b"MZ")
    assert resp.status_code == 400


def test_upload_empty_file(client):
    """空文件返回 400"""
    resp = _upload(client, "empty.txt", b"")
    assert resp.status_code == 400
    assert resp.get_json()["code"] == 1


def test_upload_oversized_file(client):
    """超过 10MB 上限返回 413"""
    big = b"a" * (11 * 1024 * 1024)
    resp = _upload(client, "big.txt", big)
    assert resp.status_code == 413
    assert resp.get_json()["code"] == 1


# ===== 粘贴文本 =====

def test_paste_text_fallback(client):
    """粘贴文本走正则兜底提取"""
    resp = client.post("/api/upload/text", json={
        "text": "赵六 2026-03-18 08:00-12:00 体育馆"
    })
    assert resp.status_code == 200
    assert resp.get_json()["data"]["total"] == 1


def test_paste_text_fallback_first_person(client):
    """兜底正则支持对话场景的"我是X"前缀（单行）"""
    # 姓名重复出现
    resp = client.post("/api/upload/text", json={
        "text": "我是张三，张三 2026-03-15 08:00-12:00 图书馆一楼"
    })
    data = resp.get_json()["data"]
    assert data["total"] == 1
    assert data["schedules"][0]["name"] == "张三"

    # 姓名未重复，直接跟日期
    resp2 = client.post("/api/upload/text", json={
        "text": "我是张三 2026-03-15 08:00-12:00 图书馆一楼"
    })
    data2 = resp2.get_json()["data"]
    assert data2["total"] == 1
    assert data2["schedules"][0]["name"] == "张三"


def test_paste_text_empty(client):
    """空文本返回 400"""
    resp = client.post("/api/upload/text", json={"text": ""})
    assert resp.status_code == 400


def test_paste_text_missing_fields_creates_qa(client, mock_ai):
    """AI 返回缺失字段时本地校验生成 QA（且不盲信 AI 的 missing_fields）"""
    mock_ai("missing_time.json")
    resp = client.post("/api/upload/text", json={"text": "李四明天值班"})
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    # 本地校验结果：start_time 实际有值，缺失应为 end_time、location
    fields = sorted(q["field"] for q in data["questions"])
    assert fields == ["end_time", "location"]


def test_paste_text_multiple_schedules(client, mock_ai):
    """多条排班正确提取，仅缺失的那一条生成 QA"""
    mock_ai("multiple_schedules.json")
    resp = client.post("/api/upload/text", json={"text": "多人值班表"})
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["total"] == 2
    assert len(data["questions"]) == 1
    assert data["questions"][0]["field"] == "location"


def test_paste_text_ai_bad_payload(client, mock_ai_bad_payload):
    """AI 返回格式异常时接口给出明确 502 错误，而不是静默返回 0 条"""
    resp = client.post("/api/upload/text", json={"text": "测试"})
    assert resp.status_code == 502
    body = resp.get_json()
    assert body["code"] == 1
    assert "AI" in body["msg"]
