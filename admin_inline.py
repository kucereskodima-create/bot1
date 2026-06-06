import os
import json
import time
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from admin_roles import (
    get_role, has_permission, is_admin_any, grant_role, revoke_role,
    ROLE_FOUNDER, ROLE_ZAM_LD, ROLE_TECH_ADMIN, ROLE_ADMIN,
    ROLE_DESIGNER, ROLE_MODER, ROLE_FOLLOWER, ROLE_LABELS, founders,
    followers_list,
)
from admin_logs import log_action, get_logs, format_logs
import utils
from utils import (
    get_user, get_balance, update_balance, format_amount,
    find_user_by_identifier, save_user_data, clickable_name, safe_reply_kb,
)
from config import bot

router = Router()

WARPS_FILE       = os.path.join(os.path.dirname(__file__), "warps.json")
COMPLAINTS_FILE  = os.path.join(os.path.dirname(__file__), "complaints.json")
REPORTS_FILE     = os.path.join(os.path.dirname(__file__), "reports.json")
BOT_START_TIME   = time.time()


# ══════════════════════════════════════════════════════════════════
#  FSM States
# ══════════════════════════════════════════════════════════════════

class IpGiveState(StatesGroup):
    waiting_user   = State()
    waiting_type   = State()
    waiting_amount = State()

class IpTakeState(StatesGroup):
    waiting_user   = State()
    waiting_type   = State()
    waiting_amount = State()

class IpBanState(StatesGroup):
    waiting_user   = State()
    waiting_dur    = State()
    waiting_reason = State()

class IpUnbanState(StatesGroup):
    waiting_user = State()

class IpMuteState(StatesGroup):
    waiting_user   = State()
    waiting_dur    = State()
    waiting_reason = State()

class IpUnmuteState(StatesGroup):
    waiting_user = State()

class IpWarnState(StatesGroup):
    waiting_user   = State()
    waiting_reason = State()

class IpUnwarnState(StatesGroup):
    waiting_user = State()

class IpWarpState(StatesGroup):
    waiting_user  = State()
    waiting_point = State()

class IpUnwarpState(StatesGroup):
    waiting_user = State()

class IpDbWipeState(StatesGroup):
    waiting_confirm = State()

class IpGrantRoleState(StatesGroup):
    waiting_user = State()
    waiting_role = State()

class IpRevokeRoleState(StatesGroup):
    waiting_user = State()

class IpComplaintReplyState(StatesGroup):
    waiting_text = State()


# ══════════════════════════════════════════════════════════════════
#  Warp helpers
# ══════════════════════════════════════════════════════════════════

def _load_warps() -> dict:
    if os.path.exists(WARPS_FILE):
        try:
            with open(WARPS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_warps(data: dict):
    with open(WARPS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _load_complaints() -> dict:
    if os.path.exists(COMPLAINTS_FILE):
        try:
            with open(COMPLAINTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_complaints(data: dict):
    with open(COMPLAINTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _load_reports() -> dict:
    if os.path.exists(REPORTS_FILE):
        try:
            with open(REPORTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_reports(data: dict):
    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _load_bans() -> dict:
    bans_file = os.path.join(os.path.dirname(__file__), "admin_bans.json")
    if os.path.exists(bans_file):
        try:
            with open(bans_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_bans(data: dict):
    bans_file = os.path.join(os.path.dirname(__file__), "admin_bans.json")
    with open(bans_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _load_mutes() -> dict:
    mutes_file = os.path.join(os.path.dirname(__file__), "admin_mutes.json")
    if os.path.exists(mutes_file):
        try:
            with open(mutes_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_mutes(data: dict):
    mutes_file = os.path.join(os.path.dirname(__file__), "admin_mutes.json")
    with open(mutes_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════
#  Inline panel keyboards per role
# ══════════════════════════════════════════════════════════════════

_CLOSE_ROW = [InlineKeyboardButton(text="✖️ Закрыть панель", callback_data="ip_close")]

def _founder_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Выдать",       callback_data="ip_give"),
         InlineKeyboardButton(text="💸 Забрать",      callback_data="ip_take")],
        [InlineKeyboardButton(text="🗄 База данных",  callback_data="ip_db"),
         InlineKeyboardButton(text="🚫 Бан",          callback_data="ip_ban")],
        [InlineKeyboardButton(text="🔓 Разбан",       callback_data="ip_unban"),
         InlineKeyboardButton(text="🔇 Мут",          callback_data="ip_mute")],
        [InlineKeyboardButton(text="🔊 Размут",       callback_data="ip_unmute"),
         InlineKeyboardButton(text="⚠️ Варн",         callback_data="ip_warn")],
        [InlineKeyboardButton(text="✅ Снять варн",   callback_data="ip_unwarn"),
         InlineKeyboardButton(text="🌀 Варп",         callback_data="ip_warp")],
        [InlineKeyboardButton(text="❌ Снять варп",   callback_data="ip_unwarp"),
         InlineKeyboardButton(text="📜 Логи",         callback_data="ip_logs")],
        [InlineKeyboardButton(text="🛡 Управление",   callback_data="ip_admins"),
         InlineKeyboardButton(text="📨 Жалобы",       callback_data="ip_complaints")],
        [InlineKeyboardButton(text="📋 Репорты",      callback_data="ip_reports"),
         InlineKeyboardButton(text="⚙️ Настройки",    callback_data="ip_settings")],
        [_CLOSE_ROW[0]],
    ])

def _zam_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Выдать",       callback_data="ip_give"),
         InlineKeyboardButton(text="💸 Забрать",      callback_data="ip_take")],
        [InlineKeyboardButton(text="🚫 Бан",          callback_data="ip_ban"),
         InlineKeyboardButton(text="🔓 Разбан",       callback_data="ip_unban")],
        [InlineKeyboardButton(text="🔇 Мут",          callback_data="ip_mute"),
         InlineKeyboardButton(text="🔊 Размут",       callback_data="ip_unmute")],
        [InlineKeyboardButton(text="⚠️ Варн",         callback_data="ip_warn"),
         InlineKeyboardButton(text="✅ Снять варн",   callback_data="ip_unwarn")],
        [InlineKeyboardButton(text="🌀 Варп",         callback_data="ip_warp"),
         InlineKeyboardButton(text="📜 Логи",         callback_data="ip_logs")],
        [InlineKeyboardButton(text="🛡 Управление",   callback_data="ip_admins"),
         InlineKeyboardButton(text="📨 Жалобы",       callback_data="ip_complaints")],
        [InlineKeyboardButton(text="📋 Репорты",      callback_data="ip_reports")],
        [_CLOSE_ROW[0]],
    ])

def _tech_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Выдать",       callback_data="ip_give"),
         InlineKeyboardButton(text="🗄 База данных",  callback_data="ip_db")],
        [InlineKeyboardButton(text="📜 Логи",         callback_data="ip_logs"),
         InlineKeyboardButton(text="📋 Репорты",      callback_data="ip_reports")],
        [InlineKeyboardButton(text="⚙️ Настройки бота", callback_data="ip_settings"),
         InlineKeyboardButton(text="🔒 Защита",       callback_data="ip_protection")],
        [_CLOSE_ROW[0]],
    ])

def _admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Выдать",       callback_data="ip_give"),
         InlineKeyboardButton(text="🚫 Бан",          callback_data="ip_ban")],
        [InlineKeyboardButton(text="🔓 Разбан",       callback_data="ip_unban"),
         InlineKeyboardButton(text="🔇 Мут",          callback_data="ip_mute")],
        [InlineKeyboardButton(text="🔊 Размут",       callback_data="ip_unmute"),
         InlineKeyboardButton(text="⚠️ Варн",         callback_data="ip_warn")],
        [InlineKeyboardButton(text="✅ Снять варн",   callback_data="ip_unwarn"),
         InlineKeyboardButton(text="🌀 Варп",         callback_data="ip_warp")],
        [InlineKeyboardButton(text="❌ Снять варп",   callback_data="ip_unwarp"),
         InlineKeyboardButton(text="📨 Жалобы",       callback_data="ip_complaints")],
        [InlineKeyboardButton(text="📋 Репорты",      callback_data="ip_reports")],
        [_CLOSE_ROW[0]],
    ])

def _designer_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Редактор текстов",  callback_data="ip_edit_texts"),
         InlineKeyboardButton(text="😊 Редактор эмодзи",   callback_data="ip_edit_emoji")],
        [InlineKeyboardButton(text="📝 Сообщения бота",    callback_data="ip_bot_msgs"),
         InlineKeyboardButton(text="🎭 Стиль интерфейса",  callback_data="ip_style")],
        [InlineKeyboardButton(text="📋 Репорты",           callback_data="ip_reports")],
        [_CLOSE_ROW[0]],
    ])

def _moder_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔇 Мут",          callback_data="ip_mute"),
         InlineKeyboardButton(text="🔊 Размут",       callback_data="ip_unmute")],
        [InlineKeyboardButton(text="⚠️ Варн",         callback_data="ip_warn"),
         InlineKeyboardButton(text="✅ Снять варн",   callback_data="ip_unwarn")],
        [InlineKeyboardButton(text="📨 Жалобы",       callback_data="ip_complaints"),
         InlineKeyboardButton(text="📋 Репорты",      callback_data="ip_reports")],
        [_CLOSE_ROW[0]],
    ])

def _follower_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Репорты",      callback_data="ip_reports"),
         InlineKeyboardButton(text="ℹ️ Информация",   callback_data="ip_info")],
        [_CLOSE_ROW[0]],
    ])

def _get_panel_kb(role: str) -> InlineKeyboardMarkup:
    return {
        ROLE_FOUNDER:    _founder_kb,
        ROLE_ZAM_LD:     _zam_kb,
        ROLE_TECH_ADMIN: _tech_kb,
        ROLE_ADMIN:      _admin_kb,
        ROLE_DESIGNER:   _designer_kb,
        ROLE_MODER:      _moder_kb,
        ROLE_FOLLOWER:   _follower_kb,
    }.get(role, _admin_kb)()

def _role_header(role: str) -> str:
    headers = {
        ROLE_FOUNDER:    "👑 ПАНЕЛЬ ОСНОВАТЕЛЯ",
        ROLE_ZAM_LD:     "⭐ ПАНЕЛЬ ЗАМА",
        ROLE_TECH_ADMIN: "🔧 ПАНЕЛЬ ТЕХ АДМИНА",
        ROLE_ADMIN:      "👮 ПАНЕЛЬ АДМИНА",
        ROLE_DESIGNER:   "🎨 ПАНЕЛЬ ДИЗАЙНЕРА",
        ROLE_MODER:      "🛡 ПАНЕЛЬ МОДЕРА",
        ROLE_FOLLOWER:   "👁 ПАНЕЛЬ ФОЛЕРА",
    }
    return headers.get(role, "⚙️ ПАНЕЛЬ")

_CANCEL_KB = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="❌ Отмена", callback_data="ip_cancel")
]])

def _dur_ban_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 час",    callback_data="ip_ban_dur:1h"),
         InlineKeyboardButton(text="1 день",   callback_data="ip_ban_dur:1d")],
        [InlineKeyboardButton(text="7 дней",   callback_data="ip_ban_dur:7d"),
         InlineKeyboardButton(text="30 дней",  callback_data="ip_ban_dur:30d")],
        [InlineKeyboardButton(text="♾ Навсегда", callback_data="ip_ban_dur:perm")],
        [InlineKeyboardButton(text="❌ Отмена",   callback_data="ip_cancel")],
    ])

