# ============================================================
# 轻量化AI文档排班日程提取工具
# Copyright (c) 2026 schedule-extractor Contributors
# Licensed under MIT License
# 详见 LICENSE 文件与 PRIVACY.md 隐私声明
# ============================================================

"""
服务层：日程数据提供者

- ApiClient   ：真实 Flask API 客户端（接入后端 /api/schedules 等接口）
- MockProvider：UI 开发阶段使用的示例数据提供者（不依赖后端即可预览界面）

两者提供相同的方法签名，MainWindow 通过构造参数注入 provider，
Phase 3 接入后端时只需把 MockProvider 换成 ApiClient。
"""
import os
import sys
from datetime import date, timedelta

import requests

# 项目根目录加入导入路径（便于直接运行 pc_client/app.py）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.utils.helpers import format_date  # noqa: E402


class ScheduleProvider:
    """日程数据提供者接口（duck typing，子类实现相同方法即可）"""

    def get_day(self, day: str) -> list:
        """获取某一天的日程列表（按开始时间排序）"""
        raise NotImplementedError

    def get_range(self, start: str, end: str) -> list:
        """获取日期范围 [start, end] 内的日程列表"""
        raise NotImplementedError

    def get_schedule(self, schedule_id: int) -> dict:
        """获取单条日程详情"""
        raise NotImplementedError

    def create_schedule(self, payload: dict) -> dict:
        """新建日程，返回 {"id": ...}"""
        raise NotImplementedError

    def update_schedule(self, schedule_id: int, payload: dict) -> None:
        """更新日程（payload 为要修改的字段）"""
        raise NotImplementedError

    def delete_schedule(self, schedule_id: int) -> None:
        """删除日程"""
        raise NotImplementedError

    def confirm_schedule(self, schedule_id: int) -> None:
        """确认日程"""
        raise NotImplementedError

    def get_reminders(self) -> list:
        """获取提醒列表"""
        raise NotImplementedError

    def create_reminder(self, schedule_id: int, advance_minutes: int = 15, custom_message: str = "") -> dict:
        """新建提醒，返回 {"id": ...}"""
        raise NotImplementedError

    def delete_reminder(self, reminder_id: int) -> None:
        """删除提醒"""
        raise NotImplementedError

    def health_check(self) -> dict:
        """后端健康检查，返回 {"version": ...}"""
        raise NotImplementedError


class ApiClient(ScheduleProvider):
    """Flask 后端 API 客户端（Phase 3 启用，接口与 MockProvider 一致）"""

    def __init__(self, base_url: str = None):
        # 优先读取环境变量 API_BASE，与旧 Streamlit 端保持一致
        self.base_url = (base_url or os.getenv("API_BASE") or "http://127.0.0.1:5000").rstrip("/")

    def _request(self, method: str, path: str, **kwargs):
        """统一请求封装：10 秒超时 + 统一响应结构 {"code","msg","data"}"""
        try:
            resp = requests.request(method, f"{self.base_url}{path}", timeout=10, **kwargs)
            data = resp.json()
        except requests.ConnectionError:
            raise ConnectionError(f"无法连接后端服务（{self.base_url}），请确认后端已启动")
        except requests.Timeout:
            raise TimeoutError(f"请求超时：{method} {path}")
        except ValueError:
            raise ValueError(f"后端返回非 JSON 响应：HTTP {resp.status_code}")

        if data.get("code") != 0:
            raise RuntimeError(data.get("msg") or "请求失败")
        return data.get("data")

    def get_day(self, day: str) -> list:
        return self._request("GET", "/api/schedules", params={"date": day}) or []

    def get_range(self, start: str, end: str) -> list:
        return self._request("GET", "/api/schedules", params={"start": start, "end": end}) or []

    def get_schedule(self, schedule_id: int) -> dict:
        return self._request("GET", f"/api/schedules/{schedule_id}")

    def create_schedule(self, payload: dict) -> dict:
        return self._request("POST", "/api/schedules", json=payload)

    def update_schedule(self, schedule_id: int, payload: dict) -> None:
        self._request("PUT", f"/api/schedules/{schedule_id}", json=payload)

    def delete_schedule(self, schedule_id: int) -> None:
        self._request("DELETE", f"/api/schedules/{schedule_id}")

    def confirm_schedule(self, schedule_id: int) -> None:
        self._request("POST", f"/api/schedules/{schedule_id}/confirm")

    def upload_file(self, filepath: str, dry_run: bool = True) -> dict:
        """上传文件解析（PDF/DOCX/TXT），dry_run=True 只预览不落库"""
        with open(filepath, "rb") as f:
            try:
                resp = requests.post(
                    f"{self.base_url}/api/upload/file",
                    files={"file": (os.path.basename(filepath), f)},
                    params={"dry_run": "1"} if dry_run else None,
                    timeout=60,
                )
                data = resp.json()
            except requests.ConnectionError:
                raise ConnectionError(f"无法连接后端服务（{self.base_url}）")
            except requests.Timeout:
                raise TimeoutError("上传解析超时")
            except ValueError:
                raise ValueError(f"后端返回非 JSON 响应：HTTP {resp.status_code}")
        if data.get("code") != 0:
            raise RuntimeError(data.get("msg") or "上传解析失败")
        return data.get("data")

    def upload_text(self, text: str, dry_run: bool = True) -> dict:
        """粘贴文本解析，dry_run=True 只预览不落库"""
        payload = {"text": text}
        if dry_run:
            payload["dry_run"] = "1"
        return self._request("POST", "/api/upload/text", json=payload)

    def apply_schedules(self, schedules: list, source_type: str = "upload", original_text: str = "") -> dict:
        """确认导入：把预览结果落库，缺失字段自动生成 QA 记录"""
        return self._request("POST", "/api/upload/apply", json={
            "schedules": schedules,
            "source_type": source_type,
            "original_text": original_text,
        })

    def parse_intent(self, text: str) -> dict:
        """AI 自然语言指令解析（只解析预览，不写库）"""
        return self._request("POST", "/api/ai/intent", json={"text": text})

    # ===== 提醒 =====

    def get_reminders(self) -> list:
        return self._request("GET", "/api/reminders") or []

    def create_reminder(self, schedule_id: int, advance_minutes: int = 15, custom_message: str = "") -> dict:
        return self._request("POST", "/api/reminders", json={
            "schedule_id": schedule_id,
            "advance_minutes": int(advance_minutes),
            "custom_message": custom_message,
        })

    def delete_reminder(self, reminder_id: int) -> None:
        self._request("DELETE", f"/api/reminders/{reminder_id}")

    # ===== 系统 =====

    def health_check(self) -> dict:
        return self._request("GET", "/api/health")


