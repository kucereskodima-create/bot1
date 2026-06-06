import os
import json
import time
from datetime import datetime, date

ADMIN_LIMITS_FILE = os.path.join(os.path.dirname(__file__), "admin_limits.json")

founders       = [int(x) for x in os.environ.get("BOT_FOUNDERS",    "0").split(",") if x.strip().isdigit()]
zam_ld_list    = [int(x) for x in os.environ.get("BOT_ZAM_LD",      "0").split(",") if x.strip().isdigit()]
tech_admins    = [int(x) for x in os.environ.get("BOT_TECH_ADMINS", "0").split(",") if x.strip().isdigit()]
admins_list    = [int(x) for x in os.environ.get("BOT_ADMINS",      "0").split(",") if x.strip().isdigit()]
designers_list = [int(x) for x in os.environ.get("BOT_DESIGNERS",   "0").split(",") if x.strip().isdigit()]
moders_list    = [int(x) for x in os.environ.get("BOT_MODERS",      "0").split(",") if x.strip().isdigit()]
followers_list = [int(x) for x in os.environ.get("BOT_FOLLOWERS",   "0").split(",") if x.strip().isdigit()]

ROLE_FOUNDER    = "founder"
ROLE_ZAM_LD     = "zam_ld"
ROLE_TECH_ADMIN = "tech_admin"
ROLE_ADMIN      = "admin"
ROLE_DESIGNER   = "designer"
ROLE_MODER      = "moder"
ROLE_FOLLOWER   = "follower"

ROLE_LABELS = {
    ROLE_FOUNDER:    "👑 Основатель",
    ROLE_ZAM_LD:     "⭐ Зам",
    ROLE_TECH_ADMIN: "🔧 Тех Админ",
    ROLE_ADMIN:      "👮 Админ",
    ROLE_DESIGNER:   "🎨 Дизайнер",
    ROLE_MODER:      "🛡 Модер",
    ROLE_FOLLOWER:   "👁 Фолер",
}

DAILY_LIMITS = {
    ROLE_FOUNDER:    {"currency": None,       "promos": None, "items": None, "ban_days": None},
    ROLE_ZAM_LD:     {"currency": None,       "promos": None, "items": None, "ban_days": None},
    ROLE_TECH_ADMIN: {"currency": None,       "promos": None, "items": None, "ban_days": None},
    ROLE_ADMIN:      {"currency": 200_000_000,"promos": None, "items": None, "ban_days": 30},
    ROLE_DESIGNER:   {"currency": None,       "promos": None, "items": None, "ban_days": None},
    ROLE_MODER:      {"currency": None,       "promos": None, "items": None, "ban_days": 7},
    ROLE_FOLLOWER:   {"currency": None,       "promos": None, "items": None, "ban_days": None},
}

_dynamic_roles: dict = {}
_revoked_ids:   set  = set()


