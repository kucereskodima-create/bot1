import json
import os
import re
import time
import uuid
import random
import asyncio
from datetime import datetime, timezone, timedelta
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import utils
from utils import parse_k

router = Router()

# ═══════════════════════════════════════════════════════════════
#  КОНСТАНТЫ
# ═══════════════════════════════════════════════════════════════

CLAN_CREATE_COST   = 500_000
CLAN_TRANSFER_COST = 500_000_000
MAX_CLAN_MEMBERS   = 30
MAX_CLAN_NAME_LEN  = 24
MAX_CLAN_LEVEL     = 25
MAX_LOGS           = 150
RAID_COOLDOWN_SEC  = 3_600
RAID_JOIN_SEC      = 9_000   # 2ч 30мин — окно вступления
RAID_ACTIVE_SEC    = 5_400   # 1ч 30мин — активная фаза рейда

SEASON_REWARDS = {1: 10_000_000, 2: 7_500_000, 3: 5_000_000, 4: 2_500_000, 5: 1_000_000}
SEASON_POINTS  = {"raid_win": 25, "raid_loss": -10, "upgrade": 5, "new_member": 2}

ROLE_NAMES = {
    "owner":   "👑 Владелец",
    "deputy":  "⭐ Заместитель",
    "officer": "🛡 Офицер",
    "member":  "👤 Участник",
}
ROLE_ORDER = {"owner": 0, "deputy": 1, "officer": 2, "member": 3}

CLAN_ICONS = [
    "🛡", "⚔️", "🔱", "🏴", "💀",
    "🐉", "🦅", "🌑", "⚡", "🔥",
    "❄️", "🌊", "🌪", "🏹", "🦁",
]

RESOURCE_NAMES  = {"iron": "⛏ Железо", "diamonds": "💎 Алмазы", "gold": "🥇 Золото", "coal": "🪨 Уголь"}
RESOURCE_ORDER  = ["iron", "diamonds", "gold", "coal"]
BASE_PRICES     = {"iron": 500, "diamonds": 8_000, "gold": 3_000, "coal": 150}

# ═══════════════════════════════════════════════════════════════
#  ТАБЛИЦА УРОВНЕЙ КЛАНА (1–25)
# ═══════════════════════════════════════════════════════════════

def _build_levels() -> dict:
    levels = {}
    for i in range(1, MAX_CLAN_LEVEL + 1):
        cost = 0 if i == 1 else int(1_000_000 * (1.6 ** (i - 2)))
        wh_cap = 10_000 + (i - 1) * 20_000
        k = 1.0 + (i - 1) * 0.16
        levels[i] = {
            "upgrade_cost": cost,
            "warehouse_cap": wh_cap,
            "mine_rate": {
                "iron":     int(120 * k),
                "diamonds": int(6   * k),
                "gold":     int(25  * k),
                "coal":     int(250 * k),
            },
            "raid_bonus": round(1.0 + (i - 1) * 0.04, 2),
            "mine_bonus_pct": (i - 1) * 10,
        }
    return levels

CLAN_LEVELS = _build_levels()

# ═══════════════════════════════════════════════════════════════
#  ФАЙЛЫ И ХРАНИЛИЩЕ ДАННЫХ
# ═══════════════════════════════════════════════════════════════

CLANS_FILE = os.path.join(os.path.dirname(__file__), "clans.json")
clans_data: dict = {}
active_raids: dict = {}   # clan_id → raid_info


def load_clans():
    global clans_data
    if os.path.exists(CLANS_FILE):
        try:
            with open(CLANS_FILE, "r", encoding="utf-8") as f:
                clans_data = json.load(f)
        except Exception:
            clans_data = {}
    else:
        clans_data = {}
    _migrate_clans()


def save_clans():
    try:
        with open(CLANS_FILE, "w", encoding="utf-8") as f:
            json.dump(clans_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[КЛАНЫ] Ошибка сохранения: {e}")


def _migrate_clans():
    now = int(time.time())
    for clan in list(clans_data.values()):
        if isinstance(clan, dict) and "id" in clan:
            clan.setdefault("level", 1)
            clan.setdefault("rating", 0)
            clan.setdefault("season_points", 0)
            clan.setdefault("wins", 0)
            clan.setdefault("losses", 0)
            clan.setdefault("raid_cooldown", 0)
            clan.setdefault("logs", [])
            clan.setdefault("treasury", 0)
            clan.setdefault("bound_chat_id", None)
            if "warehouse" not in clan:
                clan["warehouse"] = {r: 0 for r in RESOURCE_ORDER}
                clan["warehouse"]["last_mine"] = now
            else:
                for r in RESOURCE_ORDER:
                    clan["warehouse"].setdefault(r, 0)
                clan["warehouse"].setdefault("last_mine", now)
            # Миграция ролей: watcher → officer
            for uid, role in list(clan.get("members", {}).items()):
                if role == "watcher":
                    clan["members"][uid] = "officer"

    # Инициализация сезона
    if "_season" not in clans_data:
        clans_data["_season"] = _new_season_data()
        save_clans()

    # Инициализация рыночных цен
    if "_market" not in clans_data:
        clans_data["_market"] = _new_market_data()
        save_clans()


def _new_season_data() -> dict:
    now_dt = datetime.now(timezone.utc)
    # Начало следующего понедельника 00:00 UTC
    days_until_monday = (7 - now_dt.weekday()) % 7 or 7
    next_monday = (now_dt + timedelta(days=days_until_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start_ts = int(now_dt.timestamp())
    end_ts   = int(next_monday.timestamp())
    number   = clans_data.get("_season", {}).get("number", 0) + 1
    return {"number": number, "start_ts": start_ts, "end_ts": end_ts}


def _new_market_data() -> dict:
    prices = {}
    for r, base in BASE_PRICES.items():
        prices[r] = int(base * random.uniform(0.8, 1.2))
    prices["last_update"] = int(time.time())
    return prices


load_clans()

# ═══════════════════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════

def _fmt(n: float) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f} млрд"
    if n >= 1_000_000:
        v = n / 1_000_000
        return f"{v:.1f} млн" if v < 100 else f"{int(v)} млн"
    if n >= 1_000:
        v = n / 1_000
        return f"{v:.1f} тыс" if v < 100 else f"{int(v)} тыс"
    return f"{int(n):,}".replace(",", ".")


def _fmtint(n: float) -> str:
    return f"{int(n):,}".replace(",", ".")


def get_user_clan(user_id: int) -> dict | None:
    uid = str(user_id)
    for cid, clan in clans_data.items():
        if isinstance(clan, dict) and uid in clan.get("members", {}):
            return clan
    return None


def _next_num_id() -> int:
    used = {c.get("num_id", 0) for cid, c in clans_data.items() if isinstance(c, dict) and "id" in c}
    i = 1
    while i in used:
        i += 1
    return i


def _clan_rank(clan: dict) -> int:
    sorted_clans = sorted(
        [c for c in clans_data.values() if isinstance(c, dict) and "id" in c],
        key=lambda x: x.get("rating", 0), reverse=True
    )
    for i, c in enumerate(sorted_clans, 1):
        if c["id"] == clan["id"]:
            return i
    return 0


def _add_log(clan: dict, text: str):
    ts = datetime.now().strftime("%d.%m %H:%M")
    clan.setdefault("logs", []).insert(0, f"[{ts}] {text}")
    if len(clan["logs"]) > MAX_LOGS:
        clan["logs"] = clan["logs"][:MAX_LOGS]


def _can(role: str, action: str) -> bool:
    perms = {
        "owner":   {"all"},
        "deputy":  {"invite", "sell_ore", "start_raid", "view"},
        "officer": {"sell_ore", "join_raid", "view"},
        "member":  {"join_raid", "view"},
    }
    p = perms.get(role, {"view"})
    return "all" in p or action in p


def _get_role(clan: dict, user_id: int) -> str:
    return clan.get("members", {}).get(str(user_id), "member")


def _market_prices() -> dict:
    m = clans_data.get("_market", {})
    if not m:
        clans_data["_market"] = _new_market_data()
        return clans_data["_market"]
    return m


def _season() -> dict:
    s = clans_data.get("_season", {})
    if not s:
        clans_data["_season"] = _new_season_data()
        return clans_data["_season"]
    return s


def _season_time_left() -> str:
    s = _season()
    left = max(0, s.get("end_ts", 0) - int(time.time()))
    if left <= 0:
        return "завершается..."
    days    = left // 86400
    hours   = (left % 86400) // 3600
    minutes = (left % 3600)  // 60
    if days > 0:
        return f"{days}д {hours}ч {minutes}мин"
    if hours > 0:
        return f"{hours}ч {minutes}мин"
    return f"{minutes}мин"


# ═══════════════════════════════════════════════════════════════
#  FSM СОСТОЯНИЯ
# ═══════════════════════════════════════════════════════════════

class ClanCreateState(StatesGroup):
    waiting_icon    = State()

class ClanJoinState(StatesGroup):
    waiting_name    = State()

class ClanTransferState(StatesGroup):
    waiting_target  = State()
    waiting_confirm = State()

class TreasuryDepositState(StatesGroup):
    waiting_amount  = State()

class ClanRenameState(StatesGroup):
    waiting_name    = State()

class ClanIconChangeState(StatesGroup):
    waiting_icon    = State()


# ═══════════════════════════════════════════════════════════════
#  КЛАВИАТУРЫ
# ═══════════════════════════════════════════════════════════════

def _icon_kb() -> InlineKeyboardMarkup:
    rows, row = [], []
    for icon in CLAN_ICONS:
        row.append(InlineKeyboardButton(text=icon, callback_data=f"clan_icon:{icon}"))
        if len(row) == 5:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="clan_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _icon_change_kb(clan_id: str) -> InlineKeyboardMarkup:
    rows, row = [], []
    for icon in CLAN_ICONS:
        row.append(InlineKeyboardButton(text=icon, callback_data=f"clan_icon_pick:{clan_id}:{icon}"))
        if len(row) == 5:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data=f"cl_manage:{clan_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _clan_main_kb(clan_id: str, is_owner: bool = False, user_role: str = "member") -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="👥 Участники",    callback_data=f"cl_members:{clan_id}"),
            InlineKeyboardButton(text="🏛 Система",      callback_data=f"cl_system:{clan_id}"),
        ],
        [
            InlineKeyboardButton(text="🏆 Топ кланов",   callback_data=f"cl_top:rating:0:{clan_id}"),
            InlineKeyboardButton(text="🎖 Сезон",        callback_data=f"cl_season:{clan_id}"),
        ],
    ]
    if user_role in ("owner", "deputy"):
        rows.insert(2, [
            InlineKeyboardButton(text="📝 Логи",         callback_data=f"cl_logs:{clan_id}"),
        ])
    if user_role != "owner":
        rows.append([
            InlineKeyboardButton(text="🚪 Покинуть клан", callback_data=f"cl_leave_ask:{clan_id}"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _no_clan_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список кланов", callback_data="clan_list")],
    ])


def _back_kb(clan_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"clan_back:{clan_id}")]
    ])


# ═══════════════════════════════════════════════════════════════
#  ТЕКСТЫ ГЛАВНОГО МЕНЮ
# ═══════════════════════════════════════════════════════════════

def _clan_main_text(clan: dict, user_id: int) -> str:
    members = clan.get("members", {})
    role    = members.get(str(user_id), "member")
    role_lbl = ROLE_NAMES.get(role, "👤 Участник")
    level    = clan.get("level", 1)
    rating   = clan.get("rating", 0)
    treasury = clan.get("treasury", 0)
    wins     = clan.get("wins", 0)
    losses   = clan.get("losses", 0)
    rank     = _clan_rank(clan)
    num_id   = clan.get("num_id", "?")
    return (
        f"╔══════════════════════════╗\n"
        f"  {clan.get('icon','🛡')}  <b>{clan['name'].upper()}</b>\n"
        f"╚══════════════════════════╝\n\n"
        f"🆔 ID клана: <b>#{num_id}</b>\n"
        f"🎖 Ваша роль: <b>{role_lbl}</b>\n"
        f"👥 Участников: <b>{len(members)}</b> / {MAX_CLAN_MEMBERS}\n"
        f"📈 Уровень: <b>{level}</b> / {MAX_CLAN_LEVEL}\n"
        f"⭐ Рейтинг: <b>{_fmt(rating)}</b>  •  🌍 Место: <b>#{rank}</b>\n"
        f"💰 Казна: <b>{_fmt(treasury)}$</b>\n"
        f"⚔ Победы: <b>{wins}</b>  •  💀 Поражений: <b>{losses}</b>\n\n"
        f"<i>Используйте кнопки ниже для управления кланом</i>"
    )


# ═══════════════════════════════════════════════════════════════
#  КОМАНДЫ — ВХОД В МЕНЮ КЛАНА
# ═══════════════════════════════════════════════════════════════

@router.message(F.text.lower().in_([
    "клан", "/клан", "кланы", "/кланы", "clan", "/clan", "мой клан",
]))
async def cmd_clan(message: Message):
    await _show_clan(message, message.from_user.id)


@router.message(F.text.lower().startswith("топ кланов"))
async def cmd_top_clans_msg(message: Message):
    await _show_top(message, "rating", 0, send_new=True)


@router.message(F.text.lower().in_(["сезон", "/сезон"]))
async def cmd_season_msg(message: Message):
    clan = get_user_clan(message.from_user.id)
    clan_id = clan["id"] if clan else ""
    text = _season_text(clan)
    await message.answer(text, parse_mode="HTML", reply_markup=_season_kb(clan_id))