# ============================================================
# Mock 数据提供者（Phase 2 UI 预览用，不访问后端）
# ============================================================

def _make(sid, name, duty_date, start_time, end_time, location, remark="", confirmed=True):
    return {
        "id": sid,
        "name": name,
        "duty_date": format_date(duty_date),  # 统一存 YYYY-MM-DD 字符串，与后端一致
        "start_time": start_time,
        "end_time": end_time,
        "location": location,
        "remark": remark,
        "is_confirmed": confirmed,
        "source_type": "manual",
    }


def _build_mock_schedules() -> list:
    """构造围绕今天/本月的示例日程（日期按当前日期动态生成）"""
    today = date.today()
    rows = [
        _make(1, "项目会议", today, "09:00", "10:30", "会议室 A", "项目周会", True),
        _make(2, "午餐", today, "11:30", "12:30", "", "和同事聚餐", True),
        _make(3, "值班", today, "14:00", "17:00", "图书馆", "", True),
        _make(4, "健身", today, "18:00", "19:30", "健身房", "", False),
        _make(5, "图书馆开会", today + timedelta(days=1), "15:00", "16:30", "图书馆", "", True),
        _make(6, "产品评审", today + timedelta(days=1), "09:30", "11:00", "会议室 B", "", True),
        _make(7, "客户拜访", today + timedelta(days=3), "14:30", "16:00", "客户公司", "提前准备材料", True),
        _make(8, "部门例会", today + timedelta(days=-2), "10:00", "11:00", "大会议室", "", True),
        _make(9, "体检", today + timedelta(days=7), "08:30", "10:00", "体检中心", "空腹前往", False),
    ]
    return rows