def _load_dynamic():
    global _dynamic_roles, _revoked_ids
    if os.path.exists(ADMIN_LIMITS_FILE):
        try:
            with open(ADMIN_LIMITS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _dynamic_roles = data.get("dynamic_roles", {})
                _revoked_ids   = set(str(x) for x in data.get("revoked_ids", []))
        except Exception:
            _dynamic_roles = {}
            _revoked_ids   = set()


def _save_dynamic():
    data = {}
    if os.path.exists(ADMIN_LIMITS_FILE):
        try:
            with open(ADMIN_LIMITS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    data["dynamic_roles"] = _dynamic_roles
    data["revoked_ids"]   = list(_revoked_ids)
    with open(ADMIN_LIMITS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


_load_dynamic()


def get_role(user_id: int) -> str | None:
    uid = str(user_id)
    # Динамическая роль (выданная через бот) всегда приоритетнее env-var
    if uid in _dynamic_roles:
        return _dynamic_roles[uid]
    # Founders не снимаются
    if user_id in founders:
        return ROLE_FOUNDER
    # Остальные env-var роли блокируются если в revoked_ids
    if uid in _revoked_ids:
        return None
    if user_id in zam_ld_list:
        return ROLE_ZAM_LD
    if user_id in tech_admins:
        return ROLE_TECH_ADMIN
    if user_id in admins_list:
        return ROLE_ADMIN
    if user_id in designers_list:
        return ROLE_DESIGNER
    if user_id in moders_list:
        return ROLE_MODER
    if user_id in followers_list:
        return ROLE_FOLLOWER
    return None


def is_admin_any(user_id: int) -> bool:
    return get_role(user_id) is not None


def has_permission(user_id: int, perm: str) -> bool:
    role = get_role(user_id)
    if role is None:
        return False
    perms = PERMISSIONS.get(role, set())
    return perm in perms


def grant_role(user_id: int, role: str) -> bool:
    if role not in (ROLE_ADMIN, ROLE_TECH_ADMIN, ROLE_ZAM_LD, ROLE_DESIGNER, ROLE_MODER, ROLE_FOUNDER, ROLE_FOLLOWER):
        return False
    uid = str(user_id)
    _dynamic_roles[uid] = role
    _revoked_ids.discard(uid)
    _save_dynamic()
    return True


def revoke_role(user_id: int) -> bool:
    uid = str(user_id)
    changed = False
    if uid in _dynamic_roles:
        del _dynamic_roles[uid]
        changed = True
    # Если пользователь прописан в env-var (зам/тех/etc) — добавляем в revoked
    env_roles = [zam_ld_list, tech_admins, admins_list, designers_list, moders_list]
    if any(user_id in lst for lst in env_roles):
        _revoked_ids.add(uid)
        changed = True
    if changed:
        _save_dynamic()
    return changed


def get_all_dynamic_roles() -> dict:
    return dict(_dynamic_roles)


PERMISSIONS = {
    ROLE_FOUNDER: {
        "give_currency", "reset_user", "set_data", "info",
        "manage_roles", "eco_panel", "view_logs", "system_control",
        "api_keys", "ban", "mute", "delete_account", "view_db",
        "change_limits", "full_system", "create_promo", "manage_shop",
        "restart_bot", "manage_modules", "check_staff", "view_all",
        "give_zam_ld", "give_founder",
        "warp", "view_complaints", "view_reports", "bot_settings",
        "clear_db", "manage_designer", "manage_moder",
    },
    ROLE_ZAM_LD: {
        "give_currency", "info", "eco_panel", "view_logs",
        "ban", "mute", "create_promo", "manage_shop",
        "restart_bot", "manage_modules", "check_staff",
        "give_admin", "revoke_admin", "set_data", "reset_user",
        "give_zam_ld", "warp", "view_complaints", "view_reports",
        "manage_moder", "manage_designer",
    },
    ROLE_TECH_ADMIN: {
        "info", "view_logs", "system_control", "view_db",
        "antispam_config", "block_suspicious", "give_currency",
        "view_reports", "bot_settings",
    },
    ROLE_ADMIN: {
        "give_currency", "ban", "mute", "create_promo",
        "info", "give_items", "create_event", "check_reports",
        "manage_tickets", "warp", "view_complaints", "view_reports",
    },
    ROLE_DESIGNER: {
        "edit_texts", "edit_emoji", "edit_buttons", "view_interface",
        "info", "view_reports",
    },
    ROLE_MODER: {
        "mute", "warn", "check_reports", "manage_tickets",
        "info", "view_complaints", "view_reports", "answer_complaints",
    },
    ROLE_FOLLOWER: {
        "info", "view_reports",
    },
}


def _today_key():
    return date.today().isoformat()


def _load_usage() -> dict:
    if os.path.exists(ADMIN_LIMITS_FILE):
        try:
            with open(ADMIN_LIMITS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("usage", {})
        except Exception:
            pass
    return {}


def _save_usage(usage: dict):
    data = {}
    if os.path.exists(ADMIN_LIMITS_FILE):
        try:
            with open(ADMIN_LIMITS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    data["usage"] = usage
    with open(ADMIN_LIMITS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def check_and_use_limit(user_id: int, limit_type: str, amount: int = 1) -> tuple[bool, int]:
    role = get_role(user_id)
    if role is None:
        return False, 0
    limit = DAILY_LIMITS.get(role, {}).get(limit_type)
    if limit is None:
        return True, 0

    usage = _load_usage()
    today = _today_key()
    uid = str(user_id)
    day_usage = usage.get(today, {}).get(uid, {})
    current = day_usage.get(limit_type, 0)

    remaining = limit - current
    if remaining < amount:
        return False, remaining

    if today not in usage:
        usage[today] = {}
    if uid not in usage[today]:
        usage[today][uid] = {}
    usage[today][uid][limit_type] = current + amount

    old_days = [d for d in usage if d != today]
    for d in old_days:
        del usage[d]

    _save_usage(usage)
    return True, remaining - amount


def get_remaining_limit(user_id: int, limit_type: str) -> int | None:
    role = get_role(user_id)
    if role is None:
        return 0
    limit = DAILY_LIMITS.get(role, {}).get(limit_type)
    if limit is None:
        return None

    usage = _load_usage()
    today = _today_key()
    uid = str(user_id)
    current = usage.get(today, {}).get(uid, {}).get(limit_type, 0)
    return limit - current