async def _show_clan(message: Message, user_id: int):
    clan = get_user_clan(user_id)
    if clan:
        _flush_mine(clan)
        await message.answer(
            _clan_main_text(clan, user_id),
            parse_mode="HTML",
            reply_markup=_clan_main_kb(clan["id"], user_role=_get_role(clan, user_id))
        )
    else:
        await message.answer(
            "🛡 <b>КЛАНОВАЯ СИСТЕМА</b>\n\n"
            "Вы не состоите ни в одном клане.\n\n"
            "📌 <b>Команды:</b>\n"
            "  • <code>создать клан (ник)</code> — создать клан\n"
            "  • <code>клан вступить (ид)</code> — вступить по ID\n",
            parse_mode="HTML",
            reply_markup=_no_clan_kb()
        )


# ═══════════════════════════════════════════════════════════════
#  СОЗДАНИЕ КЛАНА
# ═══════════════════════════════════════════════════════════════

@router.message(F.text.lower().startswith("создать клан "))
async def cmd_create_clan_shortcut(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if get_user_clan(user_id):
        await message.answer("❌ Вы уже состоите в клане!")
        return
    name = message.text.strip()[len("создать клан "):].strip()
    await _start_clan_creation(message, state, user_id, name)


@router.callback_query(F.data == "clan_create")
async def cb_clan_create(callback: CallbackQuery, state: FSMContext):
    if get_user_clan(callback.from_user.id):
        await callback.answer("❌ Вы уже состоите в клане!", show_alert=True)
        return
    await callback.message.edit_text(
        "➕ <b>СОЗДАНИЕ КЛАНА</b>\n\nВведите название для вашего клана:\n<i>От 2 до 24 символов</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="clan_cancel")]
        ])
    )
    await state.set_state(ClanCreateState.waiting_icon)
    await state.update_data(step="name")
    await callback.answer()


@router.message(ClanCreateState.waiting_icon)
async def msg_clan_create_input(message: Message, state: FSMContext):
    data = await state.get_data()
    step = data.get("step", "name")

    if step == "name":
        name = message.text.strip()
        user_id = message.from_user.id
        if get_user_clan(user_id):
            await state.clear()
            await message.answer("❌ Вы уже состоите в клане!")
            return
        await _start_clan_creation(message, state, user_id, name)


async def _start_clan_creation(message: Message, state: FSMContext, user_id: int, name: str):
    if len(name) < 2 or len(name) > MAX_CLAN_NAME_LEN:
        await message.answer(f"❌ Название клана: от 2 до {MAX_CLAN_NAME_LEN} символов.")
        return
    for c in clans_data.values():
        if isinstance(c, dict) and c.get("name", "").lower() == name.lower():
            await message.answer("❌ Клан с таким названием уже существует.")
            return
    balance = utils.get_balance(user_id)
    if balance < CLAN_CREATE_COST:
        await message.answer(
            f"❌ <b>Недостаточно средств!</b>\n\n"
            f"💰 Стоимость создания: <b>{_fmt(CLAN_CREATE_COST)}$</b>\n"
            f"💼 Ваш баланс: <b>{_fmt(balance)}$</b>\n"
            f"📉 Не хватает: <b>{_fmt(CLAN_CREATE_COST - balance)}$</b>",
            parse_mode="HTML"
        )
        return
    await state.update_data(clan_name=name, step="icon")
    await state.set_state(ClanCreateState.waiting_icon)
    await message.answer(
        f"❓ Вы уверены, что хотите создать клан «<b>{name}</b>» за <b>{_fmt(CLAN_CREATE_COST)}$</b>?\n\n"
        f"Выберите иконку клана:",
        parse_mode="HTML",
        reply_markup=_icon_kb()
    )


@router.callback_query(ClanCreateState.waiting_icon, F.data.startswith("clan_icon:"))
async def cb_clan_icon(callback: CallbackQuery, state: FSMContext):
    icon    = callback.data.split(":", 1)[1]
    data    = await state.get_data()
    name    = data.get("clan_name", "Клан")
    user_id = callback.from_user.id
    await state.clear()

    if get_user_clan(user_id):
        await callback.answer("❌ Вы уже в клане!", show_alert=True)
        return
    balance = utils.get_balance(user_id)
    if balance < CLAN_CREATE_COST:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return

    utils.update_balance(user_id, balance - CLAN_CREATE_COST)
    clan_id = str(uuid.uuid4())[:8]
    now     = int(time.time())
    clan = {
        "id": clan_id,
        "num_id": _next_num_id(),
        "name": name,
        "icon": icon,
        "owner_id": user_id,
        "members": {str(user_id): "owner"},
        "created_at": now,
        "treasury": 0,
        "level": 1,
        "rating": 0,
        "season_points": 0,
        "wins": 0,
        "losses": 0,
        "raid_cooldown": 0,
        "logs": [],
        "warehouse": {**{r: 0 for r in RESOURCE_ORDER}, "last_mine": now},
        "complex": {
            "level": 1,
            "resources": {r: 0.0 for r in ["diamonds", "gold", "titan", "energycores", "uranium"]},
            "last_update": now,
            "upgrade_fund": 0,
            "investors": {},
        }
    }
    clans_data[clan_id] = clan
    _add_log(clan, f"🎉 Клан основан игроком {utils.get_name(user_id)}")
    save_clans()

    await callback.message.edit_text(
        f"🎉 <b>Клан успешно создан!</b>\n\n"
        f"{icon} <b>{name}</b>\n"
        f"🆔 ID: <b>#{clan['num_id']}</b>\n"
        f"👑 Основатель: <b>{utils.get_name(user_id)}</b>\n"
        f"💸 Списано: <b>{_fmt(CLAN_CREATE_COST)}$</b>\n\n"
        f"Начните развивать клан!",
        parse_mode="HTML",
        reply_markup=_clan_main_kb(clan_id, user_role="owner")
    )
    await callback.answer("✅ Клан создан!")


# ═══════════════════════════════════════════════════════════════
#  ВСТУПЛЕНИЕ В КЛАН
# ═══════════════════════════════════════════════════════════════

@router.message(F.text.lower().startswith("клан вступить "))
async def cmd_join_by_id_clan(message: Message):
    user_id = message.from_user.id
    if get_user_clan(user_id):
        await message.answer("❌ Вы уже состоите в клане!")
        return
    arg = message.text.strip().split(None, 2)[-1].strip()
    if not arg.isdigit():
        await message.answer("❌ Укажите числовой ID клана. Пример: <b>клан вступить 3</b>", parse_mode="HTML")
        return
    num_id = int(arg)
    target = next((c for c in clans_data.values() if isinstance(c, dict) and c.get("num_id") == num_id), None)
    if not target:
        await message.answer(f"❌ Клан <b>#{num_id}</b> не найден.", parse_mode="HTML")
        return
    if len(target.get("members", {})) >= MAX_CLAN_MEMBERS:
        await message.answer("❌ Клан заполнен.")
        return
    target["members"][str(user_id)] = "member"
    _add_log(target, f"➕ Вступил {utils.get_name(user_id)}")
    _add_season_points(target, "new_member")
    save_clans()
    await message.answer(
        f"✅ Вы вступили в клан {target.get('icon','')} <b>{target['name']}</b>!\n🆔 ID: <code>#{num_id}</code>",
        parse_mode="HTML",
        reply_markup=_clan_main_kb(target["id"], user_role="member")
    )


@router.message(F.text.lower().startswith("вступить "))
async def cmd_join_by_id(message: Message):
    user_id = message.from_user.id
    if get_user_clan(user_id):
        await message.answer("❌ Вы уже состоите в клане!")
        return
    arg = message.text.strip().split(None, 1)[1].strip()
    if not arg.isdigit():
        await message.answer("❌ Укажите числовой ID клана. Пример: <b>Вступить 3</b>", parse_mode="HTML")
        return
    num_id = int(arg)
    target = next((c for c in clans_data.values() if isinstance(c, dict) and c.get("num_id") == num_id), None)
    if not target:
        await message.answer(f"❌ Клан <b>#{num_id}</b> не найден.", parse_mode="HTML")
        return
    if len(target.get("members", {})) >= MAX_CLAN_MEMBERS:
        await message.answer("❌ Клан заполнен.")
        return
    target["members"][str(user_id)] = "member"
    _add_log(target, f"➕ Вступил {utils.get_name(user_id)}")
    _add_season_points(target, "new_member")
    save_clans()
    await message.answer(
        f"✅ Вы вступили в клан {target.get('icon','')} <b>{target['name']}</b>!\n🆔 ID: <code>#{num_id}</code>",
        parse_mode="HTML",
        reply_markup=_clan_main_kb(target["id"], user_role="member")
    )


@router.callback_query(F.data == "clan_join")
async def cb_clan_join(callback: CallbackQuery, state: FSMContext):
    if get_user_clan(callback.from_user.id):
        await callback.answer("❌ Вы уже в клане!", show_alert=True)
        return
    await state.set_state(ClanJoinState.waiting_name)
    await callback.message.edit_text(
        "🔍 <b>ВСТУПЛЕНИЕ В КЛАН</b>\n\nВведите ID (#число) или название клана:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="clan_cancel")]
        ])
    )
    await callback.answer()


@router.message(ClanJoinState.waiting_name)
async def msg_clan_join(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text    = message.text.strip()
    target  = None
    for c in clans_data.values():
        if not isinstance(c, dict) or "id" not in c:
            continue
        if c.get("name", "").lower() == text.lower() or str(c.get("num_id", "")) == text.lstrip("#"):
            target = c
            break
    if not target:
        await message.answer("❌ Клан не найден. Введите точное название или ID (#число).")
        return
    if len(target.get("members", {})) >= MAX_CLAN_MEMBERS:
        await message.answer("❌ Клан заполнен.")
        await state.clear()
        return
    await state.clear()
    target["members"][str(user_id)] = "member"
    _add_log(target, f"➕ Вступил {utils.get_name(user_id)}")
    _add_season_points(target, "new_member")
    save_clans()
    await message.answer(
        f"✅ Вы вступили в клан <b>{target.get('icon','')} {target['name']}</b>!",
        parse_mode="HTML",
        reply_markup=_clan_main_kb(target["id"], user_role="member")
    )


# ═══════════════════════════════════════════════════════════════
#  СПИСОК КЛАНОВ
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "clan_list")
async def cb_clan_list(callback: CallbackQuery):
    clans = sorted(
        [c for c in clans_data.values() if isinstance(c, dict) and "id" in c],
        key=lambda x: x.get("rating", 0), reverse=True
    )[:15]
    if not clans:
        await callback.answer("📋 Кланов пока нет.", show_alert=True)
        return
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 12
    lines  = ["📋 <b>СПИСОК КЛАНОВ</b>\n"]
    for i, c in enumerate(clans):
        mc  = len(c.get("members", {}))
        lines.append(
            f"{medals[i]} <code>#{c.get('num_id','?')}</code> {c.get('icon','🛡')} "
            f"<b>{c['name']}</b> — {mc} уч. | ⭐{_fmt(c.get('rating',0))}"
        )
    lines.append("\n<i>Вступить: <b>Вступить (номер)</b></i>")
    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Вступить по названию", callback_data="clan_join")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="clan_no_clan_back")],
        ])
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════
#  НАВИГАЦИЯ — НАЗАД
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "clan_cancel")
async def cb_clan_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    clan = get_user_clan(callback.from_user.id)
    if clan:
        await callback.message.edit_text(
            _clan_main_text(clan, callback.from_user.id), parse_mode="HTML",
            reply_markup=_clan_main_kb(clan["id"], user_role=_get_role(clan, callback.from_user.id))
        )
    else:
        await callback.message.edit_text(
            "🛡 <b>КЛАНОВАЯ СИСТЕМА</b>\n\nВы не состоите ни в одном клане.\n\n"
            "📌 <b>Команды:</b>\n"
            "  • <code>создать клан (ник)</code> — создать клан\n"
            "  • <code>клан вступить (ид)</code> — вступить по ID\n",
            parse_mode="HTML", reply_markup=_no_clan_kb()
        )
    await callback.answer()


@router.callback_query(F.data == "clan_no_clan_back")
async def cb_no_clan_back(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛡 <b>КЛАНОВАЯ СИСТЕМА</b>\n\nВы не состоите ни в одном клане.\n\n"
        "📌 <b>Команды:</b>\n"
        "  • <code>создать клан (ник)</code> — создать клан\n"
        "  • <code>клан вступить (ид)</code> — вступить по ID\n",
        parse_mode="HTML", reply_markup=_no_clan_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("clan_back:"))
async def cb_clan_back(callback: CallbackQuery):
    user_id  = callback.from_user.id
    clan_id  = callback.data.split(":", 1)[1]
    clan     = clans_data.get(clan_id)
    if not clan or str(user_id) not in clan.get("members", {}):
        await callback.answer("❌", show_alert=True)
        return
    _flush_mine(clan)
    await callback.message.edit_text(
        _clan_main_text(clan, user_id), parse_mode="HTML",
        reply_markup=_clan_main_kb(clan_id, user_role=_get_role(clan, user_id))
    )
    await callback.answer()


def _get_clan_member(callback: CallbackQuery, clan_id: str):
    clan = clans_data.get(clan_id)
    if not clan or str(callback.from_user.id) not in clan.get("members", {}):
        return None
    return clan