def _dur_mute_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 минут",  callback_data="ip_mute_dur:10m"),
         InlineKeyboardButton(text="1 час",     callback_data="ip_mute_dur:1h")],
        [InlineKeyboardButton(text="1 день",    callback_data="ip_mute_dur:1d"),
         InlineKeyboardButton(text="♾ Навсегда", callback_data="ip_mute_dur:perm")],
        [InlineKeyboardButton(text="❌ Отмена",   callback_data="ip_cancel")],
    ])

def _give_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Деньги",         callback_data="ip_give_t:money"),
         InlineKeyboardButton(text="🏦 Банк",           callback_data="ip_give_t:bank")],
        [InlineKeyboardButton(text="₿ Битки",           callback_data="ip_give_t:btc"),
         InlineKeyboardButton(text="💎 Донат (DC)",     callback_data="ip_give_t:dc")],
        [InlineKeyboardButton(text="⭐ Уровень",        callback_data="ip_give_t:level"),
         InlineKeyboardButton(text="🏰 Клан лвл",      callback_data="ip_give_t:clan_level")],
        [InlineKeyboardButton(text="🏠 Дом",            callback_data="ip_give_t:house"),
         InlineKeyboardButton(text="🚗 Авто",           callback_data="ip_give_t:car")],
        [InlineKeyboardButton(text="🏢 Бизнес",         callback_data="ip_give_t:biz"),
         InlineKeyboardButton(text="⛏ Ферма",          callback_data="ip_give_t:farm")],
        [InlineKeyboardButton(text="🎓 КазНУ",          callback_data="ip_give_t:kaznu")],
        [InlineKeyboardButton(text="❌ Отмена",         callback_data="ip_cancel")],
    ])

def _take_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Деньги",         callback_data="ip_take_t:money"),
         InlineKeyboardButton(text="🏦 Банк",           callback_data="ip_take_t:bank")],
        [InlineKeyboardButton(text="₿ Битки",           callback_data="ip_take_t:btc"),
         InlineKeyboardButton(text="💎 Донат (DC)",     callback_data="ip_take_t:dc")],
        [InlineKeyboardButton(text="⭐ Уровень",        callback_data="ip_take_t:level"),
         InlineKeyboardButton(text="🏰 Клан лвл",      callback_data="ip_take_t:clan_level")],
        [InlineKeyboardButton(text="🏠 Дом",            callback_data="ip_take_t:house"),
         InlineKeyboardButton(text="🚗 Авто",           callback_data="ip_take_t:car")],
        [InlineKeyboardButton(text="🏢 Бизнес",         callback_data="ip_take_t:biz"),
         InlineKeyboardButton(text="⛏ Ферма",          callback_data="ip_take_t:farm")],
        [InlineKeyboardButton(text="🎓 КазНУ",          callback_data="ip_take_t:kaznu")],
        [InlineKeyboardButton(text="❌ Отмена",         callback_data="ip_cancel")],
    ])

def _role_assign_kb(my_role: str) -> InlineKeyboardMarkup:
    rows = []
    grantable = []
    if my_role == ROLE_FOUNDER:
        grantable = [ROLE_ZAM_LD, ROLE_TECH_ADMIN, ROLE_ADMIN, ROLE_DESIGNER, ROLE_MODER, ROLE_FOLLOWER]
    elif my_role == ROLE_ZAM_LD:
        grantable = [ROLE_TECH_ADMIN, ROLE_ADMIN, ROLE_DESIGNER, ROLE_MODER, ROLE_FOLLOWER]
    for r in grantable:
        rows.append([InlineKeyboardButton(
            text=ROLE_LABELS[r], callback_data=f"ip_grant_role:{r}"
        )])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="ip_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _wipe_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить",   callback_data="ip_db_wipe_confirm"),
         InlineKeyboardButton(text="❌ Отмена",        callback_data="ip_cancel")],
    ])

def _now_str() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


# ══════════════════════════════════════════════════════════════════
#  Main panel command — "админ" / "admin"
# ══════════════════════════════════════════════════════════════════

def _panel_text(role: str) -> str:
    label = ROLE_LABELS.get(role, "—")
    return (
        f"╔══════════════════════╗\n"
        f"   {_role_header(role)}\n"
        f"╚══════════════════════╝\n\n"
        f"👤 Ранг: <b>{label}</b>\n"
        f"🕐 Время входа: <b>{_now_str()}</b>\n\n"
        f"<i>Выберите действие:</i>"
    )


@router.message(F.text.lower().in_({"админка", "адми", "/админка", "/адми"}))
async def cmd_admin_panel(message: Message):
    uid = message.from_user.id
    if not is_admin_any(uid):
        await message.answer("⛔ У вас нет доступа к панели администрации.")
        return
    role = get_role(uid)
    await message.answer(_panel_text(role), parse_mode="HTML", reply_markup=_get_panel_kb(role))