class MockProvider(ScheduleProvider):
    """UI 开发阶段的数据源：内置示例数据，支持增删改（内存态）"""

    def __init__(self):
        self._rows = _build_mock_schedules()
        self._next_id = max((r["id"] for r in self._rows), default=0) + 1
        self._reminders = []
        self._next_reminder_id = 1

    def _sorted(self, rows):
        return sorted(rows, key=lambda r: (r["duty_date"], r["start_time"] or ""))

    def get_day(self, day: str) -> list:
        return self._sorted([r for r in self._rows if r["duty_date"] == format_date(day)])

    def get_range(self, start: str, end: str) -> list:
        start, end = format_date(start), format_date(end)
        return self._sorted([r for r in self._rows if start <= r["duty_date"] <= end])

    def get_schedule(self, schedule_id: int) -> dict:
        for r in self._rows:
            if r["id"] == schedule_id:
                return dict(r)
        raise RuntimeError(f"日程不存在 id={schedule_id}")

    def create_schedule(self, payload: dict) -> dict:
        row = {
            "id": self._next_id,
            "name": payload.get("name", ""),
            "duty_date": format_date(payload.get("duty_date", "")),
            "start_time": payload.get("start_time") or None,
            "end_time": payload.get("end_time") or None,
            "location": payload.get("location") or None,
            "remark": payload.get("remark", ""),
            "is_confirmed": bool(payload.get("is_confirmed", True)),
            "source_type": "manual",
        }
        self._next_id += 1
        self._rows.append(row)
        return {"id": row["id"]}

    def update_schedule(self, schedule_id: int, payload: dict) -> None:
        for r in self._rows:
            if r["id"] == schedule_id:
                for key, value in payload.items():
                    if key == "is_confirmed":
                        r[key] = bool(value)
                    elif key in ("duty_date",):
                        r[key] = format_date(value)
                    else:
                        r[key] = value
                return
        raise RuntimeError(f"日程不存在 id={schedule_id}")

    def delete_schedule(self, schedule_id: int) -> None:
        self._rows = [r for r in self._rows if r["id"] != schedule_id]

    def confirm_schedule(self, schedule_id: int) -> None:
        self.update_schedule(schedule_id, {"is_confirmed": True})

    # ===== 提醒（Mock：内存态）=====

    def get_reminders(self) -> list:
        rows = []
        for r in self._reminders:
            row = dict(r)
            sched = self.get_schedule(r["schedule_id"])
            row.update({
                "name": sched.get("name"),
                "duty_date": sched.get("duty_date"),
                "start_time": sched.get("start_time"),
                "location": sched.get("location"),
            })
            rows.append(row)
        return sorted(rows, key=lambda r: (r.get("duty_date") or "", r.get("start_time") or ""))

    def create_reminder(self, schedule_id: int, advance_minutes: int = 15, custom_message: str = "") -> dict:
        try:
            self.get_schedule(schedule_id)
        except RuntimeError:
            raise RuntimeError(f"关联的日程不存在 id={schedule_id}")
        rid = self._next_reminder_id
        self._next_reminder_id += 1
        self._reminders.append({
            "id": rid,
            "schedule_id": schedule_id,
            "advance_minutes": int(advance_minutes),
            "custom_message": custom_message or "",
            "is_active": 1,
        })
        return {"id": rid}

    def delete_reminder(self, reminder_id: int) -> None:
        for r in self._reminders:
            if r["id"] == reminder_id:
                self._reminders.remove(r)
                return
        raise RuntimeError(f"提醒不存在 id={reminder_id}")

    def health_check(self) -> dict:
        return {"version": "mock"}

    # ===== 上传/导入（Mock：按文本行生成简单预览）=====

    def _mock_preview(self, text: str) -> dict:
        import re

        preview = []
        pattern = re.compile(
            r"([\u4e00-\u9fa5]{2,4})\s+(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+(\d{1,2}:\d{2})\s*[-~至到]\s*(\d{1,2}:\d{2})\s*(.*)"
        )
        for line in text.splitlines():
            m = pattern.match(line.strip())
            if not m:
                continue
            preview.append({
                "id": None, "name": m.group(1),
                "duty_date": m.group(2), "start_time": m.group(3),
                "end_time": m.group(4), "location": m.group(5).strip(),
                "remark": "", "is_confirmed": False,
                "missing_fields": [],
            })
        return {"schedules": preview, "questions": [], "total": len(preview)}

    def upload_file(self, filepath: str, dry_run: bool = True) -> dict:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return self._mock_preview(f.read())

    def upload_text(self, text: str, dry_run: bool = True) -> dict:
        return self._mock_preview(text)

    def apply_schedules(self, schedules: list, source_type: str = "upload", original_text: str = "") -> dict:
        applied = []
        for s in schedules:
            result = self.create_schedule(s)
            applied.append(dict(s, id=result["id"]))
        return {"schedules": applied, "questions": [], "total": len(applied)}

    def parse_intent(self, text: str) -> dict:
        # Mock 模式：复用后端解析逻辑，但候选匹配基于内存数据
        from backend.core.ai_intent import _normalize_preview, parse_intent
        intent = parse_intent(text)
        action = intent.get("action") or "create"
        if action == "create":
            previews = [_normalize_preview(s) for s in (intent.get("schedules") or [])]
            return {"action": action, "previews": previews, "candidates": [], "ambiguous": False,
                    "msg": f"准备创建 {len(previews)} 条日程" if previews else "未识别出要创建的日程信息，请说得更具体些"}
        match = intent.get("match") or {}
        candidates = [r for r in self._rows if self._match_row(r, match)]
        if not candidates:
            return {"action": action, "previews": [], "candidates": [], "ambiguous": False,
                    "msg": "没有找到匹配的日程，请补充姓名、日期或时间" if match else "未识别出要操作的日程"}
        return {"action": action, "previews": [], "candidates": candidates,
                "fields": intent.get("fields") or {},
                "ambiguous": len(candidates) > 1,
                "msg": f"找到 {len(candidates)} 条匹配日程"}

    @staticmethod
    def _match_row(row: dict, match: dict) -> bool:
        name = (match.get("name") or "").strip()
        if name and name not in (row.get("name") or ""):
            return False
        duty = (match.get("duty_date") or "").strip()
        if duty and row.get("duty_date") != format_date(duty):
            return False
        time = (match.get("start_time") or "").strip()
        if time and ":" in time and not (row.get("start_time") or "").startswith(time.split(":")[0]):
            return False
        return True