# ═══════════════════════════════════════════════════════════════
#  ⚙ УПРАВЛЕНИЕ КЛАНОМ
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cl_manage:"))
async def cb_manage(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = _get_clan_member(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    role = clan["members"].get(str(callback.from_user.id))
    if role != "owner":
        await callback.answer("❌ Только владелец может управлять кланом!", show_alert=True)
        return
    await callback.message.edit_text(
        f"⚙ <b>УПРАВЛЕНИЕ КЛАНОМ</b>\n\n"
        f"{clan.get('icon','🛡')} <b>{clan['name']}</b>\n"
        f"👑 Владелец: только вы\n\n"
        f"<i>Здесь вы можете изменить настройки, передать или удалить клан.</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Сменить название",  callback_data=f"clan_rename:{clan_id}")],
            [InlineKeyboardButton(text="🎭 Сменить иконку",    callback_data=f"clan_icon_change:{clan_id}")],
            [InlineKeyboardButton(text="👑 Передать клан",     callback_data=f"clan_transfer:{clan_id}")],
            [InlineKeyboardButton(text="🗑 Удалить клан",      callback_data=f"clan_delete_ask:{clan_id}")],
            [InlineKeyboardButton(text="⬅️ Назад",             callback_data=f"clan_back:{clan_id}")],
        ])
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════
#  ✏️ СМЕНА НАЗВАНИЯ КЛАНА
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("clan_rename:"))
async def cb_clan_rename_start(callback: CallbackQuery, state: FSMContext):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan or clan.get("owner_id") != callback.from_user.id:
        await callback.answer("❌", show_alert=True); return
    await state.set_state(ClanRenameState.waiting_name)
    await state.update_data(rename_clan_id=clan_id)
    await callback.message.edit_text(
        f"✏️ <b>СМЕНА НАЗВАНИЯ КЛАНА</b>\n\n"
        f"Текущее: {clan.get('icon','🛡')} <b>{clan['name']}</b>\n\n"
        f"Введите новое название:\n<i>От 2 до 24 символов</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cl_manage:{clan_id}")]
        ])
    )
    await callback.answer()


@router.message(ClanRenameState.waiting_name)
async def msg_clan_rename(message: Message, state: FSMContext):
    data    = await state.get_data()
    clan_id = data.get("rename_clan_id")
    clan    = clans_data.get(clan_id)
    if not clan or clan.get("owner_id") != message.from_user.id:
        await state.clear()
        return
    name = message.text.strip()
    if len(name) < 2 or len(name) > 24:
        await message.answer("❌ Название должно быть от 2 до 24 символов. Попробуйте ещё раз:")
        return
    old_name = clan["name"]
    clan["name"] = name
    save_clans()
    _add_log(clan, f"✏️ Название изменено: {old_name} → {name}")
    await state.clear()
    await message.answer(
        f"✅ Название клана изменено!\n\n"
        f"{clan.get('icon','🛡')} <b>{name}</b>",
        parse_mode="HTML",
        reply_markup=_clan_main_kb(clan_id, user_role="owner")
    )


# ═══════════════════════════════════════════════════════════════
#  🎭 СМЕНА ИКОНКИ КЛАНА
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("clan_icon_change:"))
async def cb_clan_icon_change_start(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan or clan.get("owner_id") != callback.from_user.id:
        await callback.answer("❌", show_alert=True); return
    await callback.message.edit_text(
        f"🎭 <b>СМЕНА ИКОНКИ КЛАНА</b>\n\n"
        f"Текущая: {clan.get('icon','🛡')} <b>{clan['name']}</b>\n\n"
        f"Выберите новую иконку:",
        parse_mode="HTML",
        reply_markup=_icon_change_kb(clan_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("clan_icon_pick:"))
async def cb_clan_icon_pick(callback: CallbackQuery):
    parts   = callback.data.split(":", 2)
    clan_id = parts[1]
    icon    = parts[2]
    clan    = clans_data.get(clan_id)
    if not clan or clan.get("owner_id") != callback.from_user.id:
        await callback.answer("❌", show_alert=True); return
    old_icon = clan.get("icon", "🛡")
    clan["icon"] = icon
    save_clans()
    _add_log(clan, f"🎭 Иконка изменена: {old_icon} → {icon}")
    await callback.message.edit_text(
        f"✅ Иконка клана изменена!\n\n"
        f"{icon} <b>{clan['name']}</b>",
        parse_mode="HTML",
        reply_markup=_clan_main_kb(clan_id, user_role="owner")
    )
    await callback.answer(f"Иконка изменена на {icon}")


# ═══════════════════════════════════════════════════════════════
#  🗑 УДАЛЕНИЕ КЛАНА
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("clan_delete_ask:"))
async def cb_delete_ask(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan or clan.get("owner_id") != callback.from_user.id:
        await callback.answer("❌", show_alert=True); return
    await callback.message.edit_text(
        f"⚠️ <b>УДАЛЕНИЕ КЛАНА</b>\n\n"
        f"{clan.get('icon','🛡')} <b>{clan['name']}</b>\n\n"
        f"Вы уверены что хотите удалить клан?\n"
        f"<b>Все участники будут исключены. Это действие необратимо!</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить",  callback_data=f"clan_delete_confirm:{clan_id}")],
            [InlineKeyboardButton(text="❌ Нет",           callback_data=f"cl_manage:{clan_id}")],
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("clan_delete_confirm:"))
async def cb_delete_confirm(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan or clan.get("owner_id") != callback.from_user.id:
        await callback.answer("❌", show_alert=True); return
    name = clan["name"]
    icon = clan.get("icon", "🛡")
    del clans_data[clan_id]
    save_clans()
    await callback.message.edit_text(
        f"🗑 Клан {icon} <b>{name}</b> был удалён.\n"
        f"🆔 ID #{clan.get('num_id','?')} освобождён.",
        parse_mode="HTML",
        reply_markup=_no_clan_kb()
    )
    await callback.answer("Клан удалён")


# ═══════════════════════════════════════════════════════════════
#  👑 ПЕРЕДАЧА КЛАНА
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("clan_transfer:"))
async def cb_transfer_start(callback: CallbackQuery, state: FSMContext):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan or clan.get("owner_id") != callback.from_user.id:
        await callback.answer("❌ Только владелец!", show_alert=True); return
    balance = utils.get_balance(callback.from_user.id)
    members = {k: v for k, v in clan.get("members", {}).items() if k != str(callback.from_user.id)}
    if not members:
        await callback.answer("❌ В клане нет других участников!", show_alert=True); return

    lines = [f"👑 <b>ПЕРЕДАЧА КЛАНА</b>\n\n{clan.get('icon','🛡')} <b>{clan['name']}</b>\n\n"
             f"💰 Стоимость: <b>{_fmt(CLAN_TRANSFER_COST)}$</b>\n"
             f"💼 Ваш баланс: <b>{_fmt(balance)}$</b>\n\n"
             f"Введите имя или @юзернейм участника:"]
    await state.set_state(ClanTransferState.waiting_target)
    await state.update_data(clan_id=clan_id)
    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cl_manage:{clan_id}")]
        ])
    )
    await callback.answer()


@router.message(ClanTransferState.waiting_target)
async def msg_transfer_target(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data    = await state.get_data()
    clan_id = data.get("clan_id")
    clan    = clans_data.get(clan_id)
    if not clan:
        await state.clear()
        await message.answer("❌ Клан не найден.")
        return
    text     = message.text.strip().lower()
    members  = clan.get("members", {})
    target_uid, target_name = None, None
    for uid_str in members:
        if uid_str == str(user_id):
            continue
        u = utils.get_user(int(uid_str))
        if not u:
            continue
        name = u.get("name", "")
        tg   = u.get("telegram_username", "")
        if name.lower() == text or (tg and tg.lower().lstrip("@") == text.lstrip("@")):
            target_uid  = int(uid_str)
            target_name = name
            break
    if not target_uid:
        await message.answer("❌ Участник не найден. Введите точное имя.")
        return
    balance = utils.get_balance(user_id)
    if balance < CLAN_TRANSFER_COST:
        await state.clear()
        await message.answer(
            f"❌ Недостаточно средств!\n"
            f"💰 Нужно: <b>{_fmt(CLAN_TRANSFER_COST)}$</b>\n"
            f"💼 Ваш баланс: <b>{_fmt(balance)}$</b>",
            parse_mode="HTML"
        )
        return
    await state.update_data(target_uid=target_uid, target_name=target_name)
    await state.set_state(ClanTransferState.waiting_confirm)
    await message.answer(
        f"⚠️ <b>ПОДТВЕРЖДЕНИЕ ПЕРЕДАЧИ</b>\n\n"
        f"{clan.get('icon','🛡')} <b>{clan['name']}</b>\n\n"
        f"👑 Новый владелец: <b>{target_name}</b>\n"
        f"💸 Будет списано: <b>{_fmt(CLAN_TRANSFER_COST)}$</b>\n\n"
        f"Это действие необратимо!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Передать", callback_data="clan_transfer_do")],
            [InlineKeyboardButton(text="❌ Отмена",   callback_data=f"clan_back:{clan_id}")],
        ])
    )