@router.callback_query(F.data == "ip_close")
async def cb_ip_close(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer("Панель закрыта")


@router.callback_query(F.data == "ip_back")
async def cb_ip_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    uid  = callback.from_user.id
    role = get_role(uid)
    try:
        await callback.message.edit_text(
            _panel_text(role), parse_mode="HTML", reply_markup=_get_panel_kb(role)
        )
    except Exception:
        await callback.message.answer(
            _panel_text(role), parse_mode="HTML", reply_markup=_get_panel_kb(role)
        )
    await callback.answer()


@router.callback_query(F.data == "ip_cancel")
async def cb_ip_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    uid  = callback.from_user.id
    role = get_role(uid)
    try:
        await callback.message.edit_text(
            _panel_text(role), parse_mode="HTML", reply_markup=_get_panel_kb(role)
        )
    except Exception:
        await callback.message.answer("❌ Действие отменено.")
    await callback.answer()


# ══════════════════════════════════════════════════════════════════
#  ВЫДАТЬ
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_give")
async def cb_ip_give(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "give_currency"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.set_state(IpGiveState.waiting_user)
    await callback.message.edit_text(
        "💵 <b>ВЫДАТЬ</b>\n\nВведите ID, игровой ID или @юзернейм игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


@router.message(IpGiveState.waiting_user)
async def ip_give_user(message: Message, state: FSMContext):
    uid, rec = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not rec:
        await message.answer("❌ Игрок не найден. Попробуйте снова.")
        return
    await state.update_data(recipient_id=uid, recipient_name=rec.get("name", "Без имени"))
    await state.set_state(IpGiveState.waiting_type)
    await message.answer(
        f"✅ Найден: <b>{rec.get('name','?')}</b>\n\nЧто выдать?",
        parse_mode="HTML", reply_markup=_give_type_kb()
    )


def _biz_picker_kb(rid: int, rname: str, action: str) -> InlineKeyboardMarkup:
    from business_shop import BUSINESSES
    rows = []
    for i, biz in enumerate(BUSINESSES):
        rows.append([InlineKeyboardButton(
            text=f"{i+1}. {biz['name']}",
            callback_data=f"ip_{action}_biz:{rid}:{i}"
        )])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="ip_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _house_picker_kb(rid: int, rname: str, action: str) -> InlineKeyboardMarkup:
    from house_shop import SHOP_HOUSES, HOUSE_KEYS
    rows = []
    for i, key in enumerate(HOUSE_KEYS):
        h = SHOP_HOUSES[key]
        rows.append([InlineKeyboardButton(
            text=f"{i+1}. {h['name']}",
            callback_data=f"ip_{action}_house:{rid}:{key}"
        )])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="ip_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _car_picker_kb(rid: int, rname: str, action: str) -> InlineKeyboardMarkup:
    from auto_shop import SHOP_CARS, CAR_KEYS
    rows = []
    for i, key in enumerate(CAR_KEYS):
        c = SHOP_CARS[key]
        rows.append([InlineKeyboardButton(
            text=f"{i+1}. {c['name']}",
            callback_data=f"ip_{action}_car:{rid}:{key}"
        )])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="ip_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("ip_give_t:"), IpGiveState.waiting_type)
async def ip_give_type(callback: CallbackQuery, state: FSMContext):
    gtype = callback.data.split(":", 1)[1]
    data  = await state.get_data()
    name  = data.get("recipient_name", "?")
    rid   = data.get("recipient_id")
    await state.update_data(give_type=gtype)

    # Для biz/house/car — показываем inline-список, не ждём текст
    if gtype == "biz":
        await state.clear()
        await callback.message.edit_text(
            f"🏢 <b>Выдать бизнес → {name}</b>\n\nВыберите бизнес:",
            parse_mode="HTML", reply_markup=_biz_picker_kb(rid, name, "give")
        )
        await callback.answer()
        return

    if gtype == "house":
        await state.clear()
        await callback.message.edit_text(
            f"🏠 <b>Выдать дом → {name}</b>\n\nВыберите дом:",
            parse_mode="HTML", reply_markup=_house_picker_kb(rid, name, "give")
        )
        await callback.answer()
        return

    if gtype == "car":
        await state.clear()
        await callback.message.edit_text(
            f"🚗 <b>Выдать авто → {name}</b>\n\nВыберите авто:",
            parse_mode="HTML", reply_markup=_car_picker_kb(rid, name, "give")
        )
        await callback.answer()
        return

    type_prompts = {
        "money":      f"💵 <b>Деньги → {name}</b>\n\nВведите сумму (напр. 1000, 10к, 1м):",
        "bank":       f"🏦 <b>Банк → {name}</b>\n\nВведите сумму для пополнения банка:",
        "btc":        f"₿ <b>Битки → {name}</b>\n\nВведите количество BTC (напр. 0.5):",
        "dc":         f"💎 <b>DC (донат) → {name}</b>\n\nВведите количество DC:",
        "level":      f"⭐ <b>Уровень → {name}</b>\n\nВведите новый уровень (1–100):",
        "clan_level": f"🏰 <b>Клан лвл → {name}</b>\n\nВведите количество уровней для добавления:",
        "farm":       f"⛏ <b>Ферма → {name}</b>\n\nВведите уровень фермы (1–10):",
        "kaznu":      f"🎓 <b>КазНУ → {name}</b>\n\nВведите 1 для подтверждения:",
    }
    await state.set_state(IpGiveState.waiting_amount)
    await callback.message.edit_text(
        type_prompts.get(gtype, f"? → {name}\n\nВведите значение:"),
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


# ── Callback: выдать бизнес/дом/авто по ID ───────────────────────────────────

@router.callback_query(F.data.startswith("ip_give_biz:"))
async def cb_give_biz(callback: CallbackQuery):
    parts = callback.data.split(":")
    rid, biz_idx = int(parts[1]), int(parts[2])
    u = get_user(rid)
    rname = u.get("name", "?")
    cl    = u.get("clickable_name", True)
    from business_shop import BUSINESSES
    biz = BUSINESSES[biz_idx]
    owned = u.get("businesses", [])
    if biz_idx in owned:
        await callback.answer("❌ У игрока уже есть этот бизнес.", show_alert=True)
        return
    owned.append(biz_idx)
    u["businesses"] = owned
    save_user_data()
    log_action(callback.from_user.id, callback.from_user.full_name, "give_biz", rid, biz["name"])
    my_role = get_role(callback.from_user.id)
    await callback.message.edit_text(
        f"✅ <b>Бизнес выдан</b>\n\n"
        f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
        f"🏢 Бизнес: <b>{biz['name']}</b>\n"
        f"👮 Кто выдал: <b>{callback.from_user.full_name}</b>\n\n"
        + _panel_text(my_role),
        parse_mode="HTML", reply_markup=_get_panel_kb(my_role)
    )
    try:
        await bot.send_message(rid, f"🏢 Вам выдан бизнес: <b>{biz['name']}</b>!", parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("ip_give_house:"))
async def cb_give_house(callback: CallbackQuery):
    parts = callback.data.split(":")
    rid, house_key = int(parts[1]), parts[2]
    u = get_user(rid)
    rname = u.get("name", "?")
    cl    = u.get("clickable_name", True)
    from house_shop import SHOP_HOUSES
    if house_key not in SHOP_HOUSES:
        await callback.answer("❌ Дом не найден.", show_alert=True)
        return
    h = SHOP_HOUSES[house_key]
    u["shop_house"] = house_key
    save_user_data()
    log_action(callback.from_user.id, callback.from_user.full_name, "give_house", rid, h["name"])
    my_role = get_role(callback.from_user.id)
    await callback.message.edit_text(
        f"✅ <b>Дом выдан</b>\n\n"
        f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
        f"🏠 Дом: <b>{h['name']}</b>\n"
        f"👮 Кто выдал: <b>{callback.from_user.full_name}</b>\n\n"
        + _panel_text(my_role),
        parse_mode="HTML", reply_markup=_get_panel_kb(my_role)
    )
    try:
        await bot.send_message(rid, f"🏠 Вам выдан дом: <b>{h['name']}</b>!", parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("ip_give_car:"))
async def cb_give_car(callback: CallbackQuery):
    parts = callback.data.split(":")
    rid, car_key = int(parts[1]), parts[2]
    u = get_user(rid)
    rname = u.get("name", "?")
    cl    = u.get("clickable_name", True)
    from auto_shop import SHOP_CARS
    if car_key not in SHOP_CARS:
        await callback.answer("❌ Авто не найдено.", show_alert=True)
        return
    c = SHOP_CARS[car_key]
    u["shop_car"] = car_key
    save_user_data()
    log_action(callback.from_user.id, callback.from_user.full_name, "give_car", rid, c["name"])
    my_role = get_role(callback.from_user.id)
    await callback.message.edit_text(
        f"✅ <b>Авто выдано</b>\n\n"
        f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
        f"🚗 Авто: <b>{c['name']}</b>\n"
        f"👮 Кто выдал: <b>{callback.from_user.full_name}</b>\n\n"
        + _panel_text(my_role),
        parse_mode="HTML", reply_markup=_get_panel_kb(my_role)
    )
    try:
        await bot.send_message(rid, f"🚗 Вам выдано авто: <b>{c['name']}</b>!", parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.message(IpGiveState.waiting_amount)
async def ip_give_amount(message: Message, state: FSMContext):
    from utils import parse_k
    data   = await state.get_data()
    rid    = data["recipient_id"]
    rname  = data["recipient_name"]
    gtype  = data["give_type"]
    admin_id   = message.from_user.id
    admin_name = message.from_user.full_name
    u = get_user(rid)
    cl = u.get("clickable_name", True)
    txt = message.text.strip()

    await state.clear()

    if gtype == "money":
        amount = parse_k(txt)
        if not amount or amount <= 0:
            await message.answer("❌ Неверная сумма.")
            return
        update_balance(rid, get_balance(rid) + amount)
        log_action(admin_id, admin_name, "give_money", rid, f"+{format_amount(amount)}$")
        await message.answer(
            f"✅ <b>Выдача выполнена</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"💵 Выдано: <b>{format_amount(amount)}$</b>\n"
            f"👮 Кто выдал: <b>{admin_name}</b>\n"
            f"🕐 Дата: <b>{_now_str()}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"💵 Вам выдали <b>{format_amount(amount)}$</b> от администратора.", parse_mode="HTML")
        except Exception:
            pass

    elif gtype == "btc":
        try:
            amount = round(float(txt.replace(",", ".")), 6)
        except ValueError:
            await message.answer("❌ Неверное количество BTC.")
            return
        from farm import get_farm
        farm = get_farm(rid)
        farm["btc_balance"] = round(farm.get("btc_balance", 0.0) + amount, 6)
        save_user_data()
        log_action(admin_id, admin_name, "give_btc", rid, f"+{amount} BTC")
        await message.answer(
            f"✅ <b>Выдача BTC</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"₿ Выдано: <b>{amount} BTC</b>\n"
            f"👮 Кто выдал: <b>{admin_name}</b>\n"
            f"🕐 Дата: <b>{_now_str()}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"₿ Вам выдали <b>{amount} BTC</b> от администратора.", parse_mode="HTML")
        except Exception:
            pass

    elif gtype == "dc":
        try:
            amount = int(txt)
        except ValueError:
            await message.answer("❌ Введите целое число DC.")
            return
        u["donate_coins"] = u.get("donate_coins", 0) + amount
        save_user_data()
        log_action(admin_id, admin_name, "give_dc", rid, f"+{amount} DC")
        await message.answer(
            f"✅ <b>Выдача DC</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"💎 Выдано: <b>{amount} DC</b>\n"
            f"👮 Кто выдал: <b>{admin_name}</b>\n"
            f"🕐 Дата: <b>{_now_str()}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"💎 Вам выдали <b>{amount} DC</b> от администратора.", parse_mode="HTML")
        except Exception:
            pass

    elif gtype == "level":
        try:
            lvl = int(txt)
            if not (1 <= lvl <= 100):
                raise ValueError
        except ValueError:
            await message.answer("❌ Уровень должен быть от 1 до 100.")
            return
        old_lvl = u.get("level", 1)
        u["level"] = lvl
        u["experience"] = lvl * 100
        save_user_data()
        log_action(admin_id, admin_name, "give_level", rid, f"lvl {old_lvl} → {lvl}")
        await message.answer(
            f"✅ <b>Уровень установлен</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"⭐ Уровень: <b>{old_lvl} → {lvl}</b>\n"
            f"👮 Кто выдал: <b>{admin_name}</b>\n"
            f"🕐 Дата: <b>{_now_str()}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"⭐ Администратор установил ваш уровень <b>{lvl}</b>.", parse_mode="HTML")
        except Exception:
            pass

    elif gtype == "bank":
        amount = parse_k(txt)
        if not amount or amount <= 0:
            await message.answer("❌ Неверная сумма.")
            return
        u["user_bank"] = u.get("user_bank", 0) + amount
        save_user_data()
        log_action(admin_id, admin_name, "give_bank", rid, f"+{format_amount(amount)}$ в банк")
        await message.answer(
            f"✅ <b>Выдача в банк</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"🏦 Выдано: <b>{format_amount(amount)}$</b> в банк\n"
            f"👮 Кто выдал: <b>{admin_name}</b>\n"
            f"🕐 Дата: <b>{_now_str()}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"🏦 Вам выдали <b>{format_amount(amount)}$</b> на банковский счёт.", parse_mode="HTML")
        except Exception:
            pass

    elif gtype == "clan_level":
        try:
            lvl_add = int(txt)
            if lvl_add <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Введите положительное число уровней.")
            return
        try:
            from clans import get_user_clan, save_clans, clans_data, MAX_CLAN_LEVEL
            clan = get_user_clan(rid)
            if not clan:
                await message.answer("❌ Игрок не состоит в клане.")
                return
            old_lvl = clan.get("level", 1)
            new_lvl = min(old_lvl + lvl_add, MAX_CLAN_LEVEL)
            clan["level"] = new_lvl
            save_clans()
            log_action(admin_id, admin_name, "give_clan_level", rid, f"клан лвл {old_lvl} → {new_lvl}")
            await message.answer(
                f"✅ <b>Клан повышен</b>\n\n"
                f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
                f"🏰 Клан: <b>{clan.get('name','?')}</b>\n"
                f"⬆️ Уровень: <b>{old_lvl} → {new_lvl}</b>\n"
                f"👮 Кто выдал: <b>{admin_name}</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")

    elif gtype == "farm":
        try:
            lvl = int(txt)
            if not (1 <= lvl <= 10):
                raise ValueError
        except ValueError:
            await message.answer("❌ Уровень фермы от 1 до 10.")
            return
        from farm import get_farm
        farm = get_farm(rid)
        old_lvl = farm.get("farm_level", 0)
        farm["farm_level"] = lvl
        save_user_data()
        log_action(admin_id, admin_name, "give_farm", rid, f"ферма лвл {old_lvl} → {lvl}")
        await message.answer(
            f"✅ <b>Ферма выдана</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"⛏ Ферма: уровень <b>{old_lvl} → {lvl}</b>\n"
            f"👮 Кто выдал: <b>{admin_name}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"⛏ Администратор установил вашу ферму на уровень <b>{lvl}</b>.", parse_mode="HTML")
        except Exception:
            pass

    elif gtype == "kaznu":
        u["kaznu"] = u.get("kaznu", 0) + 1
        save_user_data()
        log_action(admin_id, admin_name, "give_kaznu", rid, "КазНУ")
        await message.answer(
            f"✅ <b>КазНУ выдан</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"🎓 КазНУ: <b>+1</b>\n"
            f"👮 Кто выдал: <b>{admin_name}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"🎓 Вам выдан диплом КазНУ!", parse_mode="HTML")
        except Exception:
            pass

    role = get_role(admin_id)
    try:
        await message.answer(_panel_text(role), parse_mode="HTML", reply_markup=_get_panel_kb(role))
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  ЗАБРАТЬ
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_take")
async def cb_ip_take(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "give_currency"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.set_state(IpTakeState.waiting_user)
    await callback.message.edit_text(
        "💸 <b>ЗАБРАТЬ</b>\n\nВведите ID, игровой ID или @юзернейм игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


@router.message(IpTakeState.waiting_user)
async def ip_take_user(message: Message, state: FSMContext):
    uid, rec = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not rec:
        await message.answer("❌ Игрок не найден. Попробуйте снова.")
        return
    await state.update_data(recipient_id=uid, recipient_name=rec.get("name", "Без имени"))
    await state.set_state(IpTakeState.waiting_type)
    await message.answer(
        f"✅ Найден: <b>{rec.get('name','?')}</b>\n\nЧто забрать?",
        parse_mode="HTML", reply_markup=_take_type_kb()
    )


@router.callback_query(F.data.startswith("ip_take_t:"), IpTakeState.waiting_type)
async def ip_take_type(callback: CallbackQuery, state: FSMContext):
    ttype = callback.data.split(":", 1)[1]
    data  = await state.get_data()
    name  = data.get("recipient_name", "?")
    rid   = data["recipient_id"]
    await state.update_data(take_type=ttype)
    await state.set_state(IpTakeState.waiting_amount)

    if ttype == "level":
        u = get_user(rid)
        old_lvl = u.get("level", 1)
        u["level"] = max(1, old_lvl - 1)
        u["experience"] = u["level"] * 100
        save_user_data()
        await state.clear()
        log_action(callback.from_user.id, callback.from_user.full_name, "take_level", rid, f"lvl {old_lvl} → {u['level']}")
        await callback.message.edit_text(
            f"✅ <b>Уровень понижен</b>\n\n"
            f"👤 Игрок: <b>{name}</b>\n"
            f"⭐ Уровень: <b>{old_lvl} → {u['level']}</b>\n"
            f"🕐 Дата: <b>{_now_str()}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"📉 Администратор понизил ваш уровень до <b>{u['level']}</b>.", parse_mode="HTML")
        except Exception:
            pass
        await callback.answer()
        return

    if ttype == "clan_level":
        try:
            from clans import get_user_clan, save_clans, MAX_CLAN_LEVEL
            clan = get_user_clan(rid)
            if not clan:
                await callback.answer("❌ Игрок не в клане.", show_alert=True)
                await state.clear()
                return
            old_lvl = clan.get("level", 1)
            clan["level"] = max(1, old_lvl - 1)
            save_clans()
            log_action(callback.from_user.id, callback.from_user.full_name, "take_clan_level", rid, f"клан лвл {old_lvl} → {clan['level']}")
            await state.clear()
            await callback.message.edit_text(
                f"✅ <b>Клан понижен</b>\n\n"
                f"👤 Игрок: <b>{name}</b>\n"
                f"🏰 Клан: <b>{clan.get('name','?')}</b>\n"
                f"⬇️ Уровень: <b>{old_lvl} → {clan['level']}</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка: {e}", parse_mode="HTML")
        await callback.answer()
        return

    if ttype == "kaznu":
        u = get_user(rid)
        cur = u.get("kaznu", 0)
        if cur <= 0:
            await callback.answer("❌ У игрока нет КазНУ.", show_alert=True)
            await state.clear()
            return
        u["kaznu"] = 0
        save_user_data()
        log_action(callback.from_user.id, callback.from_user.full_name, "take_kaznu", rid, "КазНУ")
        await state.clear()
        await callback.message.edit_text(
            f"✅ <b>КазНУ забран</b>\n\n👤 Игрок: <b>{name}</b>\n🎓 КазНУ сброшен до 0",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    # Для biz/house/car — показываем inline-список
    if ttype == "biz":
        u = get_user(rid)
        owned = u.get("businesses", [])
        if not owned:
            await state.clear()
            await callback.answer("❌ У игрока нет бизнесов.", show_alert=True)
            return
        from business_shop import BUSINESSES
        rows = []
        for biz_idx in owned:
            if 0 <= biz_idx < len(BUSINESSES):
                biz = BUSINESSES[biz_idx]
                rows.append([InlineKeyboardButton(
                    text=f"❌ {biz_idx+1}. {biz['name']}",
                    callback_data=f"ip_take_biz:{rid}:{biz_idx}"
                )])
        rows.append([InlineKeyboardButton(text="Отмена", callback_data="ip_cancel")])
        await state.clear()
        await callback.message.edit_text(
            f"🏢 <b>Забрать бизнес у {name}</b>\n\nВыберите бизнес для изъятия:",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        await callback.answer()
        return

    if ttype == "house":
        u = get_user(rid)
        house_key = u.get("shop_house")
        don_house  = None
        try:
            from donate import get_donate_user_data
            don_data = get_donate_user_data(rid)
            don_house = don_data.get("house")
        except Exception:
            pass
        if not house_key and not don_house:
            await state.clear()
            await callback.answer("❌ У игрока нет дома.", show_alert=True)
            return
        rows = []
        if house_key:
            from house_shop import SHOP_HOUSES
            h = SHOP_HOUSES.get(house_key, {})
            rows.append([InlineKeyboardButton(
                text=f"❌ {h.get('name', house_key)} (магазин)",
                callback_data=f"ip_take_house:{rid}:shop"
            )])
        if don_house:
            rows.append([InlineKeyboardButton(
                text=f"❌ {don_house} (донат)",
                callback_data=f"ip_take_house:{rid}:donate"
            )])
        rows.append([InlineKeyboardButton(text="Отмена", callback_data="ip_cancel")])
        await state.clear()
        await callback.message.edit_text(
            f"🏠 <b>Забрать дом у {name}</b>\n\nВыберите дом для изъятия:",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        await callback.answer()
        return

    if ttype == "car":
        u = get_user(rid)
        car_key = u.get("shop_car")
        don_car  = None
        try:
            from donate import get_donate_user_data
            don_data = get_donate_user_data(rid)
            don_car = don_data.get("car")
        except Exception:
            pass
        if not car_key and not don_car:
            await state.clear()
            await callback.answer("❌ У игрока нет авто.", show_alert=True)
            return
        rows = []
        if car_key:
            from auto_shop import SHOP_CARS
            c = SHOP_CARS.get(car_key, {})
            rows.append([InlineKeyboardButton(
                text=f"❌ {c.get('name', car_key)} (магазин)",
                callback_data=f"ip_take_car:{rid}:shop"
            )])
        if don_car:
            rows.append([InlineKeyboardButton(
                text=f"❌ {don_car} (донат)",
                callback_data=f"ip_take_car:{rid}:donate"
            )])
        rows.append([InlineKeyboardButton(text="Отмена", callback_data="ip_cancel")])
        await state.clear()
        await callback.message.edit_text(
            f"🚗 <b>Забрать авто у {name}</b>\n\nВыберите авто для изъятия:",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        await callback.answer()
        return

    type_prompts = {
        "money": f"💵 <b>Забрать деньги у {name}</b>\n\nВведите сумму (или <code>все</code>):",
        "bank":  f"🏦 <b>Забрать из банка у {name}</b>\n\nВведите сумму (или <code>все</code>):",
        "btc":   f"₿ <b>Забрать BTC у {name}</b>\n\nВведите количество (или <code>все</code>):",
        "dc":    f"💎 <b>Забрать DC у {name}</b>\n\nВведите количество (или <code>все</code>):",
        "farm":  f"⛏ <b>Забрать ферму у {name}</b>\n\nВведите уровень фермы (1–10) или 0 для сброса:",
    }
    await callback.message.edit_text(
        type_prompts.get(ttype, f"? — забрать у <b>{name}</b>\n\nВведите значение:"),
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


# ── Callback: забрать бизнес/дом/авто ────────────────────────────────────────

@router.callback_query(F.data.startswith("ip_take_biz:"))
async def cb_take_biz(callback: CallbackQuery):
    parts = callback.data.split(":")
    rid, biz_idx = int(parts[1]), int(parts[2])
    u = get_user(rid)
    rname = u.get("name", "?")
    cl    = u.get("clickable_name", True)
    from business_shop import BUSINESSES
    owned = u.get("businesses", [])
    if biz_idx not in owned:
        await callback.answer("❌ Бизнес уже отсутствует.", show_alert=True)
        return
    owned.remove(biz_idx)
    u["businesses"] = owned
    # Также убираем уровень бизнеса если есть
    u.get("biz_levels", {}).pop(str(biz_idx), None)
    save_user_data()
    biz = BUSINESSES[biz_idx]
    log_action(callback.from_user.id, callback.from_user.full_name, "take_biz", rid, biz["name"])
    my_role = get_role(callback.from_user.id)
    await callback.message.edit_text(
        f"✅ <b>Бизнес изъят</b>\n\n"
        f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
        f"🏢 Бизнес: <b>{biz['name']}</b>\n"
        f"👮 Кто забрал: <b>{callback.from_user.full_name}</b>\n\n"
        + _panel_text(my_role),
        parse_mode="HTML", reply_markup=_get_panel_kb(my_role)
    )
    try:
        await bot.send_message(rid, f"🏢 Администратор изъял ваш бизнес: <b>{biz['name']}</b>.", parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("ip_take_house:"))
async def cb_take_house(callback: CallbackQuery):
    parts = callback.data.split(":")
    rid, source = int(parts[1]), parts[2]
    u = get_user(rid)
    rname = u.get("name", "?")
    cl    = u.get("clickable_name", True)
    house_name = "?"
    if source == "shop":
        from house_shop import SHOP_HOUSES
        key = u.get("shop_house")
        if key and key in SHOP_HOUSES:
            house_name = SHOP_HOUSES[key]["name"]
        u.pop("shop_house", None)
        save_user_data()
    elif source == "donate":
        try:
            from donate import get_donate_user_data
            don_data = get_donate_user_data(rid)
            house_name = don_data.get("house", "Донат-дом")
            don_data["house"] = None
            save_user_data()
        except Exception:
            pass
    log_action(callback.from_user.id, callback.from_user.full_name, "take_house", rid, house_name)
    my_role = get_role(callback.from_user.id)
    await callback.message.edit_text(
        f"✅ <b>Дом изъят</b>\n\n"
        f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
        f"🏠 Дом: <b>{house_name}</b>\n"
        f"👮 Кто забрал: <b>{callback.from_user.full_name}</b>\n\n"
        + _panel_text(my_role),
        parse_mode="HTML", reply_markup=_get_panel_kb(my_role)
    )
    try:
        await bot.send_message(rid, f"🏠 Администратор изъял ваш дом: <b>{house_name}</b>.", parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("ip_take_car:"))
async def cb_take_car(callback: CallbackQuery):
    parts = callback.data.split(":")
    rid, source = int(parts[1]), parts[2]
    u = get_user(rid)
    rname = u.get("name", "?")
    cl    = u.get("clickable_name", True)
    car_name = "?"
    if source == "shop":
        from auto_shop import SHOP_CARS
        key = u.get("shop_car")
        if key and key in SHOP_CARS:
            car_name = SHOP_CARS[key]["name"]
        u.pop("shop_car", None)
        save_user_data()
    elif source == "donate":
        try:
            from donate import get_donate_user_data
            don_data = get_donate_user_data(rid)
            car_name = don_data.get("car", "Донат-авто")
            don_data["car"] = None
            save_user_data()
        except Exception:
            pass
    log_action(callback.from_user.id, callback.from_user.full_name, "take_car", rid, car_name)
    my_role = get_role(callback.from_user.id)
    await callback.message.edit_text(
        f"✅ <b>Авто изъято</b>\n\n"
        f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
        f"🚗 Авто: <b>{car_name}</b>\n"
        f"👮 Кто забрал: <b>{callback.from_user.full_name}</b>\n\n"
        + _panel_text(my_role),
        parse_mode="HTML", reply_markup=_get_panel_kb(my_role)
    )
    try:
        await bot.send_message(rid, f"🚗 Администратор изъял ваше авто: <b>{car_name}</b>.", parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.message(IpTakeState.waiting_amount)
async def ip_take_amount(message: Message, state: FSMContext):
    from utils import parse_k
    data   = await state.get_data()
    rid    = data["recipient_id"]
    rname  = data["recipient_name"]
    ttype  = data["take_type"]
    admin_id   = message.from_user.id
    admin_name = message.from_user.full_name
    u = get_user(rid)
    cl = u.get("clickable_name", True)
    txt = message.text.strip().lower()
    await state.clear()

    if ttype == "money":
        cur = get_balance(rid)
        amount = cur if txt in ("все", "all") else parse_k(txt)
        if not amount or amount <= 0:
            await message.answer("❌ Неверная сумма.")
            return
        amount = min(amount, cur)
        update_balance(rid, cur - amount)
        log_action(admin_id, admin_name, "take_money", rid, f"-{format_amount(amount)}$")
        await message.answer(
            f"✅ <b>Деньги забраны</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"💵 Забрано: <b>{format_amount(amount)}$</b>\n"
            f"👮 Кто забрал: <b>{admin_name}</b>\n"
            f"🕐 Дата: <b>{_now_str()}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"💸 Администратор списал <b>{format_amount(amount)}$</b> с вашего счёта.", parse_mode="HTML")
        except Exception:
            pass

    elif ttype == "btc":
        from farm import get_farm
        farm = get_farm(rid)
        cur_btc = farm.get("btc_balance", 0.0)
        if txt in ("все", "all"):
            amount = cur_btc
        else:
            try:
                amount = round(float(txt.replace(",", ".")), 6)
            except ValueError:
                await message.answer("❌ Неверное количество BTC.")
                return
        amount = min(amount, cur_btc)
        farm["btc_balance"] = round(cur_btc - amount, 6)
        save_user_data()
        log_action(admin_id, admin_name, "take_btc", rid, f"-{amount} BTC")
        await message.answer(
            f"✅ <b>BTC забраны</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"₿ Забрано: <b>{amount} BTC</b>\n"
            f"👮 Кто забрал: <b>{admin_name}</b>\n"
            f"🕐 Дата: <b>{_now_str()}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"₿ Администратор списал <b>{amount} BTC</b> с вашего кошелька.", parse_mode="HTML")
        except Exception:
            pass

    elif ttype == "dc":
        cur_dc = u.get("donate_coins", 0)
        if txt in ("все", "all"):
            amount = cur_dc
        else:
            try:
                amount = int(txt)
            except ValueError:
                await message.answer("❌ Введите целое число DC.")
                return
        amount = min(amount, cur_dc)
        u["donate_coins"] = cur_dc - amount
        save_user_data()
        log_action(admin_id, admin_name, "take_dc", rid, f"-{amount} DC")
        await message.answer(
            f"✅ <b>DC забраны</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"💎 Забрано: <b>{amount} DC</b>\n"
            f"👮 Кто забрал: <b>{admin_name}</b>\n"
            f"🕐 Дата: <b>{_now_str()}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"💎 Администратор списал <b>{amount} DC</b> с вашего счёта.", parse_mode="HTML")
        except Exception:
            pass

    elif ttype == "bank":
        cur = u.get("user_bank", 0)
        amount = cur if txt in ("все", "all") else parse_k(txt)
        if not amount or amount <= 0:
            await message.answer("❌ Неверная сумма.")
            return
        amount = min(amount, cur)
        u["user_bank"] = cur - amount
        save_user_data()
        log_action(admin_id, admin_name, "take_bank", rid, f"-{format_amount(amount)}$ из банка")
        await message.answer(
            f"✅ <b>Деньги из банка забраны</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"🏦 Забрано: <b>{format_amount(amount)}$</b> из банка\n"
            f"👮 Кто забрал: <b>{admin_name}</b>\n"
            f"🕐 Дата: <b>{_now_str()}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"🏦 Администратор снял <b>{format_amount(amount)}$</b> с вашего банковского счёта.", parse_mode="HTML")
        except Exception:
            pass

    elif ttype == "farm":
        try:
            lvl = int(txt)
            if not (0 <= lvl <= 10):
                raise ValueError
        except ValueError:
            await message.answer("❌ Уровень фермы от 0 до 10.")
            return
        from farm import get_farm
        farm = get_farm(rid)
        old_lvl = farm.get("farm_level", 0)
        farm["farm_level"] = lvl
        save_user_data()
        log_action(admin_id, admin_name, "take_farm", rid, f"ферма лвл {old_lvl} → {lvl}")
        await message.answer(
            f"✅ <b>Ферма изменена</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"⛏ Ферма: уровень <b>{old_lvl} → {lvl}</b>\n"
            f"👮 Кто изменил: <b>{admin_name}</b>",
            parse_mode="HTML"
        )

    elif ttype == "house":
        u.pop("houses", None)
        save_user_data()
        log_action(admin_id, admin_name, "take_house", rid, "дом забран")
        await message.answer(
            f"✅ <b>Дом забран</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"🏠 Дом удалён\n"
            f"👮 Кто забрал: <b>{admin_name}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, "🏠 Администратор изъял ваш дом.", parse_mode="HTML")
        except Exception:
            pass

    elif ttype == "car":
        u.pop("cars", None)
        save_user_data()
        log_action(admin_id, admin_name, "take_car", rid, "авто забрано")
        await message.answer(
            f"✅ <b>Авто забрано</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"🚗 Авто удалено\n"
            f"👮 Кто забрал: <b>{admin_name}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, "🚗 Администратор изъял ваше авто.", parse_mode="HTML")
        except Exception:
            pass

    elif ttype == "biz":
        u.pop("business", None)
        save_user_data()
        log_action(admin_id, admin_name, "take_biz", rid, "бизнес забран")
        await message.answer(
            f"✅ <b>Бизнес забран</b>\n\n"
            f"👤 Игрок: {clickable_name(rid, rname, cl)}\n"
            f"🏢 Бизнес удалён\n"
            f"👮 Кто забрал: <b>{admin_name}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, "🏢 Администратор изъял ваш бизнес.", parse_mode="HTML")
        except Exception:
            pass

    role = get_role(admin_id)
    try:
        await message.answer(_panel_text(role), parse_mode="HTML", reply_markup=_get_panel_kb(role))
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  БАЗА ДАННЫХ
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_db")
async def cb_ip_db(callback: CallbackQuery):
    uid = callback.from_user.id
    if not has_permission(uid, "view_db"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return

    bans   = _load_bans()
    mutes  = _load_mutes()
    from clans import clans_data
    from admin_roles import (founders, zam_ld_list, tech_admins, admins_list,
                               designers_list, moders_list, followers_list, get_all_dynamic_roles)

    total_admins = (
        len([x for x in founders if x != 0]) +
        len([x for x in zam_ld_list if x != 0]) +
        len([x for x in tech_admins if x != 0]) +
        len([x for x in admins_list if x != 0]) +
        len([x for x in designers_list if x != 0]) +
        len([x for x in moders_list if x != 0]) +
        len([x for x in followers_list if x != 0]) +
        len(get_all_dynamic_roles())
    )

    now      = time.time()
    uptime   = int(now - BOT_START_TIME)
    h, r     = divmod(uptime, 3600)
    m, s     = divmod(r, 60)
    uptime_s = f"{h}ч {m}м {s}с"

    active_bans  = sum(1 for v in bans.values()  if v.get("permanent") or (v.get("until",0) > now))
    active_mutes = sum(1 for v in mutes.values() if v.get("permanent") or (v.get("until",0) > now))

    try:
        db_size = os.path.getsize(os.path.join(os.path.dirname(__file__), "users.json"))
        db_size_str = f"{db_size / 1024:.1f} КБ"
    except Exception:
        db_size_str = "—"

    rows = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="ip_back")],
    ]
    if has_permission(uid, "clear_db"):
        rows.insert(0, [InlineKeyboardButton(text="🗑 Очистить базу данных", callback_data="ip_db_wipe")])

    await callback.message.edit_text(
        f"🗄 <b>БАЗА ДАННЫХ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Игроков: <b>{len(utils.user_data)}</b>\n"
        f"🚫 Активных банов: <b>{active_bans}</b>\n"
        f"🔇 Активных мутов: <b>{active_mutes}</b>\n"
        f"🛡 Кланов: <b>{len(clans_data)}</b>\n"
        f"📁 Размер БД: <b>{db_size_str}</b>\n"
        f"⏱ Аптайм бота: <b>{uptime_s}</b>\n"
        f"👮 Всего в составе: <b>{total_admins}</b>\n\n"
        f"<i>Последнее обновление: {_now_str()}</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data == "ip_db_close")
async def cb_ip_db_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "ip_db_wipe")
async def cb_ip_db_wipe(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "clear_db"):
        await callback.answer("⛔ Только Основатель.", show_alert=True)
        return
    await callback.message.edit_text(
        "⚠️ <b>ВНИМАНИЕ! Очистка базы данных</b>\n\n"
        "Все игроки потеряют:\n"
        "• 💵 Деньги\n"
        "• 💎 Донат и DC\n"
        "• ⭐ Уровни и XP\n"
        "• 🎁 Предметы\n"
        "• 📊 Весь прогресс\n"
        "• 📈 Статистику\n\n"
        "<b>Это действие необратимо!</b>",
        parse_mode="HTML",
        reply_markup=_wipe_confirm_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "ip_db_wipe_confirm")
async def cb_ip_db_wipe_confirm(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "clear_db"):
        await callback.answer("⛔ Только Основатель.", show_alert=True)
        return
    count = len(utils.user_data)
    for uid_str in list(utils.user_data.keys()):
        utils.reset_user_data(int(uid_str))
    log_action(callback.from_user.id, callback.from_user.full_name, "db_wipe", details=f"Очищено {count} профилей")
    await callback.message.edit_text(
        f"✅ <b>База данных очищена</b>\n\n"
        f"🗑 Сброшено профилей: <b>{count}</b>\n"
        f"👮 Выполнил: <b>{callback.from_user.full_name}</b>\n"
        f"🕐 Дата: <b>{_now_str()}</b>",
        parse_mode="HTML"
    )
    await callback.answer()


# ══════════════════════════════════════════════════════════════════
#  БАН
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_ban")
async def cb_ip_ban(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "ban"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.set_state(IpBanState.waiting_user)
    await callback.message.edit_text(
        "🚫 <b>БАН</b>\n\nВведите ID, игровой ID или @юзернейм игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


@router.message(IpBanState.waiting_user)
async def ip_ban_user(message: Message, state: FSMContext):
    uid, rec = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not rec:
        await message.answer("❌ Игрок не найден.")
        return
    target_role = get_role(uid)
    my_role     = get_role(message.from_user.id)
    if my_role != ROLE_FOUNDER and target_role in (ROLE_FOUNDER, ROLE_ZAM_LD):
        await message.answer("⛔ Нельзя банить Основателя или Зама.")
        await state.clear()
        return
    await state.update_data(recipient_id=uid, recipient_name=rec.get("name", "Без имени"))
    await state.set_state(IpBanState.waiting_dur)
    await message.answer(
        f"⏳ Выберите срок бана для <b>{rec.get('name','?')}</b>:",
        parse_mode="HTML", reply_markup=_dur_ban_kb()
    )


@router.callback_query(F.data.startswith("ip_ban_dur:"), IpBanState.waiting_dur)
async def ip_ban_dur(callback: CallbackQuery, state: FSMContext):
    dur = callback.data.split(":", 1)[1]
    await state.update_data(ban_dur=dur)
    await state.set_state(IpBanState.waiting_reason)
    await callback.message.edit_text(
        "📝 Введите причину бана:", reply_markup=_CANCEL_KB
    )
    await callback.answer()


@router.message(IpBanState.waiting_reason)
async def ip_ban_reason(message: Message, state: FSMContext):
    data   = await state.get_data()
    rid    = data["recipient_id"]
    rname  = data["recipient_name"]
    dur    = data["ban_dur"]
    reason = message.text.strip()
    admin_id   = message.from_user.id
    admin_name = message.from_user.full_name
    await state.clear()

    bans = _load_bans()
    dur_map = {"1h": 3600, "1d": 86400, "7d": 604800, "30d": 2592000}
    if dur == "perm":
        bans[str(rid)] = {"permanent": True, "by": admin_id, "ts": time.time(), "reason": reason}
        dur_text = "навсегда"
    else:
        secs = dur_map.get(dur, 86400)
        bans[str(rid)] = {"until": time.time() + secs, "by": admin_id, "ts": time.time(), "reason": reason}
        labels = {"1h": "1 час", "1d": "1 день", "7d": "7 дней", "30d": "30 дней"}
        dur_text = labels.get(dur, dur)
    _save_bans(bans)
    log_action(admin_id, admin_name, "ban", rid, f"{rname} — {dur_text} | {reason}")

    await message.answer(
        f"🚫 <b>Бан выдан</b>\n\n"
        f"👤 Игрок: <b>{rname}</b>\n"
        f"⏳ Срок: <b>{dur_text}</b>\n"
        f"📄 Причина: <b>{reason}</b>\n"
        f"👮 Кто забанил: <b>{admin_name}</b>\n"
        f"🕐 Дата: <b>{_now_str()}</b>",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            rid,
            f"🚫 <b>Вы были заблокированы администрацией</b>\n\n"
            f"📄 Причина: <b>{reason}</b>\n"
            f"⏳ Срок: <b>{dur_text}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  РАЗБАН
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_unban")
async def cb_ip_unban(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "ban"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.set_state(IpUnbanState.waiting_user)
    await callback.message.edit_text(
        "🔓 <b>РАЗБАН</b>\n\nВведите ID, игровой ID или @юзернейм игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


@router.message(IpUnbanState.waiting_user)
async def ip_unban_user(message: Message, state: FSMContext):
    uid, rec = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not rec:
        await message.answer("❌ Игрок не найден.")
        return
    bans = _load_bans()
    if str(uid) not in bans:
        await message.answer("ℹ️ Этот игрок не забанен.")
        await state.clear()
        return
    entry = bans.pop(str(uid))
    _save_bans(bans)
    rname = rec.get("name", "Без имени")
    log_action(message.from_user.id, message.from_user.full_name, "unban", uid, rname)
    await state.clear()
    await message.answer(
        f"✅ <b>Бан снят</b>\n\n"
        f"👤 Игрок: <b>{rname}</b>\n"
        f"👮 Кто снял: <b>{message.from_user.full_name}</b>\n"
        f"🕐 Дата: <b>{_now_str()}</b>",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(uid, "✅ <b>Ваша блокировка была снята администратором.</b>", parse_mode="HTML")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  МУТ
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_mute")
async def cb_ip_mute(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "mute"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.set_state(IpMuteState.waiting_user)
    await callback.message.edit_text(
        "🔇 <b>МУТ</b>\n\nВведите ID, игровой ID или @юзернейм игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


@router.message(IpMuteState.waiting_user)
async def ip_mute_user(message: Message, state: FSMContext):
    uid, rec = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not rec:
        await message.answer("❌ Игрок не найден.")
        return
    await state.update_data(recipient_id=uid, recipient_name=rec.get("name", "Без имени"))
    await state.set_state(IpMuteState.waiting_dur)
    await message.answer(
        f"⏳ Выберите срок мута для <b>{rec.get('name','?')}</b>:",
        parse_mode="HTML", reply_markup=_dur_mute_kb()
    )


@router.callback_query(F.data.startswith("ip_mute_dur:"), IpMuteState.waiting_dur)
async def ip_mute_dur(callback: CallbackQuery, state: FSMContext):
    dur = callback.data.split(":", 1)[1]
    await state.update_data(mute_dur=dur)
    await state.set_state(IpMuteState.waiting_reason)
    await callback.message.edit_text("📝 Введите причину мута:", reply_markup=_CANCEL_KB)
    await callback.answer()


@router.message(IpMuteState.waiting_reason)
async def ip_mute_reason(message: Message, state: FSMContext):
    data   = await state.get_data()
    rid    = data["recipient_id"]
    rname  = data["recipient_name"]
    dur    = data["mute_dur"]
    reason = message.text.strip()
    admin_id   = message.from_user.id
    admin_name = message.from_user.full_name
    await state.clear()

    mutes = _load_mutes()
    dur_map = {"10m": 600, "1h": 3600, "1d": 86400}
    if dur == "perm":
        mutes[str(rid)] = {"permanent": True, "by": admin_id, "ts": time.time(), "reason": reason}
        dur_text = "навсегда"
    else:
        secs = dur_map.get(dur, 3600)
        mutes[str(rid)] = {"until": time.time() + secs, "by": admin_id, "ts": time.time(), "reason": reason}
        labels = {"10m": "10 минут", "1h": "1 час", "1d": "1 день"}
        dur_text = labels.get(dur, dur)
    _save_mutes(mutes)
    log_action(admin_id, admin_name, "mute", rid, f"{rname} — {dur_text} | {reason}")

    await message.answer(
        f"🔇 <b>Мут выдан</b>\n\n"
        f"👤 Игрок: <b>{rname}</b>\n"
        f"⏳ Срок: <b>{dur_text}</b>\n"
        f"📄 Причина: <b>{reason}</b>\n"
        f"👮 Кто замутил: <b>{admin_name}</b>\n"
        f"🕐 Дата: <b>{_now_str()}</b>",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            rid,
            f"🔇 <b>Вы получили мут от администрации</b>\n\n"
            f"📄 Причина: <b>{reason}</b>\n"
            f"⏳ Срок: <b>{dur_text}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  РАЗМУТ
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_unmute")
async def cb_ip_unmute(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "mute"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.set_state(IpUnmuteState.waiting_user)
    await callback.message.edit_text(
        "🔊 <b>РАЗМУТ</b>\n\nВведите ID, игровой ID или @юзернейм игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


@router.message(IpUnmuteState.waiting_user)
async def ip_unmute_user(message: Message, state: FSMContext):
    uid, rec = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not rec:
        await message.answer("❌ Игрок не найден.")
        return
    mutes = _load_mutes()
    if str(uid) not in mutes:
        await message.answer("ℹ️ Этот игрок не замьючен.")
        await state.clear()
        return
    mutes.pop(str(uid))
    _save_mutes(mutes)
    rname = rec.get("name", "Без имени")
    log_action(message.from_user.id, message.from_user.full_name, "unmute", uid, rname)
    await state.clear()
    await message.answer(
        f"🔊 <b>Мут снят</b>\n\n"
        f"👤 Игрок: <b>{rname}</b>\n"
        f"👮 Кто снял: <b>{message.from_user.full_name}</b>\n"
        f"🕐 Дата: <b>{_now_str()}</b>",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(uid, "🔊 <b>Ваш мут был снят администратором.</b>", parse_mode="HTML")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  ВАРН / СНЯТЬ ВАРН
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_warn")
async def cb_ip_warn(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "ban") and not has_permission(callback.from_user.id, "warn"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.set_state(IpWarnState.waiting_user)
    await callback.message.edit_text(
        "⚠️ <b>ВАРН</b>\n\nВведите ID, игровой ID или @юзернейм игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


@router.message(IpWarnState.waiting_user)
async def ip_warn_user(message: Message, state: FSMContext):
    uid, rec = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not rec:
        await message.answer("❌ Игрок не найден.")
        return
    await state.update_data(recipient_id=uid, recipient_name=rec.get("name", "Без имени"))
    await state.set_state(IpWarnState.waiting_reason)
    await message.answer("📝 Введите причину варна:", reply_markup=_CANCEL_KB)


@router.message(IpWarnState.waiting_reason)
async def ip_warn_reason(message: Message, state: FSMContext):
    from group_commands import add_warn, get_warns, clear_warns, MAX_WARNS
    data   = await state.get_data()
    rid    = data["recipient_id"]
    rname  = data["recipient_name"]
    reason = message.text.strip()
    admin_id   = message.from_user.id
    admin_name = message.from_user.full_name
    await state.clear()

    count = add_warn(rid, admin_id, reason)
    log_action(admin_id, admin_name, "warn", rid, f"{rname}: {reason}")

    if count >= MAX_WARNS:
        bans = _load_bans()
        bans[str(rid)] = {"permanent": True, "by": admin_id, "ts": time.time(), "reason": f"Автобан: {MAX_WARNS} варна"}
        _save_bans(bans)
        clear_warns(rid)
        await message.answer(
            f"⚠️ <b>Варн выдан</b>\n\n"
            f"👤 Игрок: <b>{rname}</b>\n"
            f"📊 Варнов: <b>{MAX_WARNS}/{MAX_WARNS}</b>\n"
            f"🚫 <b>Автобан активирован!</b>\n"
            f"📄 Причина: <b>{reason}</b>\n"
            f"🕐 Дата: <b>{_now_str()}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"⚠️ Вам выдан варн: <b>{reason}</b>\n🚫 Достигнут лимит — вы забанены автоматически.", parse_mode="HTML")
        except Exception:
            pass
    else:
        await message.answer(
            f"⚠️ <b>Варн выдан</b>\n\n"
            f"👤 Игрок: <b>{rname}</b>\n"
            f"📊 Варнов: <b>{count}/{MAX_WARNS}</b>\n"
            f"📄 Причина: <b>{reason}</b>\n"
            f"🕐 Дата: <b>{_now_str()}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(rid, f"⚠️ Вам выдан варн от администрации.\nПричина: <b>{reason}</b>\nВарнов: {count}/{MAX_WARNS}", parse_mode="HTML")
        except Exception:
            pass


@router.callback_query(F.data == "ip_unwarn")
async def cb_ip_unwarn(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "ban") and not has_permission(callback.from_user.id, "warn"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.set_state(IpUnwarnState.waiting_user)
    await callback.message.edit_text(
        "✅ <b>СНЯТЬ ВАРН</b>\n\nВведите ID, игровой ID или @юзернейм игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


@router.message(IpUnwarnState.waiting_user)
async def ip_unwarn_user(message: Message, state: FSMContext):
    from group_commands import remove_last_warn, get_warns, MAX_WARNS
    uid, rec = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not rec:
        await message.answer("❌ Игрок не найден.")
        return
    rname   = rec.get("name", "Без имени")
    removed = remove_last_warn(uid)
    current = len(get_warns(uid))
    log_action(message.from_user.id, message.from_user.full_name, "unwarn", uid, rname)
    await state.clear()
    if removed:
        await message.answer(
            f"✅ <b>Варн снят</b>\n\n"
            f"👤 Игрок: <b>{rname}</b>\n"
            f"📊 Осталось варнов: <b>{current}/{MAX_WARNS}</b>\n"
            f"🕐 Дата: <b>{_now_str()}</b>",
            parse_mode="HTML"
        )
    else:
        await message.answer(f"ℹ️ У игрока <b>{rname}</b> нет активных варнов.", parse_mode="HTML")


# ══════════════════════════════════════════════════════════════════
#  ВАРП / СНЯТЬ ВАРП
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_warp")
async def cb_ip_warp(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "warp"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.set_state(IpWarpState.waiting_user)
    await callback.message.edit_text(
        "🌀 <b>ВАРП</b>\n\nВведите ID, игровой ID или @юзернейм игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


@router.message(IpWarpState.waiting_user)
async def ip_warp_user(message: Message, state: FSMContext):
    uid, rec = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not rec:
        await message.answer("❌ Игрок не найден.")
        return
    warps = _load_warps()
    cur_warp = warps.get(str(uid), {}).get("point", "нет")
    await state.update_data(recipient_id=uid, recipient_name=rec.get("name", "Без имени"))
    await state.set_state(IpWarpState.waiting_point)
    await message.answer(
        f"🌀 Игрок: <b>{rec.get('name','?')}</b>\n"
        f"📍 Текущий варп: <b>{cur_warp}</b>\n\n"
        f"Введите название варп-точки (например: <code>VIP-Зона</code>, <code>Штаб</code>):",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )


@router.message(IpWarpState.waiting_point)
async def ip_warp_point(message: Message, state: FSMContext):
    data   = await state.get_data()
    rid    = data["recipient_id"]
    rname  = data["recipient_name"]
    point  = message.text.strip()
    admin_id   = message.from_user.id
    admin_name = message.from_user.full_name
    await state.clear()

    warps = _load_warps()
    warps[str(rid)] = {"point": point, "by": admin_id, "ts": time.time()}
    _save_warps(warps)
    log_action(admin_id, admin_name, "warp_give", rid, f"{rname} → {point}")

    await message.answer(
        f"🌀 <b>Варп выдан</b>\n\n"
        f"👤 Игрок: <b>{rname}</b>\n"
        f"📍 Точка: <b>{point}</b>\n"
        f"👮 Кто выдал: <b>{admin_name}</b>\n"
        f"🕐 Дата: <b>{_now_str()}</b>",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(rid, f"🌀 Вам выдан варп: <b>{point}</b>\nАдминистратор: {admin_name}", parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data == "ip_unwarp")
async def cb_ip_unwarp(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "warp"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.set_state(IpUnwarpState.waiting_user)
    await callback.message.edit_text(
        "❌ <b>СНЯТЬ ВАРП</b>\n\nВведите ID, игровой ID или @юзернейм игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


@router.message(IpUnwarpState.waiting_user)
async def ip_unwarp_user(message: Message, state: FSMContext):
    uid, rec = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not rec:
        await message.answer("❌ Игрок не найден.")
        return
    warps = _load_warps()
    if str(uid) not in warps:
        await message.answer(f"ℹ️ У игрока <b>{rec.get('name','?')}</b> нет активного варпа.", parse_mode="HTML")
        await state.clear()
        return
    entry = warps.pop(str(uid))
    _save_warps(warps)
    rname = rec.get("name", "Без имени")
    log_action(message.from_user.id, message.from_user.full_name, "warp_remove", uid, f"{rname} — {entry.get('point','?')}")
    await state.clear()
    await message.answer(
        f"✅ <b>Варп снят</b>\n\n"
        f"👤 Игрок: <b>{rname}</b>\n"
        f"📍 Была точка: <b>{entry.get('point','—')}</b>\n"
        f"🕐 Дата: <b>{_now_str()}</b>",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(uid, "❌ Ваш варп был снят администратором.", parse_mode="HTML")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  ЛОГИ
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_logs")
async def cb_ip_logs(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "view_logs"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    logs = get_logs(limit=15)
    text = "📜 <b>ПОСЛЕДНИЕ ЛОГИ АДМИНИСТРАЦИИ</b>\n\n"
    text += format_logs(logs) if logs else "📭 Логов пока нет."

    rows = [
        [InlineKeyboardButton(text="🔍 Мои действия",    callback_data="ip_logs_mine"),
         InlineKeyboardButton(text="🚫 Только баны",     callback_data="ip_logs_bans")],
        [InlineKeyboardButton(text="💵 Только выдачи",   callback_data="ip_logs_give"),
         InlineKeyboardButton(text="🔇 Только муты",     callback_data="ip_logs_mutes")],
        [InlineKeyboardButton(text="⬅️ Назад",           callback_data="ip_back")],
    ]
    await callback.message.edit_text(
        text[:4090], parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ip_logs_"))
async def cb_ip_logs_filter(callback: CallbackQuery):
    key = callback.data.split("ip_logs_")[1]
    if key == "close":
        await callback.message.delete()
        await callback.answer()
        return

    filter_map = {
        "mine":  {"admin_id": callback.from_user.id},
        "bans":  {"action": "ban"},
        "give":  {"action": "give_currency"},
        "mutes": {"action": "mute"},
    }
    kwargs = filter_map.get(key, {})
    logs   = get_logs(limit=15, **kwargs)

    titles = {
        "mine":  "🔍 МОИ ДЕЙСТВИЯ",
        "bans":  "🚫 БАНЫ",
        "give":  "💵 ВЫДАЧИ ВАЛЮТЫ",
        "mutes": "🔇 МУТЫ",
    }
    text = f"📜 <b>{titles.get(key, 'ЛОГИ')}</b>\n\n"
    text += format_logs(logs) if logs else "📭 Логов нет."

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ К логам", callback_data="ip_logs"),
        InlineKeyboardButton(text="🏠 Панель",  callback_data="ip_back"),
    ]])
    try:
        await callback.message.edit_text(text[:4090], parse_mode="HTML", reply_markup=back_kb)
    except Exception:
        await callback.answer("Нет изменений.", show_alert=False)
    await callback.answer()


# ══════════════════════════════════════════════════════════════════
#  УПРАВЛЕНИЕ АДМИНАМИ
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_admins")
async def cb_ip_admins(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "manage_roles"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    my_role = get_role(callback.from_user.id)

    from admin_roles import (founders, zam_ld_list, tech_admins, admins_list,
                               designers_list, moders_list, followers_list, get_all_dynamic_roles)
    dynamic = get_all_dynamic_roles()

    lines = ["🛡 <b>СОСТАВ АДМИНИСТРАЦИИ</b>\n"]
    groups = [
        (founders,       ROLE_FOUNDER,    "👑"),
        (zam_ld_list,    ROLE_ZAM_LD,    "⭐"),
        (tech_admins,    ROLE_TECH_ADMIN, "🔧"),
        (admins_list,    ROLE_ADMIN,      "👮"),
        (designers_list, ROLE_DESIGNER,   "🎨"),
        (moders_list,    ROLE_MODER,      "🛡"),
        (followers_list, ROLE_FOLLOWER,   "👁"),
    ]
    for uid_list, role, icon in groups:
        real = [x for x in uid_list if x != 0]
        if real:
            label = ROLE_LABELS[role]
            lines.append(f"\n{icon} <b>{label}</b>")
            for uid in real:
                u = get_user(uid)
                name = u.get("name", "Без имени") if u else f"ID {uid}"
                lines.append(f"  • {name} (<code>{uid}</code>)")

    if dynamic:
        lines.append("\n⚙️ <b>Динамические роли</b>")
        for uid_str, role in dynamic.items():
            u    = get_user(int(uid_str))
            name = u.get("name", "Без имени") if u else f"ID {uid_str}"
            icon = ROLE_LABELS.get(role, role)
            lines.append(f"  • {name} — {icon}")

    rows = []
    if my_role in (ROLE_FOUNDER, ROLE_ZAM_LD):
        rows.append([InlineKeyboardButton(text="➕ Назначить роль",  callback_data="ip_grant_role_start"),
                     InlineKeyboardButton(text="➖ Снять роль",     callback_data="ip_revoke_role_start")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="ip_back")])

    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data == "ip_admins_close")
async def cb_ip_admins_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "ip_grant_role_start")
async def cb_ip_grant_start(callback: CallbackQuery, state: FSMContext):
    my_role = get_role(callback.from_user.id)
    if my_role not in (ROLE_FOUNDER, ROLE_ZAM_LD):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.set_state(IpGrantRoleState.waiting_user)
    await callback.message.edit_text(
        "➕ <b>НАЗНАЧИТЬ РОЛЬ</b>\n\nВведите ID, игровой ID или @юзернейм игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


@router.message(IpGrantRoleState.waiting_user)
async def ip_grant_user(message: Message, state: FSMContext):
    uid, rec = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not rec:
        await message.answer("❌ Игрок не найден.")
        return
    await state.update_data(recipient_id=uid, recipient_name=rec.get("name", "Без имени"))
    await state.set_state(IpGrantRoleState.waiting_role)
    my_role = get_role(message.from_user.id)
    await message.answer(
        f"👤 Игрок: <b>{rec.get('name','?')}</b>\n\nВыберите роль:",
        parse_mode="HTML", reply_markup=_role_assign_kb(my_role)
    )


@router.callback_query(F.data.startswith("ip_grant_role:"), IpGrantRoleState.waiting_role)
async def ip_grant_role_pick(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split(":", 1)[1]
    data = await state.get_data()
    rid  = data["recipient_id"]
    rname = data["recipient_name"]
    await state.clear()

    grant_role(rid, role)
    label = ROLE_LABELS.get(role, role)
    log_action(callback.from_user.id, callback.from_user.full_name, "grant_role", rid, f"{rname} → {label}")
    try:
        await bot.send_message(rid, f"🎖 Вам назначена роль: <b>{label}</b>\nОт: {callback.from_user.full_name}", parse_mode="HTML")
    except Exception:
        pass
    my_role = get_role(callback.from_user.id)
    result_text = (
        f"✅ <b>Роль назначена</b>\n\n"
        f"👤 Игрок: <b>{rname}</b>\n"
        f"🎖 Роль: <b>{label}</b>\n"
        f"👮 Кто назначил: <b>{callback.from_user.full_name}</b>\n"
        f"🕐 Дата: <b>{_now_str()}</b>\n\n"
        + _panel_text(my_role)
    )
    try:
        await callback.message.edit_text(result_text, parse_mode="HTML", reply_markup=_get_panel_kb(my_role))
    except Exception:
        await callback.message.answer(_panel_text(my_role), parse_mode="HTML", reply_markup=_get_panel_kb(my_role))
    await callback.answer()


@router.callback_query(F.data == "ip_revoke_role_start")
async def cb_ip_revoke_start(callback: CallbackQuery, state: FSMContext):
    my_role = get_role(callback.from_user.id)
    if my_role not in (ROLE_FOUNDER, ROLE_ZAM_LD):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.set_state(IpRevokeRoleState.waiting_user)
    await callback.message.edit_text(
        "➖ <b>СНЯТЬ РОЛЬ</b>\n\nВведите ID, игровой ID или @юзернейм администратора:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await callback.answer()


@router.message(IpRevokeRoleState.waiting_user)
async def ip_revoke_user(message: Message, state: FSMContext):
    uid, rec = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not rec:
        await message.answer("❌ Игрок не найден.")
        return
    rname = rec.get("name", "Без имени")
    revoke_role(uid)
    log_action(message.from_user.id, message.from_user.full_name, "revoke_role", uid, rname)
    await state.clear()
    await message.answer(
        f"✅ <b>Роль снята</b>\n\n"
        f"👤 Игрок: <b>{rname}</b>\n"
        f"👮 Кто снял: <b>{message.from_user.full_name}</b>\n"
        f"🕐 Дата: <b>{_now_str()}</b>",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(uid, "❌ Ваша административная роль была снята.", parse_mode="HTML")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  ЖАЛОБЫ (Complaints)
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_complaints")
async def cb_ip_complaints(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "view_complaints") and \
       not has_permission(callback.from_user.id, "answer_complaints"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    complaints = _load_complaints()
    open_c = {k: v for k, v in complaints.items() if v.get("status") == "open"}

    if not open_c:
        await callback.message.edit_text(
            "📨 <b>ЖАЛОБЫ</b>\n\n✅ Открытых жалоб нет.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="ip_back")
            ]])
        )
        await callback.answer()
        return

    lines = ["📨 <b>ОТКРЫТЫЕ ЖАЛОБЫ</b>\n"]
    rows  = []
    for cid, c in list(open_c.items())[:10]:
        lines.append(
            f"🆔 #{cid} | 👤 {c.get('from_name','?')} → 🎯 {c.get('on_name','?')}\n"
            f"📝 {c.get('text','')[:60]}..."
        )
        rows.append([
            InlineKeyboardButton(text=f"📋 #{cid}",      callback_data=f"ip_complaint_view:{cid}"),
            InlineKeyboardButton(text=f"✅ Закрыть #{cid}", callback_data=f"ip_complaint_close:{cid}"),
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="ip_back")])
    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data == "ip_complaints_close")
async def cb_ip_complaints_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("ip_complaint_close:"))
async def cb_ip_complaint_close_item(callback: CallbackQuery):
    cid = callback.data.split(":", 1)[1]
    complaints = _load_complaints()
    if cid in complaints:
        complaints[cid]["status"] = "closed"
        complaints[cid]["closed_by"] = callback.from_user.id
        _save_complaints(complaints)
    log_action(callback.from_user.id, callback.from_user.full_name, "close_complaint", details=f"#{cid}")
    await callback.answer(f"✅ Жалоба #{cid} закрыта.", show_alert=True)


@router.callback_query(F.data.startswith("ip_complaint_view:"))
async def cb_ip_complaint_view(callback: CallbackQuery):
    cid = callback.data.split(":", 1)[1]
    complaints = _load_complaints()
    c = complaints.get(cid)
    if not c:
        await callback.answer("❌ Жалоба не найдена.", show_alert=True)
        return
    text = (
        f"📋 <b>ЖАЛОБА #{cid}</b>\n\n"
        f"👤 От: <b>{c.get('from_name','?')}</b> (<code>{c.get('from_id','?')}</code>)\n"
        f"🎯 На: <b>{c.get('on_name','?')}</b> (<code>{c.get('on_id','?')}</code>)\n"
        f"📝 Текст: {c.get('text','—')}\n"
        f"🕐 Дата: {c.get('date','—')}\n"
        f"📊 Статус: <b>{c.get('status','?')}</b>"
    )
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Закрыть жалобу", callback_data=f"ip_complaint_close:{cid}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="ip_complaints"),
    ]])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb)
    await callback.answer()


# ══════════════════════════════════════════════════════════════════
#  РЕПОРТЫ
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_reports")
async def cb_ip_reports(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "view_reports") and \
       not has_permission(callback.from_user.id, "check_reports"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    reports = _load_reports()
    open_r  = {k: v for k, v in reports.items() if v.get("status") == "open"}

    if not open_r:
        await callback.message.edit_text(
            "📋 <b>РЕПОРТЫ</b>\n\n✅ Открытых репортов нет.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="ip_back")
            ]])
        )
        await callback.answer()
        return

    lines = [f"📋 <b>ОТКРЫТЫЕ РЕПОРТЫ ({len(open_r)})</b>\n"]
    rows  = []
    for rid_key, r in list(open_r.items())[-10:]:
        uname = r.get("user_name", "?")
        txt   = r.get("text", "")[:50]
        lines.append(f"🆔 #{rid_key} | 👤 {uname}: {txt}...")
        rows.append([
            InlineKeyboardButton(text=f"📖 #{rid_key}", callback_data=f"ip_report_view:{rid_key}"),
            InlineKeyboardButton(text=f"✅ #{rid_key}", callback_data=f"ip_report_done:{rid_key}"),
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="ip_back")])
    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data == "ip_reports_close")
async def cb_ip_reports_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("ip_report_view:"))
async def cb_ip_report_view(callback: CallbackQuery):
    rid_key  = callback.data.split(":", 1)[1]
    reports  = _load_reports()
    r        = reports.get(rid_key)
    if not r:
        await callback.answer("❌ Репорт не найден.", show_alert=True)
        return
    text = (
        f"📖 <b>РЕПОРТ #{rid_key}</b>\n\n"
        f"👤 От: <b>{r.get('user_name','?')}</b> (<code>{r.get('user_id','?')}</code>)\n"
        f"📝 Текст:\n{r.get('text','—')}\n\n"
        f"📊 Статус: <b>{r.get('status','?')}</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Закрыть репорт", callback_data=f"ip_report_done:{rid_key}"),
         InlineKeyboardButton(text="⬅️ Назад",          callback_data="ip_reports")],
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("ip_report_done:"))
async def cb_ip_report_done(callback: CallbackQuery):
    rid_key = callback.data.split(":", 1)[1]
    reports = _load_reports()
    if rid_key in reports:
        reports[rid_key]["status"] = "answered"
        reports[rid_key]["closed_by"] = callback.from_user.id
        _save_reports(reports)
    log_action(callback.from_user.id, callback.from_user.full_name, "close_report", details=f"#{rid_key}")
    await callback.answer(f"✅ Репорт #{rid_key} закрыт.", show_alert=True)


# ══════════════════════════════════════════════════════════════════
#  НАСТРОЙКИ БОТА
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_settings")
async def cb_ip_settings(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "bot_settings") and \
       not has_permission(callback.from_user.id, "system_control"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    from admin_roles import (founders, zam_ld_list, tech_admins, admins_list,
                               designers_list, moders_list, followers_list)
    text = (
        "⚙️ <b>НАСТРОЙКИ БОТА</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📋 <b>Переменные окружения:</b>\n"
        f"  • <code>BOT_TOKEN</code> — токен бота ✅\n"
        f"  • <code>BOT_FOUNDERS</code> — {len([x for x in founders if x!=0])} Основателей\n"
        f"  • <code>BOT_ZAM_LD</code> — {len([x for x in zam_ld_list if x!=0])} Замов\n"
        f"  • <code>BOT_TECH_ADMINS</code> — {len([x for x in tech_admins if x!=0])} Тех Админов\n"
        f"  • <code>BOT_ADMINS</code> — {len([x for x in admins_list if x!=0])} Админов\n"
        f"  • <code>BOT_DESIGNERS</code> — {len([x for x in designers_list if x!=0])} Дизайнеров\n"
        f"  • <code>BOT_MODERS</code> — {len([x for x in moders_list if x!=0])} Модеров\n\n"
        "🔐 <b>Безопасность:</b>\n"
        "  • Логирование: ✅ включено\n"
        "  • Авто-бан при 3 варнах: ✅\n"
        "  • Лимит выдачи (Админ): 200 млн/день\n\n"
        "🗄 <b>Данные:</b>\n"
        "  • Хранилище: JSON-файлы\n"
        "  • Макс. логов: 500 записей\n\n"
        f"⏱ <b>Аптайм:</b> {int(time.time() - BOT_START_TIME) // 3600}ч "
        f"{(int(time.time() - BOT_START_TIME) % 3600) // 60}м"
    )
    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Назад", callback_data="ip_back")
        ]])
    )
    await callback.answer()


@router.callback_query(F.data == "ip_settings_close")
async def cb_ip_settings_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


# ══════════════════════════════════════════════════════════════════
#  ЗАЩИТА (Tech Admin)
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ip_protection")
async def cb_ip_protection(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "system_control") and \
       not has_permission(callback.from_user.id, "antispam_config"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await callback.message.edit_text(
        "🔒 <b>СИСТЕМА ЗАЩИТЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📜 <b>Что логируется:</b>\n"
        "  • Выдача/снятие валюты\n"
        "  • Баны и разбаны\n"
        "  • Муты и размуты\n"
        "  • Варны\n"
        "  • Варпы\n"
        "  • Смена ролей\n"
        "  • Очистка базы\n\n"
        "⚠️ <b>Авто-контроль:</b>\n"
        "  • Проверка лимитов в реальном времени\n"
        "  • Уведомление Основателей при ≥80% лимита\n"
        "  • Авто-бан при 3 варнах\n"
        "  • Блокировка выдач сверх лимита",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Назад", callback_data="ip_back")
        ]])
    )
    await callback.answer()


@router.callback_query(F.data == "ip_protection_close")
async def cb_ip_protection_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


# ══════════════════════════════════════════════════════════════════
#  ДИЗАЙНЕР — редактор текстов
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data.in_({"ip_edit_texts", "ip_edit_emoji", "ip_bot_msgs", "ip_style"}))
async def cb_ip_designer(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "edit_texts"):
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    section_texts = {
        "ip_edit_texts": (
            "🎨 <b>РЕДАКТОР ТЕКСТОВ</b>\n\n"
            "Здесь можно управлять текстами бота.\n\n"
            "<i>Для изменения текстов обратитесь к Основателю или отправьте правки через репорт.</i>"
        ),
        "ip_edit_emoji": (
            "😊 <b>РЕДАКТОР ЭМОДЗИ</b>\n\n"
            "Список эмодзи используемых в боте:\n"
            "• 💵 — Деньги\n• ₿ — Биткоин\n• 💎 — DC донат\n"
            "• ⭐ — Уровень\n• 🚫 — Бан\n• 🔇 — Мут\n• ⚠️ — Варн\n"
            "• 🌀 — Варп\n• 🛡 — Клан\n• 👑 — Основатель"
        ),
        "ip_bot_msgs": (
            "📝 <b>СООБЩЕНИЯ БОТА</b>\n\n"
            "Все тексты бота хранятся в файле <code>texts.py</code>.\n"
            "Для правок передайте изменения Основателю."
        ),
        "ip_style": (
            "🎭 <b>СТИЛЬ ИНТЕРФЕЙСА</b>\n\n"
            "Текущий стиль: <b>Классический</b>\n"
            "Разделители: ━━━━━━━━━━\n"
            "Рамки: ╔══╗ / ╚══╝\n"
            "Теги: HTML (<b>, <i>, <code>)"
        ),
    }
    text = section_texts.get(callback.data, "—")
    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Назад", callback_data="ip_designer_back")
        ]])
    )
    await callback.answer()


@router.callback_query(F.data == "ip_designer_back")
async def cb_ip_designer_back(callback: CallbackQuery):
    uid  = callback.from_user.id
    role = get_role(uid)
    label = ROLE_LABELS.get(role, "—")
    await callback.message.edit_text(
        f"╔══════════════════════╗\n"
        f"   {_role_header(role)}\n"
        f"╚══════════════════════╝\n\n"
        f"👤 Ранг: <b>{label}</b>\n"
        f"🕐 Время: <b>{_now_str()}</b>\n\n"
        f"<i>Выберите действие:</i>",
        parse_mode="HTML", reply_markup=_get_panel_kb(role)
    )
    await callback.answer()


# ══════════════════════════════════════════════════════════════════
#  Команда "жалоба" для игроков
# ══════════════════════════════════════════════════════════════════

@router.message(F.text.lower().startswith("жалоба "))
async def player_complaint(message: Message):
    user_id   = message.from_user.id
    user_name = get_user(user_id).get("name", message.from_user.full_name)
    text_arg  = message.text.strip()[len("жалоба "):].strip()

    if not text_arg:
        await message.answer(
            "❌ Укажите текст жалобы.\nПример: <code>жалоба игрок Вася использует читы</code>",
            parse_mode="HTML"
        )
        return

    complaints = _load_complaints()
    next_id    = str(max((int(k) for k in complaints.keys()), default=0) + 1)
    complaints[next_id] = {
        "from_id":   user_id,
        "from_name": user_name,
        "on_name":   "Неизвестно",
        "on_id":     None,
        "text":      text_arg,
        "status":    "open",
        "date":      _now_str(),
    }
    _save_complaints(complaints)
    await message.answer(
        f"✅ <b>Жалоба #{next_id} отправлена!</b>\n\n"
        f"📝 Текст: {text_arg[:100]}\n"
        f"👮 Администрация рассмотрит её в ближайшее время.",
        parse_mode="HTML"
    )
    for f_id in founders:
        if f_id == 0:
            continue
        try:
            await bot.send_message(
                f_id,
                f"📨 <b>Новая жалоба #{next_id}</b>\n\n"
                f"👤 От: {user_name} (<code>{user_id}</code>)\n"
                f"📝 {text_arg[:200]}",
                parse_mode="HTML"
            )
        except Exception:
            pass
