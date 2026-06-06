"""
Система топа — рейтинг игроков и кланов.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils import format_amount
import utils

router = Router()

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

HIDDEN_CLAN_IDS = {1}

# ─── Категории игроков ────────────────────────────────────────────────────────
CATS = {
    "balance": {
        "label":  "💰 Баланс",
        "title":  "💰 ТОП 10 — БАЛАНС (КОШЕЛЁК)",
        "getter": lambda u: u.get("balance", 0),
        "fmt":    lambda v: f"{format_amount(int(v))}$",
    },
    "bank": {
        "label":  "🏦 Банк",
        "title":  "🏦 ТОП 10 — БАНКОВСКИЙ СЧЁТ",
        "getter": lambda u: u.get("user_bank", 0),
        "fmt":    lambda v: f"{format_amount(int(v))}$",
    },
    "total": {
        "label":  "💎 Всего",
        "title":  "💎 ТОП 10 — ОБЩЕЕ СОСТОЯНИЕ (баланс+банк)",
        "getter": lambda u: u.get("balance", 0) + u.get("user_bank", 0),
        "fmt":    lambda v: f"{format_amount(int(v))}$",
    },
    "level": {
        "label":  "📈 Уровень",
        "title":  "📈 ТОП 10 — УРОВЕНЬ",
        "getter": lambda u: u.get("level", 1),
        "fmt":    lambda v: f"Ур. {int(v)}",
    },
    "btc": {
        "label":  "₿ BTC",
        "title":  "₿ ТОП 10 — BTC КОШЕЛЁК",
        "getter": lambda u: u.get("farm", {}).get("btc_balance", 0.0),
        "fmt":    lambda v: f"{v:.4f} BTC".rstrip("0").rstrip(".") + " BTC",
    },
    "dc": {
        "label":  "💎 DC",
        "title":  "💎 ТОП 10 — ДОНАТ МОНЕТЫ (DC)",
        "getter": lambda u: u.get("donate_coins", 0),
        "fmt":    lambda v: f"{int(v)} DC",
    },
}

CAT_ORDER = ["balance", "bank", "total", "level", "btc", "dc"]


# ─── Вспомогательные (игроки) ─────────────────────────────────────────────────

def _is_real_player(u: dict, val) -> bool:
    if val == 0:
        return False
    has_name = u.get("name", "Игрок") not in ("Игрок", "", None)
    has_progress = (
        u.get("balance", 0) > 0
        or u.get("user_bank", 0) > 0
        or u.get("level", 1) > 1
        or u.get("farm", {}).get("btc_balance", 0.0) > 0
        or u.get("donate_coins", 0) > 0
    )
    return has_name or has_progress


def _get_top(cat_key: str, limit: int = 10) -> list[tuple]:
    cat    = CATS[cat_key]
    getter = cat["getter"]
    rows   = []
    for uid, u in utils.user_data.items():
        val  = getter(u)
        if not _is_real_player(u, val):
            continue
        name = u.get("name", "Игрок")
        rows.append((uid, name, val))
    rows.sort(key=lambda x: x[2], reverse=True)
    return rows[:limit]


def _caller_rank(caller_id: int, cat_key: str) -> int | None:
    cat    = CATS[cat_key]
    getter = cat["getter"]
    rows   = []
    for uid, u in utils.user_data.items():
        val = getter(u)
        if not _is_real_player(u, val):
            continue
        rows.append((uid, u))
    rows.sort(key=lambda kv: getter(kv[1]), reverse=True)
    for i, (uid, _) in enumerate(rows, 1):
        if str(uid) == str(caller_id):
            return i
    return None


def _build_text(cat_key: str, caller_id: int = None) -> str:
    cat   = CATS[cat_key]
    rows  = _get_top(cat_key)
    lines = [f"<b>{cat['title']}</b>", "━━━━━━━━━━━━━━━━━━━━", ""]

    for i, (uid, name, val) in enumerate(rows, 1):
        medal  = MEDALS.get(i, f"{i}.")
        vfmt   = cat["fmt"](val)
        lines.append(f"{medal} <b>{name}</b>  —  {vfmt}")

    if caller_id:
        rank = _caller_rank(caller_id, cat_key)
        lines += ["", "━━━━━━━━━━━━━━━━━━━━"]
        if rank and rank <= 10:
            lines.append(f"🎯 Ваше место: <b>#{rank}</b>  🏆")
        elif rank:
            lines.append(f"🎯 Ваше место: <b>#{rank}</b>")
        else:
            lines.append("🎯 Вы не в рейтинге")

    return "\n".join(lines)


# ─── Клановый топ ─────────────────────────────────────────────────────────────

CLAN_CATS = {
    "clan_rating": {
        "label": "🏆 Рейтинг",
        "title": "🏆 ТОП 10 КЛАНОВ — РЕЙТИНГ СЕЗОНА",
        "getter": lambda c: c.get("season_points", 0) + c.get("rating", 0),
        "fmt":    lambda v: f"{int(v)} очк.",
    },
    "clan_treasury": {
        "label": "💰 Казна",
        "title": "💰 ТОП 10 КЛАНОВ — КАЗНА",
        "getter": lambda c: c.get("treasury", 0),
        "fmt":    lambda v: f"{format_amount(int(v))}$",
    },
    "clan_members": {
        "label": "👥 Участники",
        "title": "👥 ТОП 10 КЛАНОВ — КОЛИЧЕСТВО УЧАСТНИКОВ",
        "getter": lambda c: len(c.get("members", [])),
        "fmt":    lambda v: f"{int(v)} чел.",
    },
    "clan_level": {
        "label": "⭐ Уровень",
        "title": "⭐ ТОП 10 КЛАНОВ — УРОВЕНЬ",
        "getter": lambda c: c.get("level", 1),
        "fmt":    lambda v: f"Ур. {int(v)}",
    },
}

CLAN_CAT_ORDER = ["clan_rating", "clan_treasury", "clan_members", "clan_level"]


def _get_clan_top(clan_cat_key: str, limit: int = 10) -> list[tuple]:
    try:
        from clans import clans_data
    except Exception:
        return []
    cat    = CLAN_CATS[clan_cat_key]
    getter = cat["getter"]
    rows   = []
    for cid, clan in clans_data.items():
        if int(cid) in HIDDEN_CLAN_IDS:
            continue
        val  = getter(clan)
        if val == 0:
            continue
        name = clan.get("name", "Клан")
        icon = clan.get("icon", "🛡")
        lvl  = clan.get("level", 1)
        rows.append((cid, name, icon, lvl, val))
    rows.sort(key=lambda x: x[4], reverse=True)
    return rows[:limit]


def _get_user_clan_rank(caller_id: int, clan_cat_key: str) -> tuple[str | None, int | None]:
    try:
        from clans import clans_data, get_user_clan
        clan = get_user_clan(caller_id)
        if not clan:
            return None, None
        cat    = CLAN_CATS[clan_cat_key]
        getter = cat["getter"]
        rows   = []
        for cid, c in clans_data.items():
            if int(cid) in HIDDEN_CLAN_IDS:
                continue
            rows.append((cid, getter(c)))
        rows.sort(key=lambda x: x[1], reverse=True)
        my_name = clan.get("name", "Клан")
        my_val  = getter(clan)
        for i, (cid, val) in enumerate(rows, 1):
            if clans_data.get(cid) is clan:
                return my_name, i
        return my_name, None
    except Exception:
        return None, None


def _build_clan_text(clan_cat_key: str, caller_id: int = None) -> str:
    cat   = CLAN_CATS[clan_cat_key]
    rows  = _get_clan_top(clan_cat_key)
    lines = [f"<b>{cat['title']}</b>", "━━━━━━━━━━━━━━━━━━━━", ""]

    if not rows:
        lines.append("Кланов пока нет.")
    else:
        for i, (cid, name, icon, lvl, val) in enumerate(rows, 1):
            medal = MEDALS.get(i, f"{i}.")
            vfmt  = cat["fmt"](val)
            lines.append(f"{medal} {icon} <b>{name}</b> (ур.{lvl})  —  {vfmt}")

    if caller_id:
        clan_name, rank = _get_user_clan_rank(caller_id, clan_cat_key)
        lines += ["", "━━━━━━━━━━━━━━━━━━━━"]
        if clan_name and rank and rank <= 10:
            lines.append(f"🎯 Ваш клан <b>{clan_name}</b>: <b>#{rank}</b>  🏆")
        elif clan_name and rank:
            lines.append(f"🎯 Ваш клан <b>{clan_name}</b>: <b>#{rank}</b>")
        elif clan_name:
            lines.append(f"🎯 Ваш клан <b>{clan_name}</b> не в рейтинге")
        else:
            lines.append("🎯 Вы не состоите в клане")

    return "\n".join(lines)


# ─── Построение клавиатур ─────────────────────────────────────────────────────

def _build_kb(active: str, mode: str = "player") -> InlineKeyboardMarkup:
    rows = []
    row  = []
    if mode == "player":
        order = CAT_ORDER
        cb_prefix = "top_cat"
        cats_dict = CATS
    else:
        order = CLAN_CAT_ORDER
        cb_prefix = "top_clan_cat"
        cats_dict = CLAN_CATS

    for i, key in enumerate(order):
        label = cats_dict[key]["label"]
        if key == active:
            label = f"› {label} ‹"
        row.append(InlineKeyboardButton(text=label, callback_data=f"{cb_prefix}:{key}"))
        if len(row) == 2 or i == len(order) - 1:
            rows.append(row)
            row = []

    if mode == "player":
        rows.append([InlineKeyboardButton(text="🏰 Топ кланов", callback_data="top_clan_cat:clan_rating")])
    else:
        rows.append([InlineKeyboardButton(text="👤 Топ игроков", callback_data="top_cat:balance")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── Хэндлеры ─────────────────────────────────────────────────────────────────

@router.message(F.text.lower().in_([
    "топ", "/топ", "рейтинг", "/рейтинг", "лидерборд", "top", "/top",
    "топ игроков", "🏆 топ", "📊 рейтинг"
]))
async def cmd_top(message: Message):
    cat_key = "balance"
    text    = _build_text(cat_key, message.from_user.id)
    kb      = _build_kb(cat_key, "player")
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.text.lower().in_(["топ кланов", "клан топ", "рейтинг кланов"]))
async def cmd_clan_top(message: Message):
    clan_cat_key = "clan_rating"
    text = _build_clan_text(clan_cat_key, message.from_user.id)
    kb   = _build_kb(clan_cat_key, "clan")
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("top_cat:"))
async def cb_top_cat(callback: CallbackQuery):
    cat_key = callback.data.split(":")[1]
    if cat_key not in CATS:
        await callback.answer("Категория не найдена.")
        return
    text = _build_text(cat_key, callback.from_user.id)
    kb   = _build_kb(cat_key, "player")
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("top_clan_cat:"))
async def cb_top_clan_cat(callback: CallbackQuery):
    clan_cat_key = callback.data.split(":")[1]
    if clan_cat_key not in CLAN_CATS:
        await callback.answer("Категория не найдена.")
        return
    text = _build_clan_text(clan_cat_key, callback.from_user.id)
    kb   = _build_kb(clan_cat_key, "clan")
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()