@router.callback_query(ClanTransferState.waiting_confirm, F.data == "clan_transfer_do")
async def cb_transfer_do(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data    = await state.get_data()
    clan_id     = data.get("clan_id")
    target_uid  = data.get("target_uid")
    target_name = data.get("target_name")
    await state.clear()
    clan = clans_data.get(clan_id)
    if not clan or clan.get("owner_id") != user_id:
        await callback.answer("❌", show_alert=True); return
    if str(target_uid) not in clan.get("members", {}):
        await callback.answer("❌ Участник больше не в клане.", show_alert=True); return
    balance = utils.get_balance(user_id)
    if balance < CLAN_TRANSFER_COST:
        await callback.answer(f"❌ Недостаточно средств! Нужно {_fmt(CLAN_TRANSFER_COST)}$", show_alert=True); return
    utils.update_balance(user_id, balance - CLAN_TRANSFER_COST)
    clan["owner_id"]                  = target_uid
    clan["members"][str(user_id)]     = "deputy"
    clan["members"][str(target_uid)]  = "owner"
    _add_log(clan, f"👑 Клан передан игроку {target_name}")
    save_clans()
    try:
        from config import bot as _bot
        await _bot.send_message(
            target_uid,
            f"👑 Вы стали новым <b>владельцем</b> клана {clan.get('icon','🛡')} <b>{clan['name']}</b>!",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.message.edit_text(
        f"✅ <b>Клан передан!</b>\n\n"
        f"{clan.get('icon','🛡')} <b>{clan['name']}</b>\n"
        f"👑 Новый владелец: <b>{target_name}</b>\n"
        f"💸 Списано: <b>{_fmt(CLAN_TRANSFER_COST)}$</b>",
        parse_mode="HTML",
        reply_markup=_back_kb(clan_id)
    )
    await callback.answer("✅ Клан передан!")


# ═══════════════════════════════════════════════════════════════
#  ⬆ ПРОКАЧКА КЛАНА
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cl_upgrade:"))
async def cb_upgrade(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = _get_clan_member(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    await callback.message.edit_text(
        _upgrade_text(clan), parse_mode="HTML",
        reply_markup=_upgrade_kb(clan_id, clan)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cl_upgrade_do:"))
async def cb_upgrade_do(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    role = clan["members"].get(str(callback.from_user.id))
    if role != "owner":
        await callback.answer("❌ Только владелец может прокачивать клан!", show_alert=True); return
    level = clan.get("level", 1)
    if level >= MAX_CLAN_LEVEL:
        await callback.answer("🏆 Клан уже на максимальном уровне!", show_alert=True); return
    cost = CLAN_LEVELS[level + 1]["upgrade_cost"]
    treasury = clan.get("treasury", 0)
    if treasury < cost:
        await callback.answer(
            f"❌ Недостаточно средств в казне!\nНужно: {_fmt(cost)}$\nВ казне: {_fmt(treasury)}$",
            show_alert=True
        ); return
    clan["treasury"] -= cost
    clan["level"]    += 1
    _add_log(clan, f"⬆ Клан улучшен до уровня {clan['level']}")
    _add_season_points(clan, "upgrade")
    save_clans()
    await callback.message.edit_text(
        f"✅ <b>Клан улучшен до уровня {clan['level']}!</b>\n\n"
        + _upgrade_text(clan),
        parse_mode="HTML",
        reply_markup=_upgrade_kb(clan_id, clan)
    )
    await callback.answer(f"⬆ Уровень {clan['level']}!")


def _upgrade_text(clan: dict) -> str:
    level = clan.get("level", 1)
    treasury = clan.get("treasury", 0)
    if level >= MAX_CLAN_LEVEL:
        info = CLAN_LEVELS[level]
        return (
            f"⬆ <b>ПРОКАЧКА КЛАНА</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📈 Уровень: <b>{level} / {MAX_CLAN_LEVEL}</b>\n\n"
            f"🏆 <b>Клан достиг максимального уровня!</b>\n\n"
            f"📦 Склад: <b>{_fmtint(info['warehouse_cap'])}</b> ед.\n"
            f"⚔ Бонус рейдов: <b>+{int((info['raid_bonus']-1)*100)}%</b>\n"
            f"⛏ Добыча руды: <b>+{info['mine_bonus_pct']}%</b>"
        )
    next_level = level + 1
    cost = CLAN_LEVELS[next_level]["upgrade_cost"]
    cur  = CLAN_LEVELS[level]
    nxt  = CLAN_LEVELS[next_level]
    diff_wh   = nxt["warehouse_cap"] - cur["warehouse_cap"]
    diff_iron = nxt["mine_rate"]["iron"] - cur["mine_rate"]["iron"]
    diff_raid = round((nxt["raid_bonus"] - cur["raid_bonus"]) * 100, 1)
    return (
        f"⬆ <b>ПРОКАЧКА КЛАНА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📈 Уровень: <b>{level}</b> → <b>{next_level}</b>  (макс. {MAX_CLAN_LEVEL})\n"
        f"💰 Стоимость: <b>{_fmt(cost)}$</b>\n"
        f"🏦 Казна: <b>{_fmt(treasury)}$</b>\n\n"
        f"<b>Бонусы после улучшения:</b>\n"
        f"• 📦 Склад: +{_fmtint(diff_wh)} ед.\n"
        f"• ⛏ Добыча железа: +{diff_iron}/час\n"
        f"• ⚔ Бонус рейдов: +{diff_raid}%\n"
        f"• ⛏ Бонус добычи: +10%\n\n"
        f"<i>Оплата производится из казны клана</i>"
    )


def _upgrade_kb(clan_id: str, clan: dict) -> InlineKeyboardMarkup:
    level = clan.get("level", 1)
    rows = []
    if level < MAX_CLAN_LEVEL:
        cost = CLAN_LEVELS[level + 1]["upgrade_cost"]
        rows.append([InlineKeyboardButton(
            text=f"⬆ Улучшить за {_fmt(cost)}$",
            callback_data=f"cl_upgrade_do:{clan_id}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"clan_back:{clan_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ═══════════════════════════════════════════════════════════════
#  📦 СКЛАД РУДЫ
# ═══════════════════════════════════════════════════════════════

def _flush_mine(clan: dict):
    wh    = clan.setdefault("warehouse", {r: 0 for r in RESOURCE_ORDER})
    wh.setdefault("last_mine", int(time.time()))
    for r in RESOURCE_ORDER:
        wh.setdefault(r, 0)
    now   = int(time.time())
    last  = wh.get("last_mine", now)
    hours = (now - last) / 3600.0
    if hours < 0.001:
        return
    level  = clan.get("level", 1)
    rates  = CLAN_LEVELS[level]["mine_rate"]
    cap    = CLAN_LEVELS[level]["warehouse_cap"]
    total  = sum(wh.get(r, 0) for r in RESOURCE_ORDER)
    for r in RESOURCE_ORDER:
        mined   = rates[r] * hours
        space   = max(0, cap - total)
        add     = min(mined, space)
        wh[r]   = wh.get(r, 0) + add
        total  += add
    wh["last_mine"] = now


@router.callback_query(F.data.startswith("cl_warehouse:"))
async def cb_warehouse(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = _get_clan_member(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    _flush_mine(clan)
    save_clans()
    role = _get_role(clan, callback.from_user.id)
    rows = []
    if role in ("owner", "deputy"):
        treasury = clan.get("treasury", 0)
        members  = clan.get("members", {})
        per_person = treasury // len(members) if members else 0
        rows.append([InlineKeyboardButton(
            text=f"🎁 Раздать казну ({_fmt(treasury)}$)" if treasury > 0 else "🎁 Казна пуста",
            callback_data=f"cl_wh_distribute:{clan_id}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"clan_back:{clan_id}")])
    await callback.message.edit_text(
        _warehouse_text(clan), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cl_wh_distribute:"))
async def cb_wh_distribute(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    role = _get_role(clan, callback.from_user.id)
    if role not in ("owner", "deputy"):
        await callback.answer("❌ Только владелец или заместитель!", show_alert=True); return
    treasury = clan.get("treasury", 0)
    members  = clan.get("members", {})
    if treasury <= 0:
        await callback.answer("❌ Казна пуста!", show_alert=True); return
    if not members:
        await callback.answer("❌ Нет участников!", show_alert=True); return
    per_person = treasury // len(members)
    if per_person <= 0:
        await callback.answer("❌ Слишком мало для раздачи!", show_alert=True); return
    for uid_str in members:
        utils.update_balance(int(uid_str), utils.get_balance(int(uid_str)) + per_person)
    clan["treasury"] = 0
    _add_log(clan, f"🎁 Казна раздана со склада: {_fmt(per_person)}$ каждому ({utils.get_name(callback.from_user.id)})")
    save_clans()
    await callback.message.edit_text(
        f"🎁 <b>Казна распределена!</b>\n\n"
        f"👥 Участников: <b>{len(members)}</b>\n"
        f"💰 Каждый получил: <b>{_fmt(per_person)}$</b>\n\n"
        f"📦 <i>Склад обновлён</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Склад", callback_data=f"cl_warehouse:{clan_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"clan_back:{clan_id}")],
        ])
    )
    await callback.answer("✅ Казна роздана!")


def _warehouse_text(clan: dict) -> str:
    wh    = clan.get("warehouse", {})
    level = clan.get("level", 1)
    cap   = CLAN_LEVELS[level]["warehouse_cap"]
    total = sum(wh.get(r, 0) for r in RESOURCE_ORDER)
    pct   = round(total / cap * 100, 1) if cap else 0
    filled = round(pct / 10)
    bar    = "▰" * filled + "▱" * (10 - filled)
    prices = _market_prices()
    lines  = [
        "📦 <b>СКЛАД КЛАНА</b>",
        "━━━━━━━━━━━━━━━━━━━━━━\n",
    ]
    for r in RESOURCE_ORDER:
        amt  = wh.get(r, 0)
        prc  = prices.get(r, BASE_PRICES[r])
        lines.append(f"  {RESOURCE_NAMES[r]}: <b>{_fmtint(amt)}</b> ед. (~{_fmt(amt * prc)}$)")
    bonus = CLAN_LEVELS[level]["mine_bonus_pct"]
    rates = CLAN_LEVELS[level]["mine_rate"]
    lines += [
        f"\n<code>[{bar}]</code>  <b>{pct}%</b>",
        f"📦 Заполнено: <b>{_fmtint(total)} / {_fmtint(cap)}</b>",
        f"⛏ Бонус добычи уровня: <b>+{bonus}%</b>",
        f"\n<b>Добыча в час:</b>",
    ]
    for r in RESOURCE_ORDER:
        lines.append(f"  {RESOURCE_NAMES[r]}: <b>{rates[r]}/ч</b>")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  💰 ПРОДАЖА РУДЫ
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cl_sell:"))
async def cb_sell(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = _get_clan_member(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    role = clan["members"].get(str(callback.from_user.id), "member")
    if not _can(role, "sell_ore"):
        await callback.answer("❌ Нет прав для продажи руды!", show_alert=True); return
    _flush_mine(clan)
    prices = _market_prices()
    last_upd = prices.get("last_update", 0)
    next_upd = max(0, 3600 - (int(time.time()) - last_upd))
    nm = int(next_upd / 60)
    lines = [
        "💰 <b>ПРОДАЖА РУДЫ</b>",
        "━━━━━━━━━━━━━━━━━━━━━━\n",
        f"🕐 Цены обновятся через: <b>{nm} мин</b>\n",
    ]
    wh    = clan.get("warehouse", {})
    total = 0
    for r in RESOURCE_ORDER:
        amt  = wh.get(r, 0)
        prc  = prices.get(r, BASE_PRICES[r])
        val  = int(amt * prc)
        total += val
        chg  = round((prc / BASE_PRICES[r] - 1) * 100, 1)
        arrow = "📈" if chg >= 0 else "📉"
        lines.append(f"  {RESOURCE_NAMES[r]}: {_fmtint(amt)} ед. × {_fmt(prc)}$ {arrow}{abs(chg)}% = <b>{_fmt(val)}$</b>")
    lines.append(f"\n💰 Итого: <b>{_fmt(total)}$</b>")
    lines.append(f"🏦 Казна: <b>{_fmt(clan.get('treasury',0))}$</b>")
    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Продать всё ({_fmt(total)}$)", callback_data=f"cl_sell_all:{clan_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"clan_back:{clan_id}")],
        ]) if total > 0 else InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"clan_back:{clan_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cl_sell_all:"))
async def cb_sell_all(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    role = clan["members"].get(str(callback.from_user.id), "member")
    if not _can(role, "sell_ore"):
        await callback.answer("❌ Нет прав!", show_alert=True); return
    _flush_mine(clan)
    prices = _market_prices()
    wh     = clan.get("warehouse", {})
    sold_lines = []
    total  = 0
    for r in RESOURCE_ORDER:
        amt = wh.get(r, 0)
        if amt <= 0:
            continue
        val   = int(amt * prices.get(r, BASE_PRICES[r]))
        total += val
        sold_lines.append(f"{RESOURCE_NAMES[r]}: <b>{_fmtint(amt)}</b> ед. = <b>{_fmt(val)}$</b>")
        wh[r] = 0
    if total <= 0:
        await callback.answer("📦 Склад пуст!", show_alert=True); return
    clan["treasury"] = clan.get("treasury", 0) + total
    _add_log(clan, f"💰 Продана руда на {_fmt(total)}$ ({utils.get_name(callback.from_user.id)})")
    save_clans()
    await callback.message.edit_text(
        f"✅ <b>Руда продана!</b>\n\n"
        + "\n".join(sold_lines) + f"\n\n"
        f"💰 Выручка: <b>{_fmt(total)}$</b>\n"
        f"🏦 Казна: <b>{_fmt(clan['treasury'])}$</b>",
        parse_mode="HTML",
        reply_markup=_back_kb(clan_id)
    )
    await callback.answer("✅ Продано!")


# ═══════════════════════════════════════════════════════════════
#  ⚔ РЕЙДЫ
# ═══════════════════════════════════════════════════════════════

@router.message(F.text.lower().in_(["рейд", "/рейд"]))
async def cmd_raid_msg(message: Message):
    """Открыть меню рейдов (работает в личке и в группах)."""
    user_id = message.from_user.id
    clan    = get_user_clan(user_id)
    if not clan:
        await message.answer("❌ Вы не состоите в клане!", parse_mode="HTML")
        return
    clan_id = clan["id"]
    _flush_mine(clan)
    raid = active_raids.get(clan_id)
    text = _raids_text(clan, raid)
    await message.answer(
        text, parse_mode="HTML",
        reply_markup=_raids_kb(clan_id, clan, raid, user_id)
    )


@router.message(F.text.lower().in_(["рейд вступить", "/рейд вступить"]))
async def cmd_raid_join_msg(message: Message):
    user_id = message.from_user.id
    clan    = get_user_clan(user_id)
    if not clan:
        await message.answer("❌ Вы не состоите в клане!")
        return
    clan_id = clan["id"]
    raid    = active_raids.get(clan_id)
    if not raid or raid.get("status") != "preparing":
        await message.answer("❌ Нет активного набора в рейд! (набор уже завершён или рейд не начат)")
        return
    uid = str(user_id)
    if uid in raid.get("joined", []):
        await message.answer("✅ Вы уже участвуете в рейде!")
        return
    raid["joined"].append(uid)
    await message.answer(
        f"🔥 <b>Вы вступили в рейд!</b>\n"
        f"👥 Бойцов: <b>{len(raid['joined'])}</b>",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("cl_raids:"))
async def cb_raids(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = _get_clan_member(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    raid = active_raids.get(clan_id)
    text = _raids_text(clan, raid)
    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=_raids_kb(clan_id, clan, raid, callback.from_user.id)
    )
    await callback.answer()


def _fmt_time(secs: int) -> str:
    if secs <= 0:
        return "0 мин"
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    if h > 0:
        return f"{h}ч {m}мин" if m else f"{h}ч"
    if m > 0:
        return f"{m}мин {s}сек" if s else f"{m}мин"
    return f"{s}сек"


def _raids_text(clan: dict, raid: dict | None) -> str:
    now  = int(time.time())
    cd   = clan.get("raid_cooldown", 0)
    left = max(0, cd - now)
    icon = clan.get("icon", "🛡")
    name = clan["name"]

    lines = [
        "╔══════════════════════════╗",
        f"         ⚔️  <b>РЕЙДЫ</b>  ⚔️",
        "╚══════════════════════════╝\n",
        f"🏰 <b>{icon} {name}</b>",
        f"⭐ Рейтинг: <b>{_fmt(clan.get('rating',0))}</b>",
        f"🏆 Победы: <b>{clan.get('wins',0)}</b>   💀 Поражений: <b>{clan.get('losses',0)}</b>",
        f"⚔ Бонус рейда: <b>+{int((CLAN_LEVELS[clan.get('level',1)]['raid_bonus']-1)*100)}%</b>",
        "",
    ]

    if raid:
        status   = raid.get("status", "")
        enemy    = raid.get("enemy_name", "???")
        enemy_icon = enemy.split()[0] if enemy else "☠️"
        joined   = len(raid.get("joined", []))
        deadline = raid.get("deadline", 0)

        if status == "preparing":
            secs_left   = max(0, deadline - now)
            battle_end  = deadline + RAID_ACTIVE_SEC
            dt_deadline = datetime.fromtimestamp(deadline).strftime("%H:%M")
            dt_end      = datetime.fromtimestamp(battle_end).strftime("%H:%M")
            lines += [
                "┌──────────────────────────┐",
                "   🔥 <b>НАБОР БОЙЦОВ!</b> 🔥",
                "└──────────────────────────┘\n",
                f"  {icon} <b>{name}</b>",
                "        ⚡️  <b>VS</b>  ⚡️",
                f"  ☠️ <b>{enemy}</b>\n",
                f"⏳ До начала боя: <b>{_fmt_time(secs_left)}</b>",
                f"🕐 Старт боя: <b>{dt_deadline}</b>",
                f"🏁 Конец рейда: <b>{dt_end}</b>",
                f"👥 Вступило бойцов: <b>{joined}</b>\n",
                "💡 Команда: <code>рейд вступить</code>",
            ]
        elif status == "active":
            active_end  = raid.get("active_end", deadline + RAID_ACTIVE_SEC)
            secs_left   = max(0, active_end - now)
            dt_end      = datetime.fromtimestamp(active_end).strftime("%H:%M")
            lines += [
                "┌──────────────────────────┐",
                "  ⚔️ <b>СРАЖЕНИЕ ИДЁТ!</b> ⚔️",
                "└──────────────────────────┘\n",
                f"  {icon} <b>{name}</b>",
                "        ⚡️  <b>VS</b>  ⚡️",
                f"  ☠️ <b>{enemy}</b>\n",
                f"⏳ До конца боя: <b>{_fmt_time(secs_left)}</b>",
                f"🏁 Окончание: <b>{dt_end}</b>",
                f"👥 Бойцов в рейде: <b>{joined}</b>",
            ]
        elif status == "done":
            result = raid.get("result", "")
            if result == "win":
                lines += [
                    "┌──────────────────────────┐",
                    "  🏆 <b>ПОБЕДА В РЕЙДЕ!</b> 🏆",
                    "└──────────────────────────┘",
                    f"  vs {enemy}",
                ]
            else:
                lines += [
                    "┌──────────────────────────┐",
                    "  💀 <b>ПОРАЖЕНИЕ В РЕЙДЕ</b> 💀",
                    "└──────────────────────────┘",
                    f"  vs {enemy}",
                ]
    elif left > 0:
        lines.append(f"⏳ Кулдаун: <b>{_fmt_time(left)}</b>")
    else:
        lines.append("✅ <b>Можно начать рейд!</b>")
    return "\n".join(lines)


def _raids_kb(clan_id: str, clan: dict, raid: dict | None, user_id: int) -> InlineKeyboardMarkup:
    role = clan["members"].get(str(user_id), "member")
    rows = []
    if raid and raid.get("status") == "preparing":
        if str(user_id) not in raid.get("joined", []):
            rows.append([InlineKeyboardButton(text="🔥 Вступить в рейд", callback_data=f"cl_raid_join:{clan_id}")])
        else:
            rows.append([InlineKeyboardButton(text="✅ Вы уже участвуете", callback_data="cl_noop")])
        rows.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"cl_raids:{clan_id}")])
    elif raid and raid.get("status") == "active":
        rows.append([InlineKeyboardButton(text="⚔️ Сражение идёт...", callback_data="cl_noop")])
        rows.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"cl_raids:{clan_id}")])
    elif not raid or raid.get("status") == "done":
        cd = clan.get("raid_cooldown", 0)
        if int(time.time()) >= cd and role in ("owner", "deputy"):
            rows.append([InlineKeyboardButton(text="⚔️ Начать рейд", callback_data=f"cl_raid_start:{clan_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад в клан", callback_data=f"clan_back:{clan_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "cl_noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("cl_raid_start:"))
async def cb_raid_start(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    role = clan["members"].get(str(callback.from_user.id), "member")
    if not _can(role, "start_raid"):
        await callback.answer("❌ Нет прав для запуска рейда!", show_alert=True); return
    if int(time.time()) < clan.get("raid_cooldown", 0):
        await callback.answer("⏳ Рейд на кулдауне!", show_alert=True); return
    if clan_id in active_raids and active_raids[clan_id].get("status") == "preparing":
        await callback.answer("⚔ Рейд уже идёт!", show_alert=True); return

    # Поиск противника
    my_rating = clan.get("rating", 0)
    candidates = [
        c for cid, c in clans_data.items()
        if isinstance(c, dict) and "id" in c
        and cid != clan_id
        and abs(c.get("rating", 0) - my_rating) <= max(500, my_rating * 0.3)
    ]
    if not candidates:
        candidates = [c for cid, c in clans_data.items() if isinstance(c, dict) and "id" in c and cid != clan_id]
    if not candidates:
        await callback.answer("❌ Нет кланов для рейда!", show_alert=True); return
    enemy = random.choice(candidates)
    deadline = int(time.time()) + RAID_JOIN_SEC
    active_raids[clan_id] = {
        "status": "preparing",
        "enemy_id": enemy["id"],
        "enemy_name": f"{enemy.get('icon','')} {enemy['name']}",
        "joined": [str(callback.from_user.id)],
        "deadline": deadline,
    }
    _add_log(clan, f"⚔ Запущен рейд против {enemy['name']}")

    # Уведомить участников
    asyncio.create_task(_notify_raid_members(clan, enemy, deadline))
    asyncio.create_task(_auto_resolve_raid(clan_id, deadline))

    await callback.message.edit_text(
        f"⚔ <b>РЕЙД НАЧАТ!</b>\n\n"
        f"🎯 Противник: <b>{enemy.get('icon','')} {enemy['name']}</b>\n"
        f"⭐ Рейтинг врага: <b>{_fmt(enemy.get('rating',0))}</b>\n"
        f"⏳ Время на сбор: <b>{RAID_JOIN_SEC} сек</b>\n\n"
        f"<i>Участники получили уведомление!</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Присоединиться", callback_data=f"cl_raid_join:{clan_id}")],
            [InlineKeyboardButton(text="⬅️ Назад",           callback_data=f"clan_back:{clan_id}")],
        ])
    )
    await callback.answer("⚔ Рейд начат!")


@router.callback_query(F.data.startswith("cl_raid_join:"))
async def cb_raid_join(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    if str(callback.from_user.id) not in clan.get("members", {}):
        await callback.answer("❌ Вы не в этом клане!", show_alert=True); return
    raid = active_raids.get(clan_id)
    if not raid or raid.get("status") != "preparing":
        await callback.answer("❌ Нет активного рейда!", show_alert=True); return
    uid = str(callback.from_user.id)
    if uid in raid.get("joined", []):
        await callback.answer("✅ Вы уже участвуете!", show_alert=True); return
    raid["joined"].append(uid)
    await callback.answer(f"🔥 Вы присоединились к рейду! ({len(raid['joined'])} участников)")


async def _notify_raid_members(clan: dict, enemy: dict, deadline: int):
    try:
        from config import bot as _bot
        members = clan.get("members", {})
        battle_end = deadline + RAID_ACTIVE_SEC
        dt_start = datetime.fromtimestamp(deadline).strftime("%H:%M")
        dt_end   = datetime.fromtimestamp(battle_end).strftime("%H:%M")
        for uid_str in members:
            try:
                await _bot.send_message(
                    int(uid_str),
                    f"⚔️ <b>РЕЙД НАЧАТ!</b>\n\n"
                    f"🏰 <b>{clan.get('icon','')} {clan['name']}</b>\n"
                    f"        ⚡️ <b>VS</b> ⚡️\n"
                    f"☠️ <b>{enemy.get('icon','')} {enemy['name']}</b>\n\n"
                    f"⏳ Набор бойцов: <b>2ч 30мин</b>\n"
                    f"🕐 Старт боя: <b>{dt_start}</b>\n"
                    f"🏁 Конец рейда: <b>{dt_end}</b>\n\n"
                    f"💡 Напиши: <code>рейд вступить</code> чтобы участвовать!",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            await asyncio.sleep(0.05)
    except Exception:
        pass


async def _notify_raid_active(clan: dict, raid: dict):
    try:
        from config import bot as _bot
        active_end = raid.get("active_end", 0)
        dt_end = datetime.fromtimestamp(active_end).strftime("%H:%M")
        enemy  = raid.get("enemy_name", "???")
        for uid_str in raid.get("joined", []):
            try:
                await _bot.send_message(
                    int(uid_str),
                    f"⚔️ <b>БОЙ НАЧАЛСЯ!</b>\n\n"
                    f"🏰 <b>{clan.get('icon','')} {clan['name']}</b>\n"
                    f"        ⚡️ <b>VS</b> ⚡️\n"
                    f"☠️ <b>{enemy}</b>\n\n"
                    f"👥 Бойцов: <b>{len(raid.get('joined', []))}</b>\n"
                    f"🏁 Итоги в: <b>{dt_end}</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            await asyncio.sleep(0.05)
    except Exception:
        pass


async def _auto_resolve_raid(clan_id: str, deadline: int):
    # Ждём конца окна вступления
    wait = max(0, deadline - int(time.time()))
    await asyncio.sleep(wait + 1)
    clan = clans_data.get(clan_id)
    raid = active_raids.get(clan_id)
    if not clan or not raid or raid.get("status") != "preparing":
        return
    # Переходим в активную фазу
    active_end = int(time.time()) + RAID_ACTIVE_SEC
    raid["status"]     = "active"
    raid["active_end"] = active_end
    asyncio.create_task(_notify_raid_active(clan, raid))
    # Ждём конца активной фазы
    await asyncio.sleep(RAID_ACTIVE_SEC + 1)
    clan = clans_data.get(clan_id)
    raid = active_raids.get(clan_id)
    if not clan or not raid or raid.get("status") != "active":
        return
    await _resolve_raid(clan_id, clan, raid)


async def _resolve_raid(clan_id: str, clan: dict, raid: dict):
    enemy_id   = raid.get("enemy_id")
    enemy      = clans_data.get(enemy_id)
    joined     = len(raid.get("joined", []))
    my_level   = clan.get("level", 1)
    my_rating  = clan.get("rating", 0)
    my_power   = (joined + 1) * my_level * CLAN_LEVELS[my_level]["raid_bonus"] + my_rating * 0.01

    if enemy:
        en_members = len(enemy.get("members", {}))
        en_level   = enemy.get("level", 1)
        en_rating  = enemy.get("rating", 0)
        en_power   = (en_members + 1) * en_level * CLAN_LEVELS[en_level]["raid_bonus"] + en_rating * 0.01
    else:
        en_power   = max(1, my_power * random.uniform(0.7, 1.3))

    # случайный фактор ±30%
    my_power *= random.uniform(0.7, 1.3)

    win = my_power >= en_power

    if win:
        rating_change = 100_000
        money_loot    = random.randint(50_000, 500_000)
        loot = {r: random.randint(100, 2000) for r in RESOURCE_ORDER}
        clan["rating"]       = clan.get("rating", 0) + rating_change
        clan["treasury"]     = clan.get("treasury", 0) + money_loot
        clan["wins"]         = clan.get("wins", 0) + 1
        wh = clan.setdefault("warehouse", {r: 0 for r in RESOURCE_ORDER})
        level   = clan.get("level", 1)
        cap     = CLAN_LEVELS[level]["warehouse_cap"]
        _flush_mine(clan)
        for r in RESOURCE_ORDER:
            wh[r] = min(wh.get(r, 0) + loot[r], cap)
        _add_season_points(clan, "raid_win")
        enemy_name = raid.get('enemy_name', '???')
        result_text = (
            f"🏆 <b>ВЫ ПОБЕДИЛИ В РЕЙДЕ!</b>\n\n"
            f"╔══════════════════════════╗\n"
            f"  {clan.get('icon','')} <b>{clan['name']}</b>\n"
            f"      ⚡️ <b>VS</b> ⚡️\n"
            f"  ☠️ <b>{enemy_name}</b>\n"
            f"╚══════════════════════════╝\n\n"
            f"👥 Участвовало: <b>{joined}</b> бойцов\n\n"
            f"<b>🎁 Получено:</b>\n"
            f"  💰 Деньги: +<b>{_fmt(money_loot)}$</b>\n"
            f"  ⭐ Рейтинг клана: +<b>{_fmt(rating_change)}</b>"
        )
        _add_log(clan, f"🏆 Победа в рейде против {enemy_name} (+{_fmt(rating_change)} рейтинга)")
        raid["result"] = "win"

        # Нанесение потерь врагу
        if enemy:
            enemy["rating"] = max(0, enemy.get("rating", 0) - random.randint(10, 30))
            enemy_wh = enemy.setdefault("warehouse", {r: 0 for r in RESOURCE_ORDER})
            for r in RESOURCE_ORDER:
                enemy_wh[r] = max(0, enemy_wh.get(r, 0) - loot[r])
            _add_log(enemy, f"💀 Поражение в рейде от {clan.get('icon','')} {clan['name']}")
            # Уведомить защищающийся клан о поражении
            enemy_result_text = (
                f"💀 <b>ВАШ КЛАН ПРОИГРАЛ РЕЙД!</b>\n\n"
                f"╔══════════════════════════╗\n"
                f"  {clan.get('icon','')} <b>{clan['name']}</b>\n"
                f"      ⚡️ <b>VS</b> ⚡️\n"
                f"  {enemy.get('icon','')} <b>{enemy['name']}</b>\n"
                f"╚══════════════════════════╝\n\n"
                f"😢 Ваш клан был атакован и потерпел поражение.\n"
                f"  ⭐ Потери рейтинга: -<b>{random.randint(10, 30)}</b>"
            )
            asyncio.create_task(_notify_clan_members_text(enemy, enemy_result_text))
    else:
        rating_loss = random.randint(10, 30)
        loot_lost   = {r: int(clan.get("warehouse", {}).get(r, 0) * random.uniform(0.05, 0.15)) for r in RESOURCE_ORDER}
        clan["rating"] = max(0, clan.get("rating", 0) - rating_loss)
        clan["losses"] = clan.get("losses", 0) + 1
        wh = clan.setdefault("warehouse", {r: 0 for r in RESOURCE_ORDER})
        for r in RESOURCE_ORDER:
            wh[r] = max(0, wh.get(r, 0) - loot_lost[r])
        _add_season_points(clan, "raid_loss")
        enemy_name = raid.get('enemy_name', '???')
        result_text = (
            f"💀 <b>ВЫ ПРОИГРАЛИ РЕЙД!</b>\n\n"
            f"╔══════════════════════════╗\n"
            f"  {clan.get('icon','')} <b>{clan['name']}</b>\n"
            f"      ⚡️ <b>VS</b> ⚡️\n"
            f"  ☠️ <b>{enemy_name}</b>\n"
            f"╚══════════════════════════╝\n\n"
            f"👥 Участвовало: <b>{joined}</b> бойцов\n\n"
            f"<b>💸 Потери:</b>\n"
            f"  ⭐ Рейтинг: -<b>{rating_loss}</b>"
        )
        _add_log(clan, f"💀 Поражение в рейде против {enemy_name} (-{rating_loss} рейтинга)")
        raid["result"] = "loss"

    clan["raid_cooldown"] = int(time.time()) + RAID_COOLDOWN_SEC
    raid["status"] = "done"
    save_clans()

    # Уведомить участников о результате
    try:
        from config import bot as _bot
        for uid_str in raid.get("joined", []):
            try:
                await _bot.send_message(int(uid_str), result_text, parse_mode="HTML")
            except Exception:
                pass
            await asyncio.sleep(0.05)
    except Exception:
        pass


async def _notify_clan_members_text(clan: dict, text: str):
    try:
        from config import bot as _bot
        for uid_str in clan.get("members", {}):
            try:
                await _bot.send_message(int(uid_str), text, parse_mode="HTML")
            except Exception:
                pass
            await asyncio.sleep(0.05)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
#  👥 УЧАСТНИКИ
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cl_members:"))
async def cb_members(callback: CallbackQuery):
    clan_id  = callback.data.split(":", 1)[1]
    clan     = _get_clan_member(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    members  = clan.get("members", {})
    sorted_m = sorted(members.items(), key=lambda x: ROLE_ORDER.get(x[1], 9))
    my_role  = members.get(str(callback.from_user.id))
    rows = []
    rows.append([InlineKeyboardButton(text="🚪 Покинуть клан", callback_data=f"cl_leave_ask:{clan_id}")])
    if my_role in ("owner", "deputy"):
        rows.append([InlineKeyboardButton(text="➕ Пригласить",       callback_data=f"cl_invite:{clan_id}"),
                     InlineKeyboardButton(text="🚫 Выгнать",          callback_data=f"cl_kick_list:{clan_id}")])
    for uid_str, role in sorted_m:
        u    = utils.user_data.get(uid_str, {})
        name = u.get("name", f"ID {uid_str}")
        role_icon = {"owner": "👑", "deputy": "🥈", "officer": "🎖", "member": "👤"}.get(role, "👤")
        rows.append([InlineKeyboardButton(
            text=f"{role_icon} {name}",
            callback_data=f"cl_mprofile:{clan_id}:{uid_str}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"clan_back:{clan_id}")])
    await callback.message.edit_text(
        f"👥 <b>УЧАСТНИКИ КЛАНА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{clan.get('icon','')} <b>{clan['name']}</b>\n\n"
        f"<i>Всего: {len(members)} / {MAX_CLAN_MEMBERS}. Нажмите на участника для просмотра профиля.</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cl_mprofile:"))
async def cb_member_profile(callback: CallbackQuery):
    parts    = callback.data.split(":", 2)
    clan_id  = parts[1]
    uid_str  = parts[2]
    clan     = _get_clan_member(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    my_uid   = str(callback.from_user.id)
    my_role  = clan.get("members", {}).get(my_uid, "member")
    u        = utils.user_data.get(uid_str, {})
    name     = u.get("name", f"ID {uid_str}")
    balance  = u.get("balance", 0)
    level    = u.get("level", 1)
    role     = clan.get("members", {}).get(uid_str, "member")
    role_lbl  = ROLE_NAMES.get(role, "👤 Участник")
    role_icon = {"owner": "👑", "deputy": "🥈", "officer": "🎖", "member": "👤"}.get(role, "👤")
    text = (
        f"╔══════════════════════════╗\n"
        f"  {role_icon} <b>{name}</b>\n"
        f"╚══════════════════════════╝\n\n"
        f"🎖 Роль: <b>{role_lbl}</b>\n"
        f"📈 Уровень: <b>{level}</b>\n"
        f"💰 Баланс: <b>{_fmt(balance)}$</b>\n"
    )
    rows = []
    if uid_str != my_uid:
        can_kick = (
            (my_role == "owner" and role in ("deputy", "officer", "member")) or
            (my_role == "deputy" and role in ("officer", "member"))
        )
        if can_kick:
            rows.append([InlineKeyboardButton(text="🚫 Выгнать", callback_data=f"cl_kick_direct:{clan_id}:{uid_str}")])
        PROMOTE = {"member": "officer", "officer": "deputy"}
        DEMOTE  = {"deputy": "officer", "officer": "member"}
        act_row = []
        if my_role == "owner":
            if role in PROMOTE:
                act_row.append(InlineKeyboardButton(text="⬆ Повысить", callback_data=f"cl_role_set:{clan_id}:{uid_str}:{PROMOTE[role]}"))
            if role in DEMOTE:
                act_row.append(InlineKeyboardButton(text="⬇ Понизить", callback_data=f"cl_role_set:{clan_id}:{uid_str}:{DEMOTE[role]}"))
        elif my_role == "deputy":
            if role == "member":
                act_row.append(InlineKeyboardButton(text="⬆ Повысить", callback_data=f"cl_role_set:{clan_id}:{uid_str}:officer"))
            if role == "officer":
                act_row.append(InlineKeyboardButton(text="⬇ Понизить", callback_data=f"cl_role_set:{clan_id}:{uid_str}:member"))
        if act_row:
            rows.append(act_row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cl_members:{clan_id}")])
    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cl_leave_ask:"))
async def cb_leave_ask(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    if clan.get("owner_id") == callback.from_user.id:
        await callback.answer("❌ Владелец не может выйти — передайте клан!", show_alert=True); return
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите выйти из клана <b>{clan['name']}</b>?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, выйти",  callback_data=f"cl_leave_do:{clan_id}")],
            [InlineKeyboardButton(text="❌ Нет",         callback_data=f"cl_members:{clan_id}")],
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cl_leave_do:"))
async def cb_leave_do(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    user_id = callback.from_user.id
    if clan.get("owner_id") == user_id:
        await callback.answer("❌ Нельзя!", show_alert=True); return
    clan["members"].pop(str(user_id), None)
    _add_log(clan, f"🚪 Вышел {utils.get_name(user_id)}")
    save_clans()
    await callback.message.edit_text(
        f"✅ Вы вышли из клана <b>{clan['name']}</b>.",
        parse_mode="HTML", reply_markup=_no_clan_kb()
    )
    await callback.answer("Вы вышли из клана")


@router.callback_query(F.data.startswith("cl_kick_list:"))
async def cb_kick_list(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    role = clan["members"].get(str(callback.from_user.id))
    if role not in ("owner", "deputy"):
        await callback.answer("❌ Нет прав!", show_alert=True); return
    members = {k: v for k, v in clan.get("members", {}).items() if k != str(callback.from_user.id)}
    if not members:
        await callback.answer("Нет участников для выгона", show_alert=True); return
    rows = []
    for uid_str, mrole in members.items():
        if role == "deputy" and mrole == "owner":
            continue
        u    = utils.user_data.get(uid_str, {})
        name = u.get("name", f"ID {uid_str}")
        rows.append([InlineKeyboardButton(
            text=f"🚫 {ROLE_NAMES.get(mrole,'').split()[-1]} {name}",
            callback_data=f"cl_kick:{clan_id}:{uid_str}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cl_members:{clan_id}")])
    await callback.message.edit_text(
        "🚫 <b>Выгнать участника:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cl_kick:"))
async def cb_kick(callback: CallbackQuery):
    parts   = callback.data.split(":", 2)
    clan_id = parts[1]; target_uid = parts[2]
    clan    = clans_data.get(clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    role = clan["members"].get(str(callback.from_user.id))
    if role not in ("owner", "deputy"):
        await callback.answer("❌ Нет прав!", show_alert=True); return
    name = utils.user_data.get(target_uid, {}).get("name", f"ID {target_uid}")
    clan["members"].pop(target_uid, None)
    _add_log(clan, f"🚫 Выгнан {name}")
    save_clans()
    await callback.answer(f"✅ {name} исключён")
    await cb_kick_list(callback)


@router.callback_query(F.data.startswith("cl_kick_direct:"))
async def cb_kick_direct(callback: CallbackQuery):
    parts      = callback.data.split(":", 2)
    clan_id    = parts[1]
    target_uid = parts[2]
    clan       = clans_data.get(clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    my_role     = clan["members"].get(str(callback.from_user.id))
    target_role = clan["members"].get(target_uid)
    if not target_role:
        await callback.answer("❌ Участник не найден", show_alert=True); return
    can_kick = (
        (my_role == "owner" and target_role in ("deputy", "officer", "member")) or
        (my_role == "deputy" and target_role in ("officer", "member"))
    )
    if not can_kick:
        await callback.answer("❌ Нет прав!", show_alert=True); return
    name = utils.user_data.get(target_uid, {}).get("name", f"ID {target_uid}")
    clan["members"].pop(target_uid, None)
    _add_log(clan, f"🚫 Выгнан {name}")
    save_clans()
    await callback.answer(f"✅ {name} исключён", show_alert=True)
    callback.data = f"cl_members:{clan_id}"
    await cb_members(callback)


@router.callback_query(F.data.startswith("cl_role_set:"))
async def cb_role_set(callback: CallbackQuery):
    parts      = callback.data.split(":", 3)
    clan_id    = parts[1]
    target_uid = parts[2]
    new_role   = parts[3]
    clan       = clans_data.get(clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    my_role  = clan["members"].get(str(callback.from_user.id))
    old_role = clan["members"].get(target_uid)
    if not old_role:
        await callback.answer("❌ Участник не найден", show_alert=True); return
    allowed = False
    if my_role == "owner" and old_role != "owner" and new_role != "owner":
        allowed = True
    elif my_role == "deputy":
        if (old_role == "member" and new_role == "officer") or \
           (old_role == "officer" and new_role == "member"):
            allowed = True
    if not allowed:
        await callback.answer("❌ Нет прав!", show_alert=True); return
    clan["members"][target_uid] = new_role
    name   = utils.user_data.get(target_uid, {}).get("name", f"ID {target_uid}")
    action = "повышен до" if ROLE_ORDER[new_role] < ROLE_ORDER[old_role] else "понижен до"
    _add_log(clan, f"🎖 {name} {action} {ROLE_NAMES[new_role]}")
    save_clans()
    await callback.answer(f"✅ {name} → {ROLE_NAMES[new_role]}", show_alert=True)
    callback.data = f"cl_mprofile:{clan_id}:{target_uid}"
    await cb_member_profile(callback)


@router.callback_query(F.data.startswith("cl_invite:"))
async def cb_invite(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    role = clan["members"].get(str(callback.from_user.id))
    if role not in ("owner", "deputy"):
        await callback.answer("❌ Нет прав!", show_alert=True); return
    await callback.answer(
        f"📨 Напишите в чат:\nпригласить клан (ID игрока)\n\nПример: пригласить клан 123456789",
        show_alert=True
    )


@router.message(F.text.regexp(r"(?i)^пригласить клан\s+\d+"))
async def cmd_clan_invite(message: Message):
    parts = message.text.split()
    try:
        target_id = int(parts[2])
    except (IndexError, ValueError):
        await message.answer("❌ Формат: пригласить клан (ID игрока)")
        return
    sender_id = message.from_user.id
    sender_clan    = None
    sender_clan_id = None
    for cid, clan in clans_data.items():
        if not isinstance(clan, dict):
            continue
        if str(sender_id) in clan.get("members", {}):
            sender_clan    = clan
            sender_clan_id = cid
            break
    if not sender_clan:
        await message.answer("❌ Вы не состоите в клане.")
        return
    my_role = sender_clan["members"].get(str(sender_id))
    if my_role not in ("owner", "deputy"):
        await message.answer("❌ Только владелец или заместитель может приглашать.")
        return
    target_uid_str = str(target_id)
    target_user    = utils.user_data.get(target_uid_str)
    if not target_user:
        await message.answer("❌ Игрок не найден в базе.")
        return
    for cid, clan in clans_data.items():
        if not isinstance(clan, dict):
            continue
        if target_uid_str in clan.get("members", {}):
            tname = target_user.get("name", f"ID {target_id}")
            await message.answer(f"❌ Игрок <b>{tname}</b> уже состоит в клане.", parse_mode="HTML")
            return
    if len(sender_clan.get("members", {})) >= MAX_CLAN_MEMBERS:
        await message.answer("❌ Клан переполнен.")
        return
    target_name  = target_user.get("name", f"ID {target_id}")
    clan_name    = sender_clan.get("name", "???")
    clan_icon    = sender_clan.get("icon", "🏰")
    clan_desc    = sender_clan.get("description") or "—"
    clan_level   = sender_clan.get("level", 1)
    clan_members = len(sender_clan.get("members", {}))
    clan_rating  = sender_clan.get("rating", 0)
    inviter_name = utils.get_name(sender_id)
    text = (
        f"📨 <b>ПРИГЛАШЕНИЕ В КЛАН</b>\n\n"
        f"<b>{inviter_name}</b> приглашает вас в клан:\n\n"
        f"╔══════════════════════════╗\n"
        f"  {clan_icon} <b>{clan_name}</b>\n"
        f"╚══════════════════════════╝\n\n"
        f"📜 {clan_desc}\n\n"
        f"📈 Уровень: <b>{clan_level}</b>\n"
        f"👥 Участников: <b>{clan_members}</b> / {MAX_CLAN_MEMBERS}\n"
        f"⭐ Рейтинг: <b>{_fmt(clan_rating)}</b>\n"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Принять",    callback_data=f"cl_inv_accept:{sender_clan_id}:{sender_id}"),
        InlineKeyboardButton(text="❌ Отклонить",  callback_data=f"cl_inv_decline:{sender_clan_id}:{sender_id}"),
    ]])
    try:
        await message.bot.send_message(target_id, text, parse_mode="HTML", reply_markup=kb)
        await message.answer(f"✅ Приглашение отправлено <b>{target_name}</b>!", parse_mode="HTML")
    except Exception:
        await message.answer("❌ Не удалось отправить — игрок не начинал бота в ЛС.")


@router.callback_query(F.data.startswith("cl_inv_accept:"))
async def cb_inv_accept(callback: CallbackQuery):
    parts      = callback.data.split(":", 2)
    clan_id    = parts[1]
    inviter_id = int(parts[2])
    uid_str    = str(callback.from_user.id)
    clan       = clans_data.get(clan_id)
    if not clan:
        await callback.answer("❌ Клан больше не существует", show_alert=True)
        await callback.message.delete()
        return
    for cid, c in clans_data.items():
        if not isinstance(c, dict):
            continue
        if uid_str in c.get("members", {}):
            await callback.answer("❌ Вы уже состоите в клане!", show_alert=True)
            await callback.message.delete()
            return
    if len(clan.get("members", {})) >= MAX_CLAN_MEMBERS:
        await callback.answer("❌ Клан переполнен!", show_alert=True)
        await callback.message.delete()
        return
    clan["members"][uid_str] = "member"
    name = utils.get_name(callback.from_user.id)
    _add_log(clan, f"📨 {name} принял приглашение")
    save_clans()
    try:
        await callback.bot.send_message(
            inviter_id,
            f"✅ <b>{name}</b> принял ваше приглашение и вступил в клан <b>{clan['name']}</b>!",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.message.edit_text(
        f"✅ Добро пожаловать в клан <b>{clan.get('icon','')} {clan['name']}</b>!",
        parse_mode="HTML"
    )
    await callback.answer("Вы вступили в клан!")


@router.callback_query(F.data.startswith("cl_inv_decline:"))
async def cb_inv_decline(callback: CallbackQuery):
    parts      = callback.data.split(":", 2)
    clan_id    = parts[1]
    inviter_id = int(parts[2])
    clan       = clans_data.get(clan_id)
    clan_name  = clan.get("name", "???") if clan else "???"
    name       = utils.get_name(callback.from_user.id)
    try:
        await callback.bot.send_message(
            inviter_id,
            f"❌ <b>{name}</b> отклонил приглашение в клан <b>{clan_name}</b>.",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.message.edit_text("❌ Вы отклонили приглашение.")
    await callback.answer("Приглашение отклонено")


# ═══════════════════════════════════════════════════════════════
#  📊 СТАТИСТИКА КЛАНА
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cl_stats:"))
async def cb_stats(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = _get_clan_member(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    _flush_mine(clan)
    level    = clan.get("level", 1)
    rank     = _clan_rank(clan)
    total_cl = len([c for c in clans_data.values() if isinstance(c, dict) and "id" in c])
    owner    = utils.user_data.get(str(clan.get("owner_id","")), {}).get("name", "???")
    text = (
        f"📊 <b>СТАТИСТИКА КЛАНА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏰 Название: <b>{clan.get('icon','')} {clan['name']}</b>\n"
        f"🆔 ID: <b>#{clan.get('num_id','?')}</b>\n"
        f"👑 Владелец: <b>{owner}</b>\n"
        f"👥 Участников: <b>{len(clan.get('members',{}))}</b> / {MAX_CLAN_MEMBERS}\n"
        f"📈 Уровень: <b>{level}</b> / {MAX_CLAN_LEVEL}\n"
        f"📦 Склад: <b>{_fmtint(CLAN_LEVELS[level]['warehouse_cap'])}</b> ед.\n"
        f"💰 Казна: <b>{_fmt(clan.get('treasury',0))}$</b>\n"
        f"⚔ Победы: <b>{clan.get('wins',0)}</b>\n"
        f"💀 Поражения: <b>{clan.get('losses',0)}</b>\n"
        f"⭐ Рейтинг: <b>{_fmt(clan.get('rating',0))}</b>\n"
        f"🎖 Сезонные очки: <b>{clan.get('season_points',0)}</b>\n"
        f"🌍 Место в топе: <b>#{rank}</b> из {total_cl}\n"
    )
    total_matches = clan.get("wins", 0) + clan.get("losses", 0)
    if total_matches > 0:
        wr = round(clan.get("wins", 0) / total_matches * 100, 1)
        text += f"📊 Винрейт: <b>{wr}%</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_back_kb(clan_id))
    await callback.answer()


# ═══════════════════════════════════════════════════════════════
#  🏆 ТОП КЛАНОВ
# ═══════════════════════════════════════════════════════════════

TOP_MODES = {
    "rating":   ("⭐ Топ по рейтингу",    lambda c: c.get("rating", 0)),
    "rich":     ("💰 Топ по богатству",   lambda c: c.get("treasury", 0)),
    "raids":    ("⚔ Топ по рейдам",      lambda c: c.get("wins", 0)),
    "level":    ("📈 Топ по уровню",      lambda c: c.get("level", 0)),
    "members":  ("👥 Топ по участникам",  lambda c: len(c.get("members", {}))),
}
TOP_ORDER = ["rating", "rich", "raids", "level", "members"]


@router.callback_query(F.data.startswith("cl_top:"))
async def cb_top(callback: CallbackQuery):
    parts   = callback.data.split(":")
    mode    = parts[1]
    page    = int(parts[2]) if len(parts) > 2 else 0
    clan_id = parts[3] if len(parts) > 3 else ""
    if not clan_id:
        user_clan = get_user_clan(callback.from_user.id)
        clan_id   = user_clan["id"] if user_clan else ""
    await _show_top(callback.message, mode, page, edit=True, clan_id=clan_id)
    await callback.answer()


_TOP_REWARDS = {
    1: "👑 Лидер сезона — 5000$ в казну + 500 очков",
    2: "🥈 2 место — 3000$ в казну + 300 очков",
    3: "🥉 3 место — 1500$ в казну + 150 очков",
    4: "🏅 4–5 место — 500$ в казну + 50 очков",
}

async def _show_top(obj, mode: str, page: int, edit=False, send_new=False, clan_id: str = ""):
    if mode not in TOP_MODES:
        mode = "rating"
    title, key_fn = TOP_MODES[mode]
    clans = sorted(
        [c for c in clans_data.values() if isinstance(c, dict) and "id" in c],
        key=key_fn, reverse=True
    )
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 47
    lines = [
        f"🏆 <b>{title}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━\n",
    ]
    if not clans:
        lines.append("<i>Нет кланов</i>")
    else:
        for i, c in enumerate(clans[:10], 1):
            val     = key_fn(c)
            med     = medals[i - 1] if i <= len(medals) else f"{i}."
            val_str = (_fmt(val) + "$") if mode == "rich" else _fmt(val)
            lines.append(
                f"{med} <b>{i} место</b> — {c.get('icon','🛡')} <b>{c['name']}</b>\n"
                f"       └ {val_str}"
            )
    lines += [
        "",
        "🎁 <b>НАГРАДЫ ЗА СЕЗОН</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        _TOP_REWARDS[1],
        _TOP_REWARDS[2],
        _TOP_REWARDS[3],
        _TOP_REWARDS[4],
    ]
    nav_rows = []
    row = []
    for m in TOP_ORDER:
        t, _ = TOP_MODES[m]
        emoji = t.split()[0]
        row.append(InlineKeyboardButton(text=emoji + (" ✓" if m == mode else ""), callback_data=f"cl_top:{m}:0:{clan_id}"))
        if len(row) == 3:
            nav_rows.append(row); row = []
    if row:
        nav_rows.append(row)
    if clan_id:
        nav_rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"clan_back:{clan_id}")])
    kb = InlineKeyboardMarkup(inline_keyboard=nav_rows)
    text = "\n".join(lines)
    if send_new:
        await obj.answer(text, parse_mode="HTML", reply_markup=kb)
    elif edit:
        await obj.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await obj.answer(text, parse_mode="HTML", reply_markup=kb)


# ═══════════════════════════════════════════════════════════════
#  📝 ЛОГИ КЛАНА
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cl_system:"))
async def cb_system(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = _get_clan_member(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    role    = _get_role(clan, callback.from_user.id)
    rows    = [
        [
            InlineKeyboardButton(text="⚙ Управление",   callback_data=f"cl_manage:{clan_id}"),
            InlineKeyboardButton(text="⬆ Улучшение",    callback_data=f"cl_upgrade:{clan_id}"),
        ],
        [
            InlineKeyboardButton(text="📦 Склад",        callback_data=f"cl_warehouse:{clan_id}"),
            InlineKeyboardButton(text="💰 Продать руду", callback_data=f"cl_sell:{clan_id}"),
        ],
        [
            InlineKeyboardButton(text="📊 Статистика",   callback_data=f"cl_stats:{clan_id}"),
            InlineKeyboardButton(text="⚔ Рейды",        callback_data=f"cl_raids:{clan_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад",          callback_data=f"clan_back:{clan_id}")],
    ]
    await callback.message.edit_text(
        f"⚙️ <b>СИСТЕМА КЛАНА</b>\n\n"
        f"{clan.get('icon','🛡')} <b>{clan['name']}</b>\n\n"
        f"Выберите раздел управления:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cl_logs:"))
async def cb_logs(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = _get_clan_member(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    role    = _get_role(clan, callback.from_user.id)
    if role not in ("owner", "deputy"):
        await callback.answer("❌ Только лидер и зам могут просматривать логи.", show_alert=True)
        return
    logs = clan.get("logs", [])[:30]
    lines = [
        "📝 <b>ЛОГИ КЛАНА</b>",
        "━━━━━━━━━━━━━━━━━━━━━━\n",
    ]
    if not logs:
        lines.append("<i>Логов пока нет</i>")
    else:
        lines += [f"  {l}" for l in logs]
    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=_back_kb(clan_id)
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════
#  🎖 СЕЗОН
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cl_season:"))
async def cb_season(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id) if clan_id else None
    text    = _season_text(clan)
    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=_season_kb(clan_id)
    )
    await callback.answer()


def _season_text(clan: dict | None) -> str:
    s       = _season()
    number  = s.get("number", 1)
    left    = _season_time_left()
    clans_list = sorted(
        [c for c in clans_data.values() if isinstance(c, dict) and "id" in c],
        key=lambda x: x.get("season_points", 0), reverse=True
    )[:10]
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [
        f"🎖 <b>СЕЗОН #{number}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━\n",
        f"⏳ До конца сезона: <b>{left}</b>\n",
        "<b>Топ сезона:</b>",
    ]
    if not clans_list:
        lines.append("<i>Нет данных</i>")
    else:
        for i, c in enumerate(clans_list, 1):
            pts = c.get("season_points", 0)
            med = medals[i - 1] if i <= len(medals) else f"{i}."
            lines.append(f"  {med} <b>{i} место</b> — {c.get('icon','🛡')} <b>{c['name']}</b> | <b>{pts}</b> очков")
    lines += [
        "\n<b>Награды топ-5:</b>",
        f"  🥇 Топ 1: <b>{_fmt(SEASON_REWARDS[1])}$</b>",
        f"  🥈 Топ 2: <b>{_fmt(SEASON_REWARDS[2])}$</b>",
        f"  🥉 Топ 3: <b>{_fmt(SEASON_REWARDS[3])}$</b>",
        f"  🏅 Топ 4: <b>{_fmt(SEASON_REWARDS[4])}$</b>",
        f"  🎖 Топ 5: <b>{_fmt(SEASON_REWARDS[5])}$</b>",
        "\n<i>Награда делится между всеми участниками клана</i>",
    ]
    if clan:
        my_rank = next((i for i, c in enumerate(clans_list, 1) if c["id"] == clan["id"]), None)
        lines += [
            f"\n🏰 Ваш клан: <b>{clan.get('icon','')} {clan['name']}</b>",
            f"🎖 Ваши очки: <b>{clan.get('season_points',0)}</b>",
            f"🌍 Место: <b>{'#' + str(my_rank) if my_rank else 'вне топа'}</b>",
        ]
    lines += [
        "\n<b>Очки начисляются:</b>",
        f"  ⚔ Победа в рейде: <b>+{SEASON_POINTS['raid_win']}</b>",
        f"  💀 Поражение: <b>{SEASON_POINTS['raid_loss']}</b>",
        f"  ⬆ Улучшение клана: <b>+{SEASON_POINTS['upgrade']}</b>",
        f"  👥 Новый участник: <b>+{SEASON_POINTS['new_member']}</b>",
    ]
    return "\n".join(lines)


def _season_kb(clan_id: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="🔄 Обновить", callback_data=f"cl_season:{clan_id}")]]
    if clan_id:
        rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"clan_back:{clan_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _add_season_points(clan: dict, action: str):
    pts = SEASON_POINTS.get(action, 0)
    clan["season_points"] = max(0, clan.get("season_points", 0) + pts)


# ═══════════════════════════════════════════════════════════════
#  🏦 КАЗНА
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("clan_treasury:"))
async def cb_treasury(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = _get_clan_member(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    treasury = clan.get("treasury", 0)
    bal      = utils.get_balance(callback.from_user.id)
    donors   = clan.get("donors", {})
    top_lines = []
    if donors:
        for i, (uid, amt) in enumerate(sorted(donors.items(), key=lambda x: x[1], reverse=True)[:5], 1):
            n = utils.user_data.get(uid, {}).get("name", f"ID {uid}")
            top_lines.append(f"  {i}. {n} — <b>{_fmt(amt)}$</b>")
    role = clan["members"].get(str(callback.from_user.id))
    text = (
        f"🏦 <b>КАЗНА КЛАНА</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{clan.get('icon','🛡')} <b>{clan['name']}</b>\n\n"
        f"💰 Баланс казны: <b>{_fmt(treasury)}$</b>\n"
        f"💼 Ваш баланс: <b>{_fmt(bal)}$</b>\n"
        + ("\n🏆 <b>Топ вкладчиков:</b>\n" + "\n".join(top_lines) if top_lines else "")
    )
    rows = [[InlineKeyboardButton(text="💸 Вложить в казну", callback_data=f"clan_treasury_deposit:{clan_id}")]]
    if role == "owner":
        rows.append([InlineKeyboardButton(text="🎁 Раздать казну", callback_data=f"clan_treasury_distribute:{clan_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"clan_back:{clan_id}")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("clan_treasury_deposit:"))
async def cb_treasury_deposit_start(callback: CallbackQuery, state: FSMContext):
    clan_id = callback.data.split(":", 1)[1]
    clan    = _get_clan_member(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True); return
    await state.set_state(TreasuryDepositState.waiting_amount)
    await state.update_data(clan_id=clan_id)
    bal = utils.get_balance(callback.from_user.id)
    await callback.message.edit_text(
        f"💸 <b>ВКЛАД В КАЗНУ</b>\n\nВаш баланс: <b>{_fmt(bal)}$</b>\n\nВведите сумму:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"clan_treasury:{clan_id}")]
        ])
    )
    await callback.answer()


@router.message(TreasuryDepositState.waiting_amount)
async def msg_treasury_deposit(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data    = await state.get_data()
    clan_id = data.get("clan_id")
    clan    = clans_data.get(clan_id)
    if not clan:
        await state.clear(); return
    amount = parse_k(message.text.strip(), utils.get_balance(user_id))
    if not amount or amount <= 0:
        await message.answer("❌ Некорректная сумма."); return
    bal = utils.get_balance(user_id)
    if bal < amount:
        await message.answer(f"❌ Недостаточно средств! Баланс: {_fmt(bal)}$"); return
    await state.clear()
    utils.update_balance(user_id, bal - amount)
    clan["treasury"] = clan.get("treasury", 0) + amount
    clan.setdefault("donors", {})[str(user_id)] = clan.get("donors", {}).get(str(user_id), 0) + amount
    _add_log(clan, f"💸 {utils.get_name(user_id)} вложил {_fmt(amount)}$ в казну")
    save_clans()
    await message.answer(
        f"✅ Вы вложили <b>{_fmt(amount)}$</b> в казну клана.\n"
        f"🏦 Казна: <b>{_fmt(clan['treasury'])}$</b>",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("clan_treasury_distribute:"))
async def cb_treasury_distribute(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan    = clans_data.get(clan_id)
    if not clan or clan.get("owner_id") != callback.from_user.id:
        await callback.answer("❌ Только владелец!", show_alert=True); return
    treasury = clan.get("treasury", 0)
    members  = clan.get("members", {})
    if treasury <= 0:
        await callback.answer("❌ Казна пуста!", show_alert=True); return
    if not members:
        await callback.answer("❌ Нет участников!", show_alert=True); return
    per_person = treasury // len(members)
    if per_person <= 0:
        await callback.answer("❌ Слишком мало для раздачи!", show_alert=True); return
    for uid_str in members:
        utils.update_balance(int(uid_str), utils.get_balance(int(uid_str)) + per_person)
    clan["treasury"] = 0
    _add_log(clan, f"🎁 Казна раздана: {_fmt(per_person)}$ каждому участнику")
    save_clans()
    await callback.message.edit_text(
        f"🎁 <b>Казна распределена!</b>\n\n"
        f"💰 Каждый участник ({len(members)}) получил: <b>{_fmt(per_person)}$</b>",
        parse_mode="HTML", reply_markup=_back_kb(clan_id)
    )
    await callback.answer("✅ Раздано!")


# ═══════════════════════════════════════════════════════════════
#  📅 АВТОМАТИЧЕСКИЕ ЗАДАЧИ (вызывать из bot.py)
# ═══════════════════════════════════════════════════════════════

def auto_mine_ore():
    """Вызывать каждый час — начисляет руду всем кланам."""
    changed = False
    for cid, clan in clans_data.items():
        if not isinstance(clan, dict) or "id" not in clan:
            continue
        try:
            _flush_mine(clan)
            changed = True
        except Exception as e:
            print(f"[КЛАНЫ] Ошибка добычи {cid}: {e}")
    if changed:
        save_clans()


def update_market_prices():
    """Обновлять рыночные цены каждый час."""
    clans_data["_market"] = _new_market_data()
    save_clans()
    print("[КЛАНЫ] Рыночные цены обновлены")


async def check_season_end():
    """Проверять конец сезона каждые 10 минут."""
    s   = _season()
    now = int(time.time())
    if now < s.get("end_ts", 0):
        return
    await _finalize_season()


async def _finalize_season():
    s      = _season()
    number = s.get("number", 1)
    clans_list = sorted(
        [c for c in clans_data.values() if isinstance(c, dict) and "id" in c],
        key=lambda x: x.get("season_points", 0), reverse=True
    )
    reward_msgs = []
    for rank, clan in enumerate(clans_list[:5], 1):
        reward = SEASON_REWARDS.get(rank, 0)
        members = clan.get("members", {})
        if not members:
            continue
        per_person = reward // len(members)
        if per_person <= 0:
            continue
        for uid_str in members:
            utils.update_balance(int(uid_str), utils.get_balance(int(uid_str)) + per_person)
        _add_log(clan, f"🏆 Сезон #{number}: {rank} место! Каждый получил {_fmt(per_person)}$")
        reward_msgs.append((clan, rank, reward, per_person, list(members.keys())))

    # Сброс сезонных очков
    for clan in clans_data.values():
        if isinstance(clan, dict) and "id" in clan:
            clan["season_points"] = 0

    # Начало нового сезона
    clans_data["_season"] = _new_season_data()
    save_clans()

    print(f"[КЛАНЫ] Сезон #{number} завершён. Начался сезон #{clans_data['_season']['number']}")

    # Уведомления
    try:
        from config import bot as _bot
        for clan, rank, reward, per_person, member_ids in reward_msgs:
            medals = {1: "🥇", 2: "🥈", 3: "🥉", 4: "🏅", 5: "🎖"}
            med    = medals.get(rank, "🏅")
            text   = (
                f"🎖 <b>Сезон #{number} завершён!</b>\n\n"
                f"{med} Ваш клан занял <b>{rank} место</b>!\n"
                f"💰 Награда: <b>{_fmt(reward)}$</b>\n"
                f"🤝 Каждый участник получил: <b>{_fmt(per_person)}$</b>\n\n"
                f"Начался новый сезон #{clans_data['_season']['number']}!"
            )
            for uid_str in member_ids:
                try:
                    await _bot.send_message(int(uid_str), text, parse_mode="HTML")
                except Exception:
                    pass
                await asyncio.sleep(0.05)
    except Exception as e:
        print(f"[КЛАНЫ] Ошибка уведомлений сезона: {e}")


# ═══════════════════════════════════════════════════════════════
#  ПРИВЯЗКА КЛАНА К ЧАТУ
# ═══════════════════════════════════════════════════════════════

async def notify_bound_chat(clan: dict, text: str):
    """Отправляет уведомление в привязанный чат клана."""
    chat_id = clan.get("bound_chat_id")
    if not chat_id:
        return
    try:
        from config import bot as _bot
        await _bot.send_message(chat_id, text, parse_mode="HTML")
    except Exception as e:
        print(f"[КЛАНЫ] Ошибка уведомления в чат {chat_id}: {e}")


def _find_clan_by_chat(chat_id: int) -> dict | None:
    """Возвращает клан, привязанный к данному chat_id, или None."""
    for clan in clans_data.values():
        if isinstance(clan, dict) and clan.get("bound_chat_id") == chat_id:
            return clan
    return None


@router.message(F.text.lower().in_(["чат ид", "чат id", "chat id", "id чата", "ид чата"]))
async def get_chat_id_cmd(message: Message):
    """Команда в группе — показывает ID текущего чата для привязки клана."""
    if message.chat.type == "private":
        await message.answer(
            "ℹ️ Эта команда работает только в групповых чатах.\n"
            "Добавь бота в группу и напиши там <code>чат ид</code>.",
            parse_mode="HTML",
        )
        return
    # Проверяем, привязан ли чат к клану
    existing = _find_clan_by_chat(message.chat.id)
    binding_line = ""
    if existing:
        binding_line = f"\n\n🏰 Этот чат уже привязан к клану: <b>{existing.get('name', '?')}</b>"
    await message.answer(
        f"🔗 <b>ID этого чата:</b>\n"
        f"<code>{message.chat.id}</code>\n\n"
        f"Лидер клана может привязать этот чат командой прямо здесь:\n"
        f"<code>клан чат</code>\n\n"
        f"Или вручную в личке с ботом:\n"
        f"<code>клан чат {message.chat.id}</code>"
        f"{binding_line}",
        parse_mode="HTML",
    )


@router.message(F.text.lower().startswith("клан чат"))
async def clan_bind_chat_cmd(message: Message):
    """Привязать клан к чату. В группе — автоматически, в личке — нужен ID."""
    from config import bot as _bot
    user_id  = message.from_user.id
    clan     = get_user_clan(user_id)
    if not clan:
        await message.answer("❌ Вы не состоите в клане.", parse_mode="HTML")
        return
    role = _get_role(clan, user_id)
    if role not in ("owner", "deputy"):
        await message.answer(
            "❌ Только лидер или заместитель клана может привязывать чат.",
            parse_mode="HTML",
        )
        return

    clan_name = clan.get("name", "Клан")
    parts     = message.text.strip().split()
    is_group  = message.chat.type in ("group", "supergroup")

    # ── Определяем целевой chat_id ────────────────────────────────
    if len(parts) >= 3:
        # Явно указан ID
        try:
            target_chat_id = int(parts[2])
        except ValueError:
            await message.answer(
                "❌ ID чата должен быть числом (может начинаться с −).",
                parse_mode="HTML",
            )
            return
    elif is_group:
        # Команда написана прямо в группе — привязываем этот чат
        target_chat_id = message.chat.id
    else:
        # Личка, ID не указан — показываем статус привязки
        current = clan.get("bound_chat_id")
        if current:
            # Пробуем получить имя чата
            try:
                chat_info = await _bot.get_chat(current)
                chat_title = chat_info.title or str(current)
            except Exception:
                chat_title = str(current)
            await message.answer(
                f"🔗 <b>Привязка клана «{clan_name}»</b>\n\n"
                f"✅ Привязан к чату: <b>{chat_title}</b>\n"
                f"<code>{current}</code>\n\n"
                f"Чтобы отвязать: <code>клан отвязать</code>\n"
                f"Чтобы привязать другой чат:\n"
                f"<code>клан чат [ID]</code>",
                parse_mode="HTML",
            )
        else:
            await message.answer(
                f"🔗 <b>Привязка клана «{clan_name}»</b>\n\n"
                f"Клан не привязан ни к одному чату.\n\n"
                f"<b>Как привязать:</b>\n"
                f"1. Добавь бота в нужную группу\n"
                f"2. Напиши там <code>клан чат</code> — чат привяжется автоматически\n"
                f"   или напиши <code>чат ид</code> и скопируй ID\n"
                f"3. Или вручную: <code>клан чат -1001234567890</code>",
                parse_mode="HTML",
            )
        return

    # ── Проверяем, не занят ли чат другим кланом ─────────────────
    existing = _find_clan_by_chat(target_chat_id)
    if existing and existing.get("id") != clan.get("id"):
        await message.answer(
            f"❌ Этот чат уже привязан к клану <b>{existing.get('name', '?')}</b>.\n"
            f"Сначала тот клан должен отвязаться: <code>клан отвязать</code>",
            parse_mode="HTML",
        )
        return

    # ── Проверяем доступность бота в чате ────────────────────────
    try:
        chat_info = await _bot.get_chat(target_chat_id)
        chat_title = chat_info.title or str(target_chat_id)
    except Exception:
        await message.answer(
            f"❌ Не удалось получить информацию о чате <code>{target_chat_id}</code>.\n"
            f"Убедись, что бот добавлен в группу.",
            parse_mode="HTML",
        )
        return

    # ── Сохраняем привязку ────────────────────────────────────────
    old_chat = clan.get("bound_chat_id")
    clan["bound_chat_id"] = target_chat_id
    save_clans()

    # Уведомление пользователю
    if is_group and target_chat_id == message.chat.id:
        # Ответили в группе — короткое подтверждение
        await message.answer(
            f"✅ Клан <b>{clan_name}</b> привязан к этому чату!\n"
            f"Все клановые уведомления (рейды, раздачи, сезон) будут приходить сюда.\n"
            f"Отвязать: <code>клан отвязать</code>",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"✅ Клан <b>{clan_name}</b> привязан к чату <b>{chat_title}</b>!\n"
            f"<code>{target_chat_id}</code>\n\n"
            f"Все клановые уведомления (рейды, раздачи, сезон) будут приходить туда.\n"
            f"Отвязать: <code>клан отвязать</code>",
            parse_mode="HTML",
        )

    # Уведомление в старый привязанный чат (если был другой)
    if old_chat and old_chat != target_chat_id:
        try:
            await _bot.send_message(
                old_chat,
                f"🔕 Клан <b>{clan_name}</b> отвязан от этого чата.\n"
                f"Уведомления теперь идут в другой чат.",
                parse_mode="HTML",
            )
        except Exception:
            pass

    # Уведомление в новый чат (только если команда была не в нём)
    if not (is_group and target_chat_id == message.chat.id):
        try:
            await _bot.send_message(
                target_chat_id,
                f"🔗 Клан <b>{clan_name}</b> привязан к этому чату!\n"
                f"Все клановые уведомления будут приходить сюда.",
                parse_mode="HTML",
            )
        except Exception:
            await message.answer(
                "⚠️ Привязка сохранена, но бот не смог отправить сообщение в чат.\n"
                "Убедись, что бот добавлен в группу и имеет права на отправку сообщений.",
                parse_mode="HTML",
            )


@router.message(F.text.lower().in_(["клан отвязать", "клан отвязать чат", "отвязать клан"]))
async def clan_unbind_chat_cmd(message: Message):
    """Отвязать клан от чата (лидер или заместитель)."""
    from config import bot as _bot
    user_id = message.from_user.id
    clan    = get_user_clan(user_id)
    if not clan:
        await message.answer("❌ Вы не состоите в клане.", parse_mode="HTML")
        return
    role = _get_role(clan, user_id)
    if role not in ("owner", "deputy"):
        await message.answer(
            "❌ Только лидер или заместитель клана может отвязывать чат.",
            parse_mode="HTML",
        )
        return

    old_chat = clan.get("bound_chat_id")
    if not old_chat:
        await message.answer("ℹ️ Клан не привязан ни к одному чату.", parse_mode="HTML")
        return

    clan_name = clan.get("name", "Клан")

    # Получаем название чата для отображения
    try:
        chat_info  = await _bot.get_chat(old_chat)
        chat_title = chat_info.title or str(old_chat)
    except Exception:
        chat_title = str(old_chat)

    clan["bound_chat_id"] = None
    save_clans()

    await message.answer(
        f"✅ Клан <b>{clan_name}</b> отвязан от чата <b>{chat_title}</b>.\n"
        f"Уведомления больше не будут туда приходить.",
        parse_mode="HTML",
    )

    # Уведомление в отвязанный чат
    try:
        await _bot.send_message(
            old_chat,
            f"🔕 Клан <b>{clan_name}</b> отвязан от этого чата.\n"
            f"Клановые уведомления сюда приходить не будут.",
            parse_mode="HTML",
        )
    except Exception:
        pass
