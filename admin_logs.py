import os
import json
import time
from datetime import datetime

LOGS_FILE = os.path.join(os.path.dirname(__file__), "admin_action_logs.json")
MAX_LOGS = 500


def _load_logs() -> list:
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_logs(logs: list):
    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs[-MAX_LOGS:], f, ensure_ascii=False, indent=2)


def log_action(admin_id: int, admin_name: str, action: str, target_id: int = None, details: str = ""):
    logs = _load_logs()
    entry = {
        "ts": time.time(),
        "dt": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "admin_id": admin_id,
        "admin_name": admin_name,
        "action": action,
        "target_id": target_id,
        "details": details,
    }
    logs.append(entry)
    _save_logs(logs)


def get_logs(limit: int = 50, admin_id: int = None, action: str = None) -> list:
    logs = _load_logs()
    if admin_id:
        logs = [l for l in logs if l.get("admin_id") == admin_id]
    if action:
        logs = [l for l in logs if l.get("action") == action]
    return list(reversed(logs))[:limit]


def format_logs(logs: list) -> str:
    if not logs:
        return "📭 Логов нет."
    lines = []
    for e in logs:
        line = (
            f"🕐 <b>{e['dt']}</b>\n"
            f"👤 {e['admin_name']} (<code>{e['admin_id']}</code>)\n"
            f"⚡ {e['action']}"
        )
        if e.get("target_id"):
            line += f" → <code>{e['target_id']}</code>"
        if e.get("details"):
            line += f"\n📝 {e['details']}"
        lines.append(line)
    return "\n\n".join(lines)
