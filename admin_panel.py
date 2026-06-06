import os
import json
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state

from admin_roles import (
    get_role, has_permission, is_admin_any, grant_role, revoke_role,
    get_all_dynamic_roles, check_and_use_limit, get_remaining_limit,
    ROLE_FOUNDER, ROLE_ZAM_LD, ROLE_TECH_ADMIN, ROLE_ADMIN,
    ROLE_DESIGNER, ROLE_MODER, ROLE_FOLLOWER,
    ROLE_LABELS, DAILY_LIMITS, founders,
)
from admin_logs import log_action, get_logs, format_logs
import utils
from utils import (
    load_user_data, save_user_data, get_user, get_balance, update_balance,
    set_name, get_name, parse_k, format_amount, find_user_by_identifier,
    reset_user_data, clickable_name, safe_reply_kb,
)
from config import bot

router = Router()

BANS_FILE = os.path.join(os.path.dirname(__file__), "admin_bans.json")
MUTES_FILE = os.path.join(os.path.dirname(__file__), "admin_mutes.json")


def _load_bans() -> dict:
    if os.path.exists(BANS_FILE):
        try:
            with open(BANS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_bans(data: dict):
    with open(BANS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_mutes() -> dict:
    if os.path.exists(MUTES_FILE):
        try:
            with open(MUTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_mutes(data: dict):
    with open(MUTES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_banned(user_id: int) -> bool:
    bans = _load_bans()
    entry = bans.get(str(user_id))
    if not entry:
        return False
    if entry.get("permanent"):
        return True
    if entry.get("until") and time.time() < entry["until"]:
        return True
    return False


def is_muted(user_id: int) -> bool:
    mutes = _load_mutes()
    entry = mutes.get(str(user_id))
    if not entry:
        return False
    if entry.get("permanent"):
        return True
    if entry.get("until") and time.time() < entry["until"]:
        return True
    return False


def _get_admin_kb(user_id: int):
    from keyboards import (
        founder_kb, zam_ld_kb, tech_admin_kb, admin_role_kb,
        designer_kb, moder_kb, follower_kb,
    )
    role = get_role(user_id)
    if role == ROLE_FOUNDER:
        return founder_kb
    elif role == ROLE_ZAM_LD:
        return zam_ld_kb
    elif role == ROLE_TECH_ADMIN:
        return tech_admin_kb
    elif role == ROLE_ADMIN:
        return admin_role_kb
    elif role == ROLE_DESIGNER:
        return designer_kb
    elif role == ROLE_MODER:
        return moder_kb
    elif role == ROLE_FOLLOWER:
        return follower_kb
    from keyboards import menu_kb
    return menu_kb


def _role_panel_text(user_id: int) -> str:
    role = get_role(user_id)
    texts = {
        ROLE_FOUNDER: (
            "👑 <b>Панель Основателя</b>\n\n"
            "Полный доступ ко всем функциям системы.\n"
            "💵 Выдача / 💸 Забирать — без лимитов\n"
            "Управляй ролями, базой, API и конфигами.\n\n"
            "<i>Напиши «админ» для открытия inline-панели.</i>"
        ),
        ROLE_ZAM_LD: (
            "⭐ <b>Панель Зама</b>\n\n"
            "Почти полный доступ.\n"
            "💰 Выдача: <b>без лимитов</b>\n"
            "🔨 Бан / 🔇 Мут / 🎁 Промо / 🗑️ Обнуление\n\n"
            "<i>Напиши «админ» для открытия inline-панели.</i>"
        ),
        ROLE_TECH_ADMIN: (
            "🔧 <b>Панель Тех Админа</b>\n\n"
            "Системный доступ и безопасность.\n"
            "💰 Выдача: <b>без лимитов</b>\n"
            "Все выдачи логируются автоматически.\n\n"
            "<i>Напиши «админ» для открытия inline-панели.</i>"
        ),
        ROLE_ADMIN: (
            "👮 <b>Панель Админа</b>\n\n"
            "Управление игроками.\n"
            "💰 Выдача: до 200 млн/день\n"
            "🔨 Бан / 🔇 Мут / 🌀 Варп / 🎁 Промо\n\n"
            "<i>Напиши «админ» для открытия inline-панели.</i>"
        ),
        ROLE_DESIGNER: (
            "🎨 <b>Панель Дизайнера</b>\n\n"
            "Управление интерфейсом и текстами бота.\n"
            "Редактирование: тексты, эмодзи, кнопки.\n\n"
            "<i>Напиши «админ» для открытия inline-панели.</i>"
        ),
        ROLE_MODER: (
            "🛡 <b>Панель Модера</b>\n\n"
            "Модерация чата и работа с жалобами.\n"
            "🔇 Мут (макс. 7 дней) / ⚠️ Варн\n"
            "📨 Жалобы / 📋 Репорты\n\n"
            "<i>Напиши «админ» для открытия inline-панели.</i>"
        ),
        ROLE_FOLLOWER: (
            "👁 <b>Панель Фолера</b>\n\n"
            "Просмотр отчётов и информации об игроках.\n"
            "📋 Репорты / ℹ️ Информация\n\n"
            "<i>Напиши «админ» для открытия inline-панели.</i>"
        ),
    }
    return texts.get(role, "⚙️ Панель")


class NewAdminGiveState(StatesGroup):
    waiting_user   = State()
    waiting_amount = State()


class AdminGiveCaseState(StatesGroup):
    waiting_user  = State()
    waiting_case  = State()
    waiting_count = State()


class AdminGiveBankState(StatesGroup):
    waiting_user   = State()
    waiting_amount = State()


class AdminGiveBtcState(StatesGroup):
    waiting_user   = State()
    waiting_amount = State()


class AdminGiveDcState(StatesGroup):
    waiting_user   = State()
    waiting_amount = State()


class AdminGiveLevelState(StatesGroup):
    waiting_user  = State()
    waiting_value = State()


class AdminGiveDonateItemState(StatesGroup):
    waiting_item = State()
    waiting_user = State()


class AdminTakeState(StatesGroup):
    waiting_user   = State()
    waiting_amount = State()


class AdminTakeBankState(StatesGroup):
    waiting_amount = State()


class AdminTakeBtcState(StatesGroup):
    waiting_amount = State()


class AdminTakeDcState(StatesGroup):
    waiting_amount = State()


class AdminTakeLevelState(StatesGroup):
    waiting_user = State()


class NewAdminResetState(StatesGroup):
    waiting_user    = State()
    waiting_confirm = State()


class ServerWipeState(StatesGroup):
    waiting_confirm1 = State()
    waiting_confirm2 = State()


class NewAdminSetState(StatesGroup):
    waiting_field   = State()
    waiting_user    = State()
    waiting_value   = State()
    waiting_confirm = State()


class BanState(StatesGroup):
    waiting_user = State()
    waiting_days = State()


class MuteState(StatesGroup):
    waiting_user = State()
    waiting_hours = State()


class UnbanState(StatesGroup):
    waiting_user = State()


class UnmuteState(StatesGroup):
    waiting_user = State()


class WarnState(StatesGroup):
    waiting_user = State()
    waiting_reason = State()


class UnwarnState(StatesGroup):
    waiting_user = State()


class GrantRoleState(StatesGroup):
    waiting_user = State()
    waiting_role = State()


class RevokeRoleState(StatesGroup):
    waiting_user = State()


class WarnFromAdminListState(StatesGroup):
    waiting_reason = State()


class AssignAdminFromListState(StatesGroup):
    waiting_id   = State()
    waiting_role = State()


PANEL_TRIGGERS = []


@router.message(F.text == "🏠 Меню")
async def back_to_menu_from_admin(message: Message, state: FSMContext):
    from keyboards import menu_kb
    await state.clear()
    await message.answer("🏠 Главное меню", reply_markup=safe_reply_kb(message, menu_kb))


def _give_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Деньги (кошелёк)",    callback_data="give_type:money")],
        [InlineKeyboardButton(text="🏦 Деньги (в банк)",      callback_data="give_type:bank")],
        [InlineKeyboardButton(text="₿ BTC",                   callback_data="give_type:btc")],
        [InlineKeyboardButton(text="💎 DC (донат монеты)",    callback_data="give_type:dc")],
        [InlineKeyboardButton(text="🎁 Донат-предмет",        callback_data="give_type:donate_item")],
        [InlineKeyboardButton(text="⭐ Уровень и XP",         callback_data="give_type:level")],
        [InlineKeyboardButton(text="❌ Отмена",               callback_data="new_admin_cancel")],
    ])


@router.message(F.text == "💵 Выдать")
async def handle_give_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not has_permission(user_id, "give_currency"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    rem = get_remaining_limit(user_id, "currency")
    rem_text = f"<b>{format_amount(rem)}$</b>" if rem is not None else "<b>∞</b>"

    if message.reply_to_message and message.reply_to_message.from_user:
        rid = message.reply_to_message.from_user.id
        recipient = get_user(rid)
        if recipient:
            await state.update_data(recipient_id=rid)
            name = recipient.get("name", "Без имени")
            await message.answer(
                f"💵 <b>Выдача → {name}</b>\n\n💰 Лимит: {rem_text}\n\nВыбери тип:",
                parse_mode="HTML", reply_markup=_give_menu_kb()
            )
            return

    await message.answer(
        f"💵 <b>Выдача</b>\n\n💰 Лимит: {rem_text}\n\nВведи ID / игровой ID / @username игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await state.set_state(NewAdminGiveState.waiting_user)


@router.message(NewAdminGiveState.waiting_user)
async def give_user_input(message: Message, state: FSMContext):
    uid, recipient = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден. Попробуйте снова.")
        return
    await state.update_data(recipient_id=uid)
    await message.answer(
        f"✅ Найден: <b>{recipient.get('name','Без имени')}</b>\n\nВыбери тип выдачи:",
        parse_mode="HTML", reply_markup=_give_menu_kb()
    )
    await state.set_state(None)


@router.message(NewAdminGiveState.waiting_amount)
async def give_amount_input(message: Message, state: FSMContext):
    amount = parse_k(message.text.strip())
    if amount is None or amount <= 0:
        await message.answer("❌ Некорректная сумма. Попробуйте снова.")
        return

    user_id = message.from_user.id
    ok, remaining = check_and_use_limit(user_id, "currency", amount)
    if not ok:
        rem_text = format_amount(remaining) if remaining is not None else "∞"
        await message.answer(f"⛔ Превышен дневной лимит!\nДоступно: <b>{rem_text}$</b>", parse_mode="HTML")
        await state.clear()
        return

    data = await state.get_data()
    recipient_id = data["recipient_id"]
    recipient = get_user(recipient_id)
    update_balance(recipient_id, get_balance(recipient_id) + amount)
    save_user_data()
    await state.clear()

    name = recipient.get("name", "Без имени")
    clickable = recipient.get("clickable_name", True)
    admin_name = message.from_user.full_name
    log_action(user_id, admin_name, "give_currency", recipient_id, f"+{format_amount(amount)}$")

    kb = _get_admin_kb(user_id)
    await message.answer(
        f"✅ Выдано <b>{format_amount(amount)}$</b> → {clickable_name(recipient_id, name, clickable)}",
        parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
    )
    try:
        await bot.send_message(recipient_id, f"💵 Вам выдали <b>{format_amount(amount)}$</b> от администратора.", parse_mode="HTML")
    except Exception:
        pass

    await _notify_founders_if_suspicious(user_id, admin_name, amount, recipient_id, name)


async def _notify_founders_if_suspicious(admin_id: int, admin_name: str, amount: int, target_id: int, target_name: str):
    role = get_role(admin_id)
    limits = DAILY_LIMITS.get(role, {})
    limit = limits.get("currency")
    if limit and amount >= limit * 0.8:
        for f_id in founders:
            try:
                await bot.send_message(
                    f_id,
                    f"⚠️ <b>Авто-уведомление</b>\n\n"
                    f"👤 {admin_name} (<code>{admin_id}</code>) [{ROLE_LABELS.get(role,'')}]\n"
                    f"💰 Выдал <b>{format_amount(amount)}$</b> → {target_name} (<code>{target_id}</code>)\n"
                    f"📊 Сумма составляет ≥80% дневного лимита!",
                    parse_mode="HTML"
                )
            except Exception:
                pass


def _take_menu_kb(recipient_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Деньги (кошелёк)",  callback_data="take_type:money")],
        [InlineKeyboardButton(text="🏦 Деньги (с банка)",   callback_data="take_type:bank")],
        [InlineKeyboardButton(text="₿ BTC",                 callback_data="take_type:btc")],
        [InlineKeyboardButton(text="💎 DC (донат монеты)",  callback_data="take_type:dc")],
        [InlineKeyboardButton(text="🎁 Донат-предмет",      callback_data="take_type:donate_item")],
        [InlineKeyboardButton(text="⭐ Уровень и XP",       callback_data=f"take_level_confirm:{recipient_id}")],
        [InlineKeyboardButton(text="❌ Отмена",             callback_data="new_admin_cancel")],
    ])


@router.message(F.text == "💸 Забрать")
async def handle_take_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not has_permission(user_id, "give_currency"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return

    if message.reply_to_message and message.reply_to_message.from_user:
        rid = message.reply_to_message.from_user.id
        recipient = get_user(rid)
        if recipient:
            await state.update_data(recipient_id=rid)
            name = recipient.get("name", "Без имени")
            await message.answer(
                f"💸 <b>Забрать у {name}</b>\n\nЧто именно забрать?",
                parse_mode="HTML", reply_markup=_take_menu_kb(rid)
            )
            return

    await state.set_state(AdminTakeState.waiting_user)
    await message.answer(
        "💸 <b>Забрать</b>\n\nВведи ID / игровой ID / @username игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )


@router.message(AdminTakeState.waiting_user)
async def take_user_input(message: Message, state: FSMContext):
    uid, recipient = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден. Попробуйте снова.")
        return
    await state.update_data(recipient_id=uid)
    name = recipient.get("name", "Без имени")
    await state.set_state(None)
    await message.answer(
        f"✅ Найден: <b>{name}</b>\n\nЧто именно забрать?",
        parse_mode="HTML", reply_markup=_take_menu_kb(uid)
    )


# ─── Выбор типа "забрать" ──────────────────────────────────────────

@router.callback_query(F.data.startswith("take_type:"))
async def cb_take_type(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "give_currency"):
        await callback.answer("Нет прав.", show_alert=True)
        return

    ttype = callback.data.split(":", 1)[1]
    data  = await state.get_data()
    pre   = data.get("recipient_id")

    if ttype == "money":
        if pre:
            u   = get_user(pre)
            bal = format_amount(get_balance(pre))
            await callback.message.answer(
                f"💵 <b>Забрать с кошелька → {u.get('name','?')}</b>\n"
                f"💰 Баланс: <b>{bal}$</b>\n\nВведи сумму (<code>все</code> — списать всё):",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminTakeState.waiting_amount)
        else:
            await callback.message.answer(
                "💵 <b>Забрать с кошелька</b>\n\nВведи ID / game_id / @username:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminTakeState.waiting_user)

    elif ttype == "bank":
        if pre:
            u    = get_user(pre)
            bank = format_amount(u.get("user_bank", 0))
            await callback.message.answer(
                f"🏦 <b>Забрать с банка → {u.get('name','?')}</b>\n"
                f"🏦 Банк: <b>{bank}$</b>\n\nВведи сумму (<code>все</code> — списать всё):",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminTakeBankState.waiting_amount)
        else:
            await callback.message.answer(
                "🏦 <b>Забрать с банка</b>\n\nВведи ID / game_id / @username:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminTakeState.waiting_user)
            await state.update_data(take_pending_type="bank")

    elif ttype == "btc":
        if pre:
            from farm import get_farm, flush_farm, _fmt_btc
            farm  = get_farm(pre)
            flush_farm(farm)
            save_user_data()
            btc_b = farm.get("btc_balance", 0.0)
            u = get_user(pre)
            await callback.message.answer(
                f"₿ <b>Забрать BTC → {u.get('name','?')}</b>\n"
                f"₿ BTC: <b>{_fmt_btc(btc_b)}</b>\n\nВведи количество (<code>все</code> — забрать всё):",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminTakeBtcState.waiting_amount)
        else:
            await callback.message.answer(
                "₿ <b>Забрать BTC</b>\n\nВведи ID / game_id / @username:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminTakeState.waiting_user)
            await state.update_data(take_pending_type="btc")

    elif ttype == "dc":
        if pre:
            u  = get_user(pre)
            dc = u.get("donate_coins", 0)
            await callback.message.answer(
                f"💎 <b>Забрать DC → {u.get('name','?')}</b>\n"
                f"💎 DC: <b>{dc}</b>\n\nВведи количество (<code>все</code> — забрать всё):",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminTakeDcState.waiting_amount)
        else:
            await callback.message.answer(
                "💎 <b>Забрать DC</b>\n\nВведи ID / game_id / @username:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminTakeState.waiting_user)
            await state.update_data(take_pending_type="dc")

    elif ttype == "donate_item":
        if not pre:
            await callback.message.answer(
                "🎁 <b>Забрать донат-предмет</b>\n\nВведи ID / game_id / @username:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminTakeState.waiting_user)
            await state.update_data(take_pending_type="donate_item")
        else:
            await _show_take_donate_menu(callback.message, pre)

    await callback.answer()


async def _show_take_donate_menu(msg, recipient_id):
    from donate import get_donate_user_data, DONATE_BUSINESSES, DONATE_HOUSES, DONATE_CARS
    u   = get_user(recipient_id)
    don = get_donate_user_data(u)
    rows = []

    if don.get("vip"):
        rows.append([InlineKeyboardButton(text="⭐ VIP статус", callback_data=f"take_ditem:{recipient_id}:vip")])
    biz_key = don.get("business")
    if biz_key and biz_key in DONATE_BUSINESSES:
        rows.append([InlineKeyboardButton(
            text=f"💼 {DONATE_BUSINESSES[biz_key]['name']}",
            callback_data=f"take_ditem:{recipient_id}:biz:{biz_key}"
        )])
    house_key = don.get("house")
    if house_key and house_key in DONATE_HOUSES:
        rows.append([InlineKeyboardButton(
            text=f"🏛 {DONATE_HOUSES[house_key]['name']}",
            callback_data=f"take_ditem:{recipient_id}:house:{house_key}"
        )])
    car_key = don.get("car")
    if car_key and car_key in DONATE_CARS:
        rows.append([InlineKeyboardButton(
            text=f"🏎 {DONATE_CARS[car_key]['name']}",
            callback_data=f"take_ditem:{recipient_id}:car:{car_key}"
        )])

    if not rows:
        await msg.answer(
            f"ℹ️ У <b>{u.get('name','?')}</b> нет донат-предметов.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="new_admin_cancel")]
            ])
        )
        return

    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="new_admin_cancel")])
    await msg.answer(
        f"🎁 <b>Донат-предметы {u.get('name','?')}</b>\n\nВыбери что забрать:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


# ─── Когда пользователь введён без reply, и тип уже выбран ─────────

@router.message(AdminTakeState.waiting_user)
async def take_user_input(message: Message, state: FSMContext):
    uid, recipient = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден. Попробуйте снова.")
        return
    data = await state.get_data()
    pending = data.get("take_pending_type")
    await state.update_data(recipient_id=uid)
    name = recipient.get("name", "Без имени")

    if pending == "bank":
        bank = format_amount(recipient.get("user_bank", 0))
        await message.answer(
            f"🏦 <b>Забрать с банка → {name}</b>\n🏦 Банк: <b>{bank}$</b>\n\nВведи сумму:",
            parse_mode="HTML", reply_markup=_CANCEL_KB
        )
        await state.set_state(AdminTakeBankState.waiting_amount)
    elif pending == "btc":
        from farm import get_farm, flush_farm, _fmt_btc
        farm = get_farm(uid)
        flush_farm(farm)
        save_user_data()
        btc_b = farm.get("btc_balance", 0.0)
        await message.answer(
            f"₿ <b>Забрать BTC → {name}</b>\n₿ BTC: <b>{_fmt_btc(btc_b)}</b>\n\nВведи количество:",
            parse_mode="HTML", reply_markup=_CANCEL_KB
        )
        await state.set_state(AdminTakeBtcState.waiting_amount)
    elif pending == "dc":
        dc = recipient.get("donate_coins", 0)
        await message.answer(
            f"💎 <b>Забрать DC → {name}</b>\n💎 DC: <b>{dc}</b>\n\nВведи количество:",
            parse_mode="HTML", reply_markup=_CANCEL_KB
        )
        await state.set_state(AdminTakeDcState.waiting_amount)
    elif pending == "donate_item":
        await _show_take_donate_menu(message, uid)
        await state.set_state(None)
    else:
        await state.set_state(None)
        await message.answer(
            f"✅ Найден: <b>{name}</b>\n\nЧто именно забрать?",
            parse_mode="HTML", reply_markup=_take_menu_kb(uid)
        )


# ─── Деньги (кошелёк) ─────────────────────────────────────────────

@router.message(AdminTakeState.waiting_amount)
async def take_money_input(message: Message, state: FSMContext):
    data         = await state.get_data()
    recipient_id = data["recipient_id"]
    recipient    = get_user(recipient_id)
    current_bal  = get_balance(recipient_id)

    txt = message.text.strip().lower()
    if txt in ("все", "all", "max"):
        amount = current_bal
    else:
        amount = parse_k(txt)
    if amount is None or amount <= 0:
        await message.answer("❌ Некорректная сумма.")
        return
    if amount > current_bal:
        await message.answer(f"⚠️ У игрока только <b>{format_amount(current_bal)}$</b>. Спишу всё.", parse_mode="HTML")
        amount = current_bal

    update_balance(recipient_id, current_bal - amount)
    save_user_data()
    await state.clear()

    user_id  = message.from_user.id
    name     = recipient.get("name", "Без имени")
    cl       = recipient.get("clickable_name", True)
    log_action(user_id, message.from_user.full_name, "take_currency", recipient_id, f"-{format_amount(amount)}$")
    kb = _get_admin_kb(user_id)
    await message.answer(
        f"✅ Списано <b>{format_amount(amount)}$</b> с кошелька {clickable_name(recipient_id, name, cl)}",
        parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
    )
    try:
        await bot.send_message(recipient_id, f"💸 Администратор списал <b>{format_amount(amount)}$</b> с вашего кошелька.", parse_mode="HTML")
    except Exception:
        pass


# ─── Банк ─────────────────────────────────────────────────────────

@router.message(AdminTakeBankState.waiting_amount)
async def take_bank_input(message: Message, state: FSMContext):
    data         = await state.get_data()
    recipient_id = data["recipient_id"]
    recipient    = get_user(recipient_id)
    current_bank = recipient.get("user_bank", 0)

    txt = message.text.strip().lower()
    if txt in ("все", "all", "max"):
        amount = current_bank
    else:
        amount = parse_k(txt)
    if amount is None or amount <= 0:
        await message.answer("❌ Некорректная сумма.")
        return
    if amount > current_bank:
        await message.answer(f"⚠️ В банке только <b>{format_amount(current_bank)}$</b>. Спишу всё.", parse_mode="HTML")
        amount = current_bank

    recipient["user_bank"] = current_bank - amount
    save_user_data()
    await state.clear()

    user_id = message.from_user.id
    name    = recipient.get("name", "Без имени")
    cl      = recipient.get("clickable_name", True)
    log_action(user_id, message.from_user.full_name, "take_bank", recipient_id, f"-{format_amount(amount)}$")
    kb = _get_admin_kb(user_id)
    await message.answer(
        f"✅ Списано <b>{format_amount(amount)}$</b> с банка {clickable_name(recipient_id, name, cl)}",
        parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
    )
    try:
        await bot.send_message(recipient_id, f"🏦 Администратор списал <b>{format_amount(amount)}$</b> с вашего банковского счёта.", parse_mode="HTML")
    except Exception:
        pass


# ─── BTC ──────────────────────────────────────────────────────────

@router.message(AdminTakeBtcState.waiting_amount)
async def take_btc_input(message: Message, state: FSMContext):
    from farm import get_farm, flush_farm, _fmt_btc
    data         = await state.get_data()
    recipient_id = data["recipient_id"]
    recipient    = get_user(recipient_id)
    farm         = get_farm(recipient_id)
    flush_farm(farm)
    save_user_data()
    current_btc = farm.get("btc_balance", 0.0)

    txt = message.text.strip().lower()
    if txt in ("все", "all", "max"):
        amount = current_btc
    else:
        try:
            amount = round(float(txt.replace(",", ".")), 6)
        except ValueError:
            await message.answer("❌ Введи число BTC, например <code>0.5</code>", parse_mode="HTML")
            return
    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше 0.")
        return
    if amount > current_btc + 1e-9:
        await message.answer(f"⚠️ У игрока только <b>{_fmt_btc(current_btc)} BTC</b>. Спишу всё.", parse_mode="HTML")
        amount = current_btc

    farm["btc_balance"] = round(current_btc - amount, 6)
    save_user_data()
    await state.clear()

    user_id = message.from_user.id
    name    = recipient.get("name", "Без имени")
    cl      = recipient.get("clickable_name", True)
    log_action(user_id, message.from_user.full_name, "take_btc", recipient_id, f"-{_fmt_btc(amount)} BTC")
    kb = _get_admin_kb(user_id)
    await message.answer(
        f"✅ Списано <b>{_fmt_btc(amount)} BTC</b> у {clickable_name(recipient_id, name, cl)}",
        parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
    )
    try:
        await bot.send_message(recipient_id, f"₿ Администратор списал <b>{_fmt_btc(amount)} BTC</b> с вашего кошелька.", parse_mode="HTML")
    except Exception:
        pass


# ─── DC ───────────────────────────────────────────────────────────

@router.message(AdminTakeDcState.waiting_amount)
async def take_dc_input(message: Message, state: FSMContext):
    data         = await state.get_data()
    recipient_id = data["recipient_id"]
    recipient    = get_user(recipient_id)
    current_dc   = recipient.get("donate_coins", 0)

    txt = message.text.strip().lower()
    if txt in ("все", "all", "max"):
        amount = current_dc
    else:
        try:
            amount = int(txt)
        except ValueError:
            await message.answer("❌ Введи целое число DC.")
            return
    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше 0.")
        return
    if amount > current_dc:
        await message.answer(f"⚠️ У игрока только <b>{current_dc} DC</b>. Спишу всё.", parse_mode="HTML")
        amount = current_dc

    recipient["donate_coins"] = current_dc - amount
    save_user_data()
    await state.clear()

    user_id = message.from_user.id
    name    = recipient.get("name", "Без имени")
    cl      = recipient.get("clickable_name", True)
    log_action(user_id, message.from_user.full_name, "take_dc", recipient_id, f"-{amount} DC")
    kb = _get_admin_kb(user_id)
    await message.answer(
        f"✅ Списано <b>{amount} DC</b> у {clickable_name(recipient_id, name, cl)}",
        parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
    )
    try:
        await bot.send_message(recipient_id, f"💎 Администратор списал <b>{amount} DC</b> с вашего счёта.", parse_mode="HTML")
    except Exception:
        pass


# ─── Донат-предмет (забрать) ───────────────────────────────────────

@router.callback_query(F.data.startswith("take_ditem:"))
async def cb_take_ditem(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "give_currency"):
        await callback.answer("Нет прав.", show_alert=True)
        return

    parts        = callback.data.split(":", 3)
    recipient_id = int(parts[1])
    item_type    = parts[2]
    item_key     = parts[3] if len(parts) > 3 else None

    from donate import get_donate_user_data, DONATE_BUSINESSES, DONATE_HOUSES, DONATE_CARS
    u   = get_user(recipient_id)
    don = get_donate_user_data(u)

    if item_type == "vip":
        don["vip"] = False
        item_label = "⭐ VIP статус"
    elif item_type == "biz":
        don["business"]         = None
        don["biz_last_collect"] = None
        item_label = DONATE_BUSINESSES.get(item_key, {}).get("name", item_key) if item_key else "Бизнес"
    elif item_type == "house":
        don["house"] = None
        item_label = DONATE_HOUSES.get(item_key, {}).get("name", item_key) if item_key else "Дом"
    elif item_type == "car":
        don["car"] = None
        item_label = DONATE_CARS.get(item_key, {}).get("name", item_key) if item_key else "Авто"
    else:
        await callback.answer("❌ Неизвестный предмет.", show_alert=True)
        return

    save_user_data()
    await state.clear()

    user_id    = callback.from_user.id
    admin_name = callback.from_user.full_name
    name       = u.get("name", "?")
    cl         = u.get("clickable_name", True)
    log_action(user_id, admin_name, "take_donate_item", recipient_id, f"-{item_label}")

    kb = _get_admin_kb(user_id)
    await callback.message.answer(
        f"✅ Забран <b>{item_label}</b> у {clickable_name(recipient_id, name, cl)}",
        parse_mode="HTML", reply_markup=safe_reply_kb(callback.message, kb)
    )
    try:
        await bot.send_message(recipient_id, f"🎁 Администратор забрал <b>{item_label}</b> с вашего аккаунта.", parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


# ─── Уровень и XP (забрать) ────────────────────────────────────────

@router.callback_query(F.data.startswith("take_level_confirm:"))
async def cb_take_level_confirm(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "give_currency"):
        await callback.answer("Нет прав.", show_alert=True)
        return

    parts = callback.data.split(":", 1)
    recipient_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

    if not recipient_id:
        await callback.answer("❌ Игрок не найден.", show_alert=True)
        return

    u    = get_user(recipient_id)
    name = u.get("name", "?")
    cl   = u.get("clickable_name", True)
    old_level = u.get("level", 1)
    old_xp    = u.get("experience", 0)

    u["level"]      = 1
    u["experience"] = 0
    save_user_data()

    admin_id   = callback.from_user.id
    admin_name = callback.from_user.full_name
    log_action(admin_id, admin_name, "take_level", recipient_id, f"lvl {old_level} xp {old_xp} → lvl 1 xp 0")

    kb = _get_admin_kb(admin_id)
    await callback.message.answer(
        f"✅ Уровень и XP сброшены у {clickable_name(recipient_id, name, cl)}\n"
        f"📉 Было: <b>Лвл {old_level}</b> / <b>{old_xp} XP</b>\n"
        f"📌 Стало: <b>Лвл 1</b> / <b>0 XP</b>",
        parse_mode="HTML", reply_markup=safe_reply_kb(callback.message, kb)
    )
    try:
        await bot.send_message(
            recipient_id,
            "📉 Администратор сбросил ваш <b>уровень и XP</b> до начального.",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer()
    await state.clear()


def _reset_menu_kb(user_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="👤 Обнулить игрока",          callback_data="reset_type:player")],
    ]
    if get_role(user_id) in (ROLE_FOUNDER, ROLE_ZAM_LD):
        rows.append([InlineKeyboardButton(text="☢️ ВАЙП СЕРВЕРА (все игроки)", callback_data="reset_type:wipe")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="new_admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text == "🗑️ Обнулить")
async def handle_reset_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not has_permission(user_id, "reset_user"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return

    if message.reply_to_message and message.reply_to_message.from_user:
        rid = message.reply_to_message.from_user.id
        recipient = get_user(rid)
        if not recipient:
            await message.answer("❌ Пользователь не зарегистрирован.")
            return
        name = recipient.get("name", "?")
        await state.update_data(recipient_id=rid, recipient_name=name)
        await message.answer(
            f"⚠️ Обнулить <b>{name}</b> (ID: <code>{rid}</code>)?\n\nНапишите <code>да</code> или <code>нет</code>.",
            parse_mode="HTML"
        )
        await state.set_state(NewAdminResetState.waiting_confirm)
        return

    await message.answer(
        "🗑️ <b>Меню обнуления</b>\n\nВыбери действие:",
        parse_mode="HTML", reply_markup=_reset_menu_kb(user_id)
    )


@router.message(NewAdminResetState.waiting_user)
async def reset_user_input(message: Message, state: FSMContext):
    data = await state.get_data()
    uid, recipient = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден.")
        return
    await state.update_data(recipient_id=uid, recipient_name=recipient.get("name", "Без имени"))
    await message.answer(
        f"⚠️ Вы уверены, что хотите обнулить <b>{recipient.get('name','?')}</b> (ID: {uid})?\n\n"
        "Напишите <code>да</code> или <code>нет</code>.",
        parse_mode="HTML"
    )
    await state.set_state(NewAdminResetState.waiting_confirm)


@router.message(NewAdminResetState.waiting_confirm)
async def reset_confirm(message: Message, state: FSMContext):
    ans = message.text.strip().lower()
    if ans == "да":
        data = await state.get_data()
        rid = data["recipient_id"]
        rname = data["recipient_name"]
        reset_user_data(rid)
        await state.clear()
        admin_name = message.from_user.full_name
        log_action(message.from_user.id, admin_name, "reset_user", rid, rname)
        kb = _get_admin_kb(message.from_user.id)
        await message.answer(f"✅ Аккаунт <b>{rname}</b> обнулён.", parse_mode="HTML", reply_markup=safe_reply_kb(message, kb))
        try:
            await bot.send_message(rid, "🗑️ Ваш аккаунт был обнулён администратором.", parse_mode="HTML")
        except Exception:
            pass
    elif ans == "нет":
        await state.clear()
        kb = _get_admin_kb(message.from_user.id)
        await message.answer("❌ Отменено.", reply_markup=safe_reply_kb(message, kb))
    else:
        await message.answer("❓ Напишите <code>да</code> или <code>нет</code>.", parse_mode="HTML")


@router.message(F.text == "🛠️ Установить")
async def handle_set_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not has_permission(user_id, "set_data"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    from keyboards import get_admin_set_kb
    await message.answer("🛠️ Что установить?", reply_markup=get_admin_set_kb(user_id))


@router.callback_query(F.data.in_({"set_name", "set_game_id", "set_balance", "set_bank"}))
async def set_field_cb(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "set_data"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    field_map = {"set_name": "name", "set_game_id": "game_id", "set_balance": "balance", "set_bank": "bank"}
    field = field_map[callback.data]
    await state.update_data(field=field)
    await callback.message.answer("Введите ID, игровой ID или @юзернейм пользователя:")
    await state.set_state(NewAdminSetState.waiting_user)
    await callback.answer()


@router.message(NewAdminSetState.waiting_user)
async def set_user_input(message: Message, state: FSMContext):
    uid, recipient = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден.")
        return
    await state.update_data(recipient_id=uid, recipient_name=recipient.get("name", "Без имени"))
    data = await state.get_data()
    prompts = {"name": "Введите новый ник:", "game_id": "Введите новый игровой ID:", "balance": "Введите новый баланс:", "bank": "Введите новую сумму банка:"}
    await message.answer(prompts.get(data["field"], "Введите значение:"))
    await state.set_state(NewAdminSetState.waiting_value)


@router.message(NewAdminSetState.waiting_value)
async def set_value_input(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data["field"]
    value = message.text.strip()
    if field == "game_id":
        if not value.isdigit():
            await message.answer("❌ ID должен быть числом.")
            return
    elif field in ("balance", "bank"):
        v = parse_k(value)
        if v is None or v < 0:
            await message.answer("❌ Сумма должна быть положительным числом.")
            return
        value = v
    elif field == "name":
        if len(value) > 30:
            await message.answer("❌ Ник слишком длинный (макс. 30 символов).")
            return
    await state.update_data(value=value)
    await message.answer(
        f"Подтвердить изменение <b>{field}</b> → <code>{value}</code> для пользователя <b>{data['recipient_name']}</b>?\n\n"
        "Напишите <code>да</code> или <code>нет</code>.",
        parse_mode="HTML"
    )
    await state.set_state(NewAdminSetState.waiting_confirm)


@router.message(NewAdminSetState.waiting_confirm)
async def set_confirm(message: Message, state: FSMContext):
    ans = message.text.strip().lower()
    if ans == "да":
        data = await state.get_data()
        rid = data["recipient_id"]
        field = data["field"]
        value = data["value"]
        recipient = get_user(rid)
        if not recipient:
            await message.answer("❌ Пользователь не найден.")
            await state.clear()
            return
        if field == "game_id":
            new_gid = int(value)
            for other_uid, other_u in utils.user_data.items():
                if str(other_uid) != str(rid) and other_u.get("game_id") == new_gid:
                    await message.answer(f"❌ Game ID <code>{new_gid}</code> уже занят другим игроком.", parse_mode="HTML")
                    await state.clear()
                    return
            recipient["game_id"] = new_gid
        elif field == "balance":
            recipient["balance"] = int(value)
        elif field == "name":
            recipient["name"] = value
        elif field == "bank":
            recipient["user_bank"] = int(value)
        save_user_data()
        await state.clear()
        admin_name = message.from_user.full_name
        log_action(message.from_user.id, admin_name, f"set_{field}", rid, str(value))
        kb = _get_admin_kb(message.from_user.id)
        await message.answer(f"✅ <b>{field}</b> обновлён.", parse_mode="HTML", reply_markup=safe_reply_kb(message, kb))
    elif ans == "нет":
        await state.clear()
        kb = _get_admin_kb(message.from_user.id)
        await message.answer("❌ Отменено.", reply_markup=safe_reply_kb(message, kb))
    else:
        await message.answer("❓ Напишите <code>да</code> или <code>нет</code>.", parse_mode="HTML")


@router.callback_query(F.data == "cancel_set")
async def cancel_set_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = _get_admin_kb(callback.from_user.id)
    await callback.message.answer("❌ Отменено.", reply_markup=safe_reply_kb(callback.message, kb))
    await callback.answer()


@router.message(F.text == "🚫 Бан")
async def handle_ban_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not has_permission(user_id, "ban"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отмена", callback_data="new_admin_cancel")
    ]])
    await message.answer("🚫 <b>Бан игрока</b>\n\nВведите ID или @юзернейм:", parse_mode="HTML", reply_markup=cancel_kb)
    await state.set_state(BanState.waiting_user)


@router.message(BanState.waiting_user)
async def ban_user_input(message: Message, state: FSMContext):
    uid, recipient = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден.")
        return

    admin_id = message.from_user.id
    target_role = get_role(uid)
    my_role = get_role(admin_id)
    protected = {ROLE_FOUNDER, ROLE_ZAM_LD}
    if my_role == ROLE_ADMIN and target_role in protected:
        await message.answer("⛔ Нельзя банить Founder или Зам ЛД.")
        await state.clear()
        return
    if my_role == ROLE_ZAM_LD and target_role == ROLE_FOUNDER:
        await message.answer("⛔ Нельзя банить Founder.")
        await state.clear()
        return

    await state.update_data(recipient_id=uid, recipient_name=recipient.get("name", "Без имени"))
    role = get_role(admin_id)
    if role == ROLE_FOUNDER:
        await message.answer("🕐 Введите количество дней (0 = навсегда):")
    else:
        await message.answer("🕐 Введите количество дней (макс. 30):")
    await state.set_state(BanState.waiting_days)


@router.message(BanState.waiting_days)
async def ban_days_input(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ Введите число дней.")
        return
    days = int(text)
    admin_id = message.from_user.id
    role = get_role(admin_id)
    if role == ROLE_ADMIN and days > 30:
        await message.answer("⛔ Максимальный срок бана для Admin — 30 дней.")
        return

    data = await state.get_data()
    rid = data["recipient_id"]
    rname = data["recipient_name"]
    bans = _load_bans()
    if days == 0:
        bans[str(rid)] = {"permanent": True, "by": admin_id, "ts": time.time()}
        duration_text = "навсегда"
    else:
        bans[str(rid)] = {"until": time.time() + days * 86400, "by": admin_id, "ts": time.time()}
        duration_text = f"{days} дн."
    _save_bans(bans)
    await state.clear()
    log_action(admin_id, message.from_user.full_name, "ban", rid, f"{rname} на {duration_text}")
    kb = _get_admin_kb(admin_id)
    await message.answer(f"🚫 Игрок <b>{rname}</b> заблокирован на {duration_text}.", parse_mode="HTML", reply_markup=safe_reply_kb(message, kb))
    try:
        await bot.send_message(rid, f"🚫 Ваш аккаунт заблокирован на {duration_text}.", parse_mode="HTML")
    except Exception:
        pass


@router.message(F.text == "🔇 Мут")
async def handle_mute_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not has_permission(user_id, "mute"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отмена", callback_data="new_admin_cancel")
    ]])
    await message.answer("🔇 <b>Мут игрока</b>\n\nВведите ID или @юзернейм:", parse_mode="HTML", reply_markup=cancel_kb)
    await state.set_state(MuteState.waiting_user)


@router.message(MuteState.waiting_user)
async def mute_user_input(message: Message, state: FSMContext):
    uid, recipient = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден.")
        return
    await state.update_data(recipient_id=uid, recipient_name=recipient.get("name", "Без имени"))
    await message.answer("🕐 Введите количество часов (0 = навсегда):")
    await state.set_state(MuteState.waiting_hours)


@router.message(MuteState.waiting_hours)
async def mute_hours_input(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ Введите число часов.")
        return
    hours = int(text)
    data = await state.get_data()
    rid = data["recipient_id"]
    rname = data["recipient_name"]
    mutes = _load_mutes()
    if hours == 0:
        mutes[str(rid)] = {"permanent": True, "by": message.from_user.id, "ts": time.time()}
        duration_text = "навсегда"
    else:
        mutes[str(rid)] = {"until": time.time() + hours * 3600, "by": message.from_user.id, "ts": time.time()}
        duration_text = f"{hours} ч."
    _save_mutes(mutes)
    await state.clear()
    log_action(message.from_user.id, message.from_user.full_name, "mute", rid, f"{rname} на {duration_text}")
    kb = _get_admin_kb(message.from_user.id)
    await message.answer(f"🔇 Игрок <b>{rname}</b> замьючен на {duration_text}.", parse_mode="HTML", reply_markup=safe_reply_kb(message, kb))
    try:
        await bot.send_message(rid, f"🔇 Вы были замьючены на {duration_text}.", parse_mode="HTML")
    except Exception:
        pass


@router.message(F.text == "🔓 Разбан")
async def handle_unban_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not has_permission(user_id, "ban"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отмена", callback_data="new_admin_cancel")
    ]])
    await message.answer("🔓 <b>Снять бан</b>\n\nВведите ID или @юзернейм:", parse_mode="HTML", reply_markup=cancel_kb)
    await state.set_state(UnbanState.waiting_user)


@router.message(UnbanState.waiting_user)
async def unban_user_input(message: Message, state: FSMContext):
    uid, recipient = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден.")
        return
    bans = _load_bans()
    if str(uid) not in bans:
        await message.answer("ℹ️ Этот игрок не забанен.")
        await state.clear()
        return
    del bans[str(uid)]
    _save_bans(bans)
    rname = recipient.get("name", "Без имени")
    admin_id = message.from_user.id
    log_action(admin_id, message.from_user.full_name, "unban", uid, rname)
    kb = _get_admin_kb(admin_id)
    await state.clear()
    await message.answer(f"✅ Бан снят с игрока <b>{rname}</b>.", parse_mode="HTML", reply_markup=safe_reply_kb(message, kb))
    try:
        await bot.send_message(uid, "✅ Ваш бан был снят администратором.")
    except Exception:
        pass


@router.message(F.text == "🔈 Снять мут")
async def handle_unmute_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not has_permission(user_id, "mute"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отмена", callback_data="new_admin_cancel")
    ]])
    await message.answer("🔈 <b>Снять мут</b>\n\nВведите ID или @юзернейм:", parse_mode="HTML", reply_markup=cancel_kb)
    await state.set_state(UnmuteState.waiting_user)


@router.message(UnmuteState.waiting_user)
async def unmute_user_input(message: Message, state: FSMContext):
    uid, recipient = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден.")
        return
    mutes = _load_mutes()
    if str(uid) not in mutes:
        await message.answer("ℹ️ Этот игрок не замьючен.")
        await state.clear()
        return
    del mutes[str(uid)]
    _save_mutes(mutes)
    rname = recipient.get("name", "Без имени")
    admin_id = message.from_user.id
    log_action(admin_id, message.from_user.full_name, "unmute", uid, rname)
    kb = _get_admin_kb(admin_id)
    await state.clear()
    await message.answer(f"🔈 Мут снят с игрока <b>{rname}</b>.", parse_mode="HTML", reply_markup=safe_reply_kb(message, kb))
    try:
        await bot.send_message(uid, "🔈 Ваш мут был снят администратором.")
    except Exception:
        pass


@router.message(F.text == "⚠️ Варн")
async def handle_warn_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not has_permission(user_id, "warn"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отмена", callback_data="new_admin_cancel")
    ]])
    await message.answer("⚠️ <b>Выдать варн</b>\n\nВведите ID или @юзернейм:", parse_mode="HTML", reply_markup=cancel_kb)
    await state.set_state(WarnState.waiting_user)


@router.message(WarnState.waiting_user)
async def warn_user_input(message: Message, state: FSMContext):
    uid, recipient = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден.")
        return
    await state.update_data(recipient_id=uid, recipient_name=recipient.get("name", "Без имени"))
    await message.answer("📋 Введите причину варна:")
    await state.set_state(WarnState.waiting_reason)


@router.message(WarnState.waiting_reason)
async def warn_reason_input(message: Message, state: FSMContext):
    from group_commands import add_warn, get_warns, clear_warns, MAX_WARNS
    reason = message.text.strip()
    data = await state.get_data()
    rid = data["recipient_id"]
    rname = data["recipient_name"]
    admin_id = message.from_user.id

    warn_count = add_warn(rid, admin_id, reason)
    log_action(admin_id, message.from_user.full_name, "warn", rid, f"{rname}: {reason}")
    kb = _get_admin_kb(admin_id)
    await state.clear()

    if warn_count >= MAX_WARNS:
        bans = _load_bans()
        bans[str(rid)] = {"permanent": True, "by": admin_id, "ts": time.time()}
        _save_bans(bans)
        clear_warns(rid)
        await message.answer(
            f"⚠️ Варн выдан игроку <b>{rname}</b>.\n"
            f"🚫 <b>Автобан!</b> Достигнут лимит варнов ({MAX_WARNS}/{MAX_WARNS}).",
            parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
        )
        try:
            await bot.send_message(rid, f"⚠️ Вам выдан варн: {reason}\n🚫 Вы автоматически забанены за {MAX_WARNS} варна.")
        except Exception:
            pass
    else:
        await message.answer(
            f"⚠️ Варн выдан игроку <b>{rname}</b>.\n"
            f"📊 Варнов: <b>{warn_count}/{MAX_WARNS}</b>\nПричина: {reason}",
            parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
        )
        try:
            await bot.send_message(rid, f"⚠️ Вам выдан варн администратором.\nПричина: {reason}\nВарнов: {warn_count}/{MAX_WARNS}")
        except Exception:
            pass


@router.message(F.text == "✅ Снять варн")
async def handle_unwarn_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not has_permission(user_id, "warn"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отмена", callback_data="new_admin_cancel")
    ]])
    await message.answer("✅ <b>Снять варн</b>\n\nВведите ID или @юзернейм:", parse_mode="HTML", reply_markup=cancel_kb)
    await state.set_state(UnwarnState.waiting_user)


@router.message(UnwarnState.waiting_user)
async def unwarn_user_input(message: Message, state: FSMContext):
    from group_commands import remove_last_warn, get_warns, MAX_WARNS
    uid, recipient = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден.")
        return
    rname = recipient.get("name", "Без имени")
    admin_id = message.from_user.id
    removed = remove_last_warn(uid)
    current = len(get_warns(uid))
    log_action(admin_id, message.from_user.full_name, "unwarn", uid, rname)
    kb = _get_admin_kb(admin_id)
    await state.clear()
    if removed:
        await message.answer(
            f"✅ Варн снят с игрока <b>{rname}</b>.\n"
            f"📊 Осталось варнов: <b>{current}/{MAX_WARNS}</b>",
            parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
        )
    else:
        await message.answer(
            f"ℹ️ У игрока <b>{rname}</b> нет активных варнов.",
            parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
        )


# ──────────────────────────────────────────────
#  КНОПКИ МОДЕРА — Жалобы / Репорты
# ──────────────────────────────────────────────

@router.message(F.text == "📨 Жалобы")
async def handle_complaints_button(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "view_complaints") and \
       not has_permission(user_id, "answer_complaints"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    await message.answer(
        "📨 <b>Жалобы</b>\n\nОткрой панель управления:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📨 Открыть жалобы", callback_data="ip_complaints")
        ]])
    )


@router.message(F.text == "📋 Репорты")
async def handle_reports_button(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "view_reports") and \
       not has_permission(user_id, "check_reports"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    await message.answer(
        "📋 <b>Репорты</b>\n\nОткрой панель управления:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📋 Открыть репорты", callback_data="ip_reports")
        ]])
    )


# ──────────────────────────────────────────────
#  КНОПКИ ДИЗАЙНЕРА — Редактор текстов / Эмодзи / Сообщения
# ──────────────────────────────────────────────

@router.message(F.text == "🎨 Редактор текстов")
async def handle_edit_texts_button(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "edit_texts"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    await message.answer(
        "🎨 <b>Редактор текстов</b>\n\nОткрой редактор:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🎨 Редактор текстов", callback_data="ip_edit_texts")
        ]])
    )


@router.message(F.text == "😊 Редактор эмодзи")
async def handle_edit_emoji_button(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "edit_texts"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    await message.answer(
        "😊 <b>Редактор эмодзи</b>\n\nОткрой редактор:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="😊 Редактор эмодзи", callback_data="ip_edit_emoji")
        ]])
    )


@router.message(F.text == "📝 Сообщения бота")
async def handle_bot_msgs_button(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "edit_texts"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    await message.answer(
        "📝 <b>Сообщения бота</b>\n\nОткрой редактор:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📝 Сообщения бота", callback_data="ip_bot_msgs")
        ]])
    )


@router.message(F.text == "📊 Логи")
async def handle_logs_button(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "view_logs"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    logs = get_logs(limit=20)
    text = "📊 <b>Последние 20 действий:</b>\n\n" + format_logs(logs)
    await message.answer(text[:4096], parse_mode="HTML")


def _get_all_admins_ordered():
    from admin_roles import (founders, zam_ld_list, tech_admins, admins_list,
                             designers_list, moders_list, followers_list, get_all_dynamic_roles)
    dynamic = get_all_dynamic_roles()
    seen = set()
    result = []

    # Founders — не снимаются (is_dynamic=False)
    for uid in founders:
        if uid not in seen:
            seen.add(uid)
            result.append((uid, ROLE_FOUNDER, "👑", False))

    # Все остальные env-var роли — снимаемые (is_dynamic=True)
    static_revokable = [
        (zam_ld_list,    ROLE_ZAM_LD,      "⭐"),
        (tech_admins,    ROLE_TECH_ADMIN,   "🛡"),
        (admins_list,    ROLE_ADMIN,        "👮"),
        (designers_list, ROLE_DESIGNER,     "🎨"),
        (moders_list,    ROLE_MODER,        "🛡"),
        (followers_list, ROLE_FOLLOWER,     "👁"),
    ]
    for uid_list, role, icon in static_revokable:
        for uid in uid_list:
            if uid not in seen:
                seen.add(uid)
                result.append((uid, role, icon, True))

    # Динамические роли (назначенные через бот)
    role_order = [
        (ROLE_ZAM_LD,     "⭐"),
        (ROLE_TECH_ADMIN, "🛡"),
        (ROLE_ADMIN,      "👮"),
        (ROLE_DESIGNER,   "🎨"),
        (ROLE_MODER,      "🛡"),
    ]
    for role, icon in role_order:
        for uid_str, r in dynamic.items():
            if r == role:
                uid = int(uid_str)
                if uid not in seen:
                    seen.add(uid)
                    result.append((uid, role, icon, True))

    return result


_ROLE_DESCRIPTIONS = {
    ROLE_FOUNDER:    "Полный доступ. Управление всей системой, ролями, базой данных и конфигурацией.",
    ROLE_ZAM_LD:     "Широкий доступ. Управление командой, выдача и снятие ролей, промо, магазин.",
    ROLE_TECH_ADMIN: "Системный доступ. Логи, безопасность, антиспам, база данных.",
    ROLE_ADMIN:      "Базовый доступ. Работа с игроками: выдача, баны, муты, промо.",
}

_ROLE_PERMS_READABLE = {
    ROLE_FOUNDER:    "Выдача • Баны • Муты • Промо • Роли • Система • API",
    ROLE_ZAM_LD:     "Выдача • Баны • Муты • Промо • Роли • Магазин",
    ROLE_TECH_ADMIN: "Выдача • Логи • Система • БД • Антиспам",
    ROLE_ADMIN:      "Выдача • Баны • Муты • Промо • Отчёты",
}


def _admins_list_kb(admins: list) -> InlineKeyboardMarkup:
    rows = []
    for idx, (uid, role, icon, _) in enumerate(admins):
        user = get_user(uid)
        name = user.get("name", "Без имени") if user else "Неизвестно"
        label = ROLE_LABELS.get(role, role)
        rows.append([InlineKeyboardButton(
            text=f"{icon} {name}  •  {label}",
            callback_data=f"alist_nav:{idx}"
        )])
    rows.append([InlineKeyboardButton(text="➕ Назначить по ID", callback_data="alist_assign")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _admin_action_kb(idx: int, uid: int, role: str, is_dynamic: bool, total: int) -> InlineKeyboardMarkup:
    rows = []

    prev_idx = (idx - 1) % total
    next_idx = (idx + 1) % total
    rows.append([
        InlineKeyboardButton(text="◀️", callback_data=f"alist_nav:{prev_idx}"),
        InlineKeyboardButton(text=f"{idx + 1} / {total}", callback_data="alist_noop"),
        InlineKeyboardButton(text="▶️", callback_data=f"alist_nav:{next_idx}"),
    ])

    promote_map = {
        ROLE_ADMIN:      (ROLE_TECH_ADMIN, "⬆️ Повысить"),
        ROLE_TECH_ADMIN: (ROLE_ZAM_LD,    "⬆️ Повысить"),
    }
    demote_map = {
        ROLE_ZAM_LD:     (ROLE_TECH_ADMIN, "⬇️ Понизить"),
        ROLE_TECH_ADMIN: (ROLE_ADMIN,      "⬇️ Понизить"),
    }

    action_row = []
    if is_dynamic and role in promote_map:
        new_role, plabel = promote_map[role]
        action_row.append(InlineKeyboardButton(
            text=plabel, callback_data=f"alist_promote:{uid}:{new_role}:{idx}"
        ))
    if is_dynamic and role in demote_map:
        new_role, dlabel = demote_map[role]
        action_row.append(InlineKeyboardButton(
            text=dlabel, callback_data=f"alist_demote:{uid}:{new_role}:{idx}"
        ))
    if action_row:
        rows.append(action_row)

    if is_dynamic:
        rows.append([InlineKeyboardButton(text="➖ Снять роль", callback_data=f"alist_revoke:{uid}:{idx}")])

    rows.append([InlineKeyboardButton(text="📋 К списку", callback_data="alist_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _admin_card_text(uid: int, role: str, icon: str, is_dynamic: bool) -> str:
    user = get_user(uid)
    if user:
        name      = user.get("name", "Без имени")
        username  = user.get("telegram_username", "")
        game_id   = user.get("game_id", "—")
    else:
        name, username, game_id = "Неизвестно", "", "—"

    label       = ROLE_LABELS.get(role, role)
    description = _ROLE_DESCRIPTIONS.get(role, "—")
    perms       = _ROLE_PERMS_READABLE.get(role, "—")
    nick_line   = f"\n🔗 Юз: @{username}" if username else "\n🔗 Юз: —"
    dyn_mark    = "  <i>(динамический)</i>" if is_dynamic else ""

    return (
        f"{icon} <b>{label}</b>{dyn_mark}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📋 <i>{description}</i>\n\n"
        f"👤 Ник: <b>{name}</b>{nick_line}\n"
        f"🎮 ID: <code>{game_id}</code>\n"
        f"📱 TG ID: <code>{uid}</code>\n\n"
        f"⚡ <b>Полномочия:</b>\n{perms}"
    )


@router.message(F.text == "👥 Админы")
async def handle_admins_list_button(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "manage_roles"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    admins = _get_all_admins_ordered()
    if not admins:
        await message.answer("ℹ️ Список администраторов пуст.", parse_mode="HTML")
        return
    await message.answer(
        f"👥 <b>Администраторы</b>  [{len(admins)}]\n\nВыбери сотрудника:",
        parse_mode="HTML",
        reply_markup=_admins_list_kb(admins)
    )


@router.callback_query(F.data == "alist_back")
async def alist_back_cb(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "manage_roles"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    admins = _get_all_admins_ordered()
    await callback.message.edit_text(
        f"👥 <b>Администраторы</b>  [{len(admins)}]\n\nВыбери сотрудника:",
        parse_mode="HTML",
        reply_markup=_admins_list_kb(admins)
    )
    await callback.answer()


async def _show_admin_card(target, idx: int):
    admins = _get_all_admins_ordered()
    if not admins:
        return
    idx = idx % len(admins)
    uid, role, icon, is_dynamic = admins[idx]
    text = _admin_card_text(uid, role, icon, is_dynamic)
    kb   = _admin_action_kb(idx, uid, role, is_dynamic, len(admins))
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "alist_noop")
async def alist_noop_cb(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("alist_nav:"))
async def alist_nav_cb(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "manage_roles"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    idx = int(callback.data.split(":")[1])
    await _show_admin_card(callback, idx)


@router.callback_query(F.data.startswith("alist_promote:"))
async def alist_promote_cb(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "manage_roles"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    parts    = callback.data.split(":")
    uid      = int(parts[1])
    new_role = parts[2]
    idx      = int(parts[3]) if len(parts) > 3 else 0
    user     = get_user(uid)
    name     = user.get("name", "Без имени") if user else str(uid)
    if grant_role(uid, new_role):
        log_action(callback.from_user.id, callback.from_user.full_name, "promote_role", uid, f"{name} → {new_role}")
        await callback.answer("✅ Роль повышена!", show_alert=True)
        try:
            await bot.send_message(uid, f"⬆️ Ваша роль повышена до {ROLE_LABELS.get(new_role, new_role)}.", parse_mode="HTML")
        except Exception:
            pass
        await _show_admin_card(callback, idx)
    else:
        await callback.answer("❌ Не удалось повысить роль.", show_alert=True)


@router.callback_query(F.data.startswith("alist_demote:"))
async def alist_demote_cb(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "manage_roles"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    parts    = callback.data.split(":")
    uid      = int(parts[1])
    new_role = parts[2]
    idx      = int(parts[3]) if len(parts) > 3 else 0
    user     = get_user(uid)
    name     = user.get("name", "Без имени") if user else str(uid)
    if grant_role(uid, new_role):
        log_action(callback.from_user.id, callback.from_user.full_name, "demote_role", uid, f"{name} → {new_role}")
        await callback.answer("⬇️ Роль понижена!", show_alert=True)
        try:
            await bot.send_message(uid, f"⬇️ Ваша роль понижена до {ROLE_LABELS.get(new_role, new_role)}.", parse_mode="HTML")
        except Exception:
            pass
        await _show_admin_card(callback, idx)
    else:
        await callback.answer("❌ Не удалось понизить роль.", show_alert=True)


@router.callback_query(F.data.startswith("alist_revoke:"))
async def alist_revoke_cb(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "manage_roles"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    parts = callback.data.split(":")
    uid   = int(parts[1])
    user  = get_user(uid)
    name  = user.get("name", "Без имени") if user else str(uid)
    if revoke_role(uid):
        log_action(callback.from_user.id, callback.from_user.full_name, "revoke_role", uid, name)
        await callback.answer(f"✅ Роль снята с {name}", show_alert=True)
        try:
            await bot.send_message(uid, "ℹ️ Ваша административная роль была снята.")
        except Exception:
            pass
        admins = _get_all_admins_ordered()
        await callback.message.edit_text(
            f"👥 <b>Администраторы</b>  [{len(admins)}]\n\nВыбери сотрудника:",
            parse_mode="HTML",
            reply_markup=_admins_list_kb(admins)
        )
    else:
        await callback.answer("Не удалось снять роль (назначена через env).", show_alert=True)
    await callback.answer()


@router.callback_query(F.data == "alist_assign")
async def alist_assign_cb(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "manage_roles"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.message.answer(
        "➕ <b>Назначить админа</b>\n\nВведите Telegram ID пользователя:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Отмена", callback_data="alist_assign_cancel")
        ]])
    )
    await state.set_state(AssignAdminFromListState.waiting_id)
    await callback.answer()


@router.callback_query(F.data == "alist_assign_cancel")
async def alist_assign_cancel_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    admins = _get_all_admins_ordered()
    await callback.message.edit_text(
        f"👥 <b>Администраторы</b>  [{len(admins)}]\n\nВыбери сотрудника:",
        parse_mode="HTML",
        reply_markup=_admins_list_kb(admins)
    )
    await callback.answer()


@router.message(AssignAdminFromListState.waiting_id)
async def alist_assign_id_input(message: Message, state: FSMContext):
    raw = message.text.strip()
    uid, user = find_user_by_identifier(raw, utils.user_data)
    if not user:
        await message.answer(
            "❌ Пользователь не найден.\n"
            "Введите TG ID, игровой ID или @username:",
        )
        return
    name     = user.get("name", "Без имени")
    username = user.get("telegram_username", "")
    game_id  = user.get("game_id", "—")
    nick_line = f"\n🔗 @{username}" if username else ""
    await state.update_data(assign_uid=uid, assign_name=name)
    caller_role = get_role(message.from_user.id)
    buttons = []
    if caller_role == ROLE_FOUNDER:
        buttons.append([InlineKeyboardButton(text="⭐ Зам ЛД",       callback_data=f"alist_assign_role:{ROLE_ZAM_LD}")])
        buttons.append([InlineKeyboardButton(text="🔧 Тех Админ",    callback_data=f"alist_assign_role:{ROLE_TECH_ADMIN}")])
        buttons.append([InlineKeyboardButton(text="👮 Админ",        callback_data=f"alist_assign_role:{ROLE_ADMIN}")])
        buttons.append([InlineKeyboardButton(text="🎨 Дизайнер",     callback_data=f"alist_assign_role:{ROLE_DESIGNER}")])
        buttons.append([InlineKeyboardButton(text="🛡 Модер",        callback_data=f"alist_assign_role:{ROLE_MODER}")])
        buttons.append([InlineKeyboardButton(text="👁 Фолер",        callback_data=f"alist_assign_role:{ROLE_FOLLOWER}")])
    elif caller_role == ROLE_ZAM_LD:
        buttons.append([InlineKeyboardButton(text="🔧 Тех Админ",    callback_data=f"alist_assign_role:{ROLE_TECH_ADMIN}")])
        buttons.append([InlineKeyboardButton(text="👮 Админ",        callback_data=f"alist_assign_role:{ROLE_ADMIN}")])
        buttons.append([InlineKeyboardButton(text="🎨 Дизайнер",     callback_data=f"alist_assign_role:{ROLE_DESIGNER}")])
        buttons.append([InlineKeyboardButton(text="🛡 Модер",        callback_data=f"alist_assign_role:{ROLE_MODER}")])
        buttons.append([InlineKeyboardButton(text="👁 Фолер",        callback_data=f"alist_assign_role:{ROLE_FOLLOWER}")])
    if not buttons:
        await state.clear()
        await message.answer("⛔ Недостаточно прав для назначения ролей.")
        return
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="new_admin_cancel")])
    await message.answer(
        f"✅ <b>Найден пользователь:</b>\n"
        f"👤 {name}{nick_line}\n"
        f"🎮 ID: <code>{game_id}</code>\n"
        f"📱 TG ID: <code>{uid}</code>\n\n"
        f"Выбери роль для назначения:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await state.set_state(AssignAdminFromListState.waiting_role)


@router.callback_query(F.data.startswith("alist_assign_role:"), AssignAdminFromListState.waiting_role)
async def alist_assign_role_cb(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "manage_roles"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    new_role = callback.data.split(":")[1]
    data = await state.get_data()
    uid  = data["assign_uid"]
    name = data["assign_name"]
    await state.clear()
    granted = grant_role(uid, new_role)
    if granted:
        log_action(callback.from_user.id, callback.from_user.full_name, "grant_role", uid, f"{name} → {new_role}")
        label = ROLE_LABELS.get(new_role, new_role)
        admins = _get_all_admins_ordered()
        await callback.message.edit_text(
            f"✅ <b>{name}</b> назначен как <b>{label}</b>.\n\n"
            f"👥 <b>Администраторы</b>  [{len(admins)}]\n\nВыбери сотрудника:",
            parse_mode="HTML",
            reply_markup=_admins_list_kb(admins)
        )
        try:
            await bot.send_message(uid, f"✅ Вам выдана роль <b>{label}</b> в системе.", parse_mode="HTML")
        except Exception:
            pass
    else:
        await callback.answer("❌ Не удалось назначить роль.", show_alert=True)
    await callback.answer()


@router.message(F.text == "👑 Управление ролями")
async def handle_roles_button(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "manage_roles") and not has_permission(user_id, "give_admin"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    role = get_role(user_id)
    buttons = []
    if has_permission(user_id, "give_admin"):
        buttons.append([InlineKeyboardButton(text="➕ Выдать роль", callback_data="roles_grant")])
        buttons.append([InlineKeyboardButton(text="➖ Снять роль", callback_data="roles_revoke")])
    buttons.append([InlineKeyboardButton(text="📋 Список ролей", callback_data="roles_list")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("👑 <b>Управление ролями</b>", parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "roles_list")
async def roles_list_cb(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "manage_roles") and not has_permission(callback.from_user.id, "give_admin"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    dynamic = get_all_dynamic_roles()
    if not dynamic:
        await callback.answer("Динамических ролей нет.", show_alert=True)
        return
    lines = []
    for uid, role in dynamic.items():
        user = get_user(int(uid))
        name = user.get("name", "Без имени") if user else "?"
        lines.append(f"👤 {name} (<code>{uid}</code>) — {ROLE_LABELS.get(role, role)}")
    await callback.message.answer("📋 <b>Назначенные роли:</b>\n\n" + "\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "roles_grant")
async def roles_grant_cb(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "give_admin") and not has_permission(callback.from_user.id, "manage_roles"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.message.answer("Введите ID или @юзернейм пользователя для выдачи роли:")
    await state.set_state(GrantRoleState.waiting_user)
    await callback.answer()


@router.message(GrantRoleState.waiting_user)
async def grant_role_user(message: Message, state: FSMContext):
    uid, recipient = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден.")
        return
    await state.update_data(recipient_id=uid)
    admin_id = message.from_user.id
    role = get_role(admin_id)

    buttons = []
    if role == ROLE_FOUNDER:
        buttons.append([InlineKeyboardButton(text="⭐ Зам ЛД",       callback_data=f"grant_{ROLE_ZAM_LD}")])
        buttons.append([InlineKeyboardButton(text="🔧 Тех Админ",    callback_data=f"grant_{ROLE_TECH_ADMIN}")])
        buttons.append([InlineKeyboardButton(text="👮 Админ",        callback_data=f"grant_{ROLE_ADMIN}")])
        buttons.append([InlineKeyboardButton(text="🎨 Дизайнер",     callback_data=f"grant_{ROLE_DESIGNER}")])
        buttons.append([InlineKeyboardButton(text="🛡 Модер",        callback_data=f"grant_{ROLE_MODER}")])
        buttons.append([InlineKeyboardButton(text="👁 Фолер",        callback_data=f"grant_{ROLE_FOLLOWER}")])
    elif role == ROLE_ZAM_LD:
        buttons.append([InlineKeyboardButton(text="🔧 Тех Админ",    callback_data=f"grant_{ROLE_TECH_ADMIN}")])
        buttons.append([InlineKeyboardButton(text="👮 Админ",        callback_data=f"grant_{ROLE_ADMIN}")])
        buttons.append([InlineKeyboardButton(text="🎨 Дизайнер",     callback_data=f"grant_{ROLE_DESIGNER}")])
        buttons.append([InlineKeyboardButton(text="🛡 Модер",        callback_data=f"grant_{ROLE_MODER}")])
        buttons.append([InlineKeyboardButton(text="👁 Фолер",        callback_data=f"grant_{ROLE_FOLLOWER}")])

    if not buttons:
        await message.answer("⛔ Недостаточно прав для выдачи ролей.")
        await state.clear()
        return
    await message.answer(
        f"Выберите роль для <b>{recipient.get('name','?')}</b>:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await state.set_state(GrantRoleState.waiting_role)


@router.callback_query(F.data.startswith("grant_"))
async def grant_role_cb(callback: CallbackQuery, state: FSMContext):
    role_to_grant = callback.data.replace("grant_", "")
    data = await state.get_data()
    rid = data.get("recipient_id")
    if not rid:
        await callback.answer("Ошибка.", show_alert=True)
        return
    grant_role(rid, role_to_grant)
    await state.clear()
    recipient = get_user(rid)
    name = recipient.get("name", "?") if recipient else "?"
    log_action(callback.from_user.id, callback.from_user.full_name, f"grant_{role_to_grant}", rid, name)
    await callback.message.answer(
        f"✅ Роль <b>{ROLE_LABELS.get(role_to_grant,'')}</b> выдана пользователю <b>{name}</b>.",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(rid, f"🎖 Вам выдана роль <b>{ROLE_LABELS.get(role_to_grant,'')}</b>.", parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "roles_revoke")
async def roles_revoke_cb(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "give_admin") and not has_permission(callback.from_user.id, "manage_roles"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.message.answer("Введите ID или @юзернейм пользователя для снятия роли:")
    await state.set_state(RevokeRoleState.waiting_user)
    await callback.answer()


@router.message(RevokeRoleState.waiting_user)
async def revoke_role_user(message: Message, state: FSMContext):
    uid, recipient = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not recipient:
        await message.answer("❌ Пользователь не найден.")
        await state.clear()
        return
    ok = revoke_role(uid)
    await state.clear()
    name = recipient.get("name", "?")
    if ok:
        log_action(message.from_user.id, message.from_user.full_name, "revoke_role", uid, name)
        kb = _get_admin_kb(message.from_user.id)
        await message.answer(f"✅ Роль снята с пользователя <b>{name}</b>.", parse_mode="HTML", reply_markup=safe_reply_kb(message, kb))
        try:
            await bot.send_message(uid, "🔻 Ваша административная роль была снята.", parse_mode="HTML")
        except Exception:
            pass
    else:
        await message.answer(f"❌ У пользователя <b>{name}</b> нет динамической роли.", parse_mode="HTML")


@router.message(F.text.in_({"🌐 Эко Панель", "эко панель"}))
async def show_eco_panel(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "eco_panel") and not has_permission(user_id, "create_promo"):
        await message.answer("⛔ Нет доступа.")
        return
    from keyboards import eco_panel_kb
    await message.answer(
        "🌐 <b>Эко Панель</b>\n\nУправление промокодами и розыгрышами:",
        parse_mode="HTML",
        reply_markup=eco_panel_kb(),
    )


@router.callback_query(F.data == "eco_create_promo")
async def eco_create_promo_cb(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not has_permission(user_id, "create_promo") and not has_permission(user_id, "eco_panel"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    ok, _ = check_and_use_limit(user_id, "promos", 1)
    if not ok:
        await callback.answer("⛔ Дневной лимит на промокоды исчерпан.", show_alert=True)
        return
    from promo import CreatePromoState
    await callback.message.answer(
        "🎟 <b>Создание промокода</b>\n\nВведите <b>название</b> (без пробелов, макс. 30 символов):\nПример: <code>BLACKLINE</code>",
        parse_mode="HTML",
    )
    await state.set_state(CreatePromoState.waiting_for_name)
    await callback.answer()


@router.callback_query(F.data == "eco_list_promos")
async def eco_list_promos_cb(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "create_promo") and not has_permission(callback.from_user.id, "eco_panel"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    from promo import load_promos, _build_promo_list_text, _build_promo_list_kb
    promos = load_promos()
    if not promos:
        await callback.answer("Промокодов нет.", show_alert=True)
        return
    await callback.message.answer(_build_promo_list_text(promos), parse_mode="HTML", reply_markup=_build_promo_list_kb(promos))
    await callback.answer()


@router.callback_query(F.data == "eco_create_raffle")
async def eco_create_raffle_cb(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "eco_panel") and not has_permission(callback.from_user.id, "create_promo"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    from raffle import CreateRaffleState, raffle_type_kb
    await callback.message.answer("🎰 <b>Создание розыгрыша</b>\n\nВыберите тип награды:", parse_mode="HTML", reply_markup=raffle_type_kb())
    await state.set_state(CreateRaffleState.waiting_for_type)
    await callback.answer()


@router.callback_query(F.data == "eco_list_raffles")
async def eco_list_raffles_cb(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "eco_panel") and not has_permission(callback.from_user.id, "create_promo"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    from raffle import load_raffles
    raffles = load_raffles()
    if not raffles:
        await callback.answer("Розыгрышей нет.", show_alert=True)
        return
    now = time.time()
    text = "📋 <b>Все розыгрыши:</b>\n\n"
    buttons = []
    for rid, r in sorted(raffles.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        unit = "$" if r["type"] == "money" else " DC"
        count = len(r.get("participants", []))
        status = r["status"]
        if status == "active" and now >= r["end_time"]:
            icon = "⏳"
        elif status == "active":
            icon = "✅"
        else:
            icon = "🏁"
        text += f"{icon} <b>#{rid}</b> — {format_amount(r['amount'])}{unit} | 👑{r['winners_count']} | 👥{count}\n"
        buttons.append([InlineKeyboardButton(text=f"🔍 #{rid}", callback_data=f"radm_info_{rid}")])
    await callback.message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.message(F.text == "⚙️ Система")
async def handle_system_button(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "system_control"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перезапустить бота", callback_data="sys_restart")],
        [InlineKeyboardButton(text="📊 Статус системы", callback_data="sys_status")],
    ])
    await message.answer("⚙️ <b>Управление системой</b>", parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "sys_status")
async def sys_status_cb(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "system_control"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    import psutil
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        text = (
            f"📊 <b>Статус системы</b>\n\n"
            f"🖥 CPU: {cpu}%\n"
            f"💾 RAM: {mem.percent}% ({mem.used // 1024 // 1024} MB / {mem.total // 1024 // 1024} MB)\n"
        )
    except Exception:
        text = "📊 <b>Статус системы</b>\n\n⚠️ Не удалось получить данные."
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "sys_restart")
async def sys_restart_cb(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "restart_bot") and not has_permission(callback.from_user.id, "system_control"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    log_action(callback.from_user.id, callback.from_user.full_name, "restart_bot", details="Перезапуск через панель")
    await callback.message.answer("🔄 Бот перезапускается...")
    await callback.answer()
    import os, signal
    os.kill(os.getpid(), signal.SIGTERM)


@router.message(F.text == "🛡 Антиспам")
async def handle_antispam(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "antispam_config"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    await message.answer(
        "🛡 <b>Антиспам / Защита</b>\n\n"
        "✅ Антиспам: активен\n"
        "✅ Антифлуд: активен\n"
        "✅ Анти-abuse: активен\n"
        "✅ Проверка лимитов: активна\n"
        "✅ Авто-уведомление Founder: активно",
        parse_mode="HTML"
    )


@router.message(F.text == "💾 База данных")
async def handle_db_button(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "view_db"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    user_count = len(utils.user_data) if utils.user_data else 0
    await message.answer(
        f"💾 <b>База данных</b>\n\n"
        f"👥 Пользователей: <b>{user_count}</b>\n"
        f"📁 Файл: users.json\n"
        f"🔒 Доступ: только чтение (Tech Admin)\n\n"
        f"⚠️ Удаление базы доступно только Founder.",
        parse_mode="HTML"
    )


@router.message(F.text == "🔒 Защита")
async def handle_protection_button(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "system_control") and not has_permission(user_id, "antispam_config"):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    await message.answer(
        "🔒 <b>Система защиты</b>\n\n"
        "📜 <b>Логируется:</b>\n"
        "• Выдача валюты\n"
        "• Баны и муты\n"
        "• Изменение настроек\n"
        "• Создание промокодов\n"
        "• Смена ролей\n\n"
        "⚠️ <b>Авто-контроль:</b>\n"
        "• Проверка лимитов в реальном времени\n"
        "• Авто-уведомление Founder при подозрениях\n"
        "• Блокировка выдач сверх лимита",
        parse_mode="HTML"
    )


@router.message(F.text == "🔑 API & Конфиги")
async def handle_api_button(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "api_keys"):
        from keyboards import menu_kb
        await message.answer("⛔ Этот раздел доступен только Founder.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    await message.answer(
        "🔑 <b>API & Конфигурация</b>\n\n"
        "Переменные окружения управляются через Replit Secrets.\n\n"
        "📋 <b>Доступные переменные:</b>\n"
        "• <code>BOT_TOKEN</code> — токен бота\n"
        "• <code>BOT_FOUNDERS</code> — ID Founder (через запятую)\n"
        "• <code>BOT_ZAM_LD</code> — ID Зам ЛД\n"
        "• <code>BOT_TECH_ADMINS</code> — ID Tech Admin\n"
        "• <code>BOT_ADMINS</code> — ID Admin\n"
        "• <code>BOT_OWNERS</code> — совместимость (старые owners)\n",
        parse_mode="HTML"
    )


@router.message(F.text == "❓ Руководство")
async def handle_guide_button(message: Message):
    user_id = message.from_user.id
    if not is_admin_any(user_id):
        from keyboards import menu_kb
        await message.answer("⛔ Нет прав.", reply_markup=safe_reply_kb(message, menu_kb))
        return
    role = get_role(user_id)
    from texts import get_admin_help_text
    await message.answer(get_admin_help_text(role), parse_mode="HTML")


@router.message(
    F.text.lower().startswith("выдать") | F.text.lower().startswith("выдать"),
    StateFilter(default_state)
)
async def give_money_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not has_permission(user_id, "give_currency"):
        return

    rem = get_remaining_limit(user_id, "currency")
    rem_text = f"<b>{format_amount(rem)}$</b>" if rem is not None else "<b>∞</b>"
    text_arg = message.text.strip()

    # ── Ответ на сообщение игрока ──────────────────────────────────────
    if message.reply_to_message and message.reply_to_message.from_user:
        rid = message.reply_to_message.from_user.id
        recipient = get_user(rid)
        if not recipient:
            await message.answer("❌ Пользователь не зарегистрирован.")
            return
        # Если указана сумма — выдаём деньги сразу: "выдать 5000"
        parts = text_arg.split(maxsplit=1)
        if len(parts) == 2:
            amount = parse_k(parts[1].strip())
            if amount and amount > 0:
                ok, remaining = check_and_use_limit(user_id, "currency", amount)
                if not ok:
                    rt = format_amount(remaining) if remaining is not None else "∞"
                    await message.answer(f"⛔ Превышен лимит! Доступно: <b>{rt}$</b>", parse_mode="HTML")
                    return
                update_balance(rid, get_balance(rid) + amount)
                save_user_data()
                name = recipient.get("name", "?")
                log_action(user_id, message.from_user.full_name, "give_currency", rid, f"+{format_amount(amount)}$")
                kb = _get_admin_kb(user_id)
                await message.answer(
                    f"✅ Выдано <b>{format_amount(amount)}$</b> → <b>{name}</b>",
                    parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
                )
                try:
                    await bot.send_message(rid, f"💵 Вам выдали <b>{format_amount(amount)}$</b> от администратора.", parse_mode="HTML")
                except Exception:
                    pass
                return
        # Иначе — показываем меню типов
        await state.update_data(recipient_id=rid)
        name = recipient.get("name", "?")
        await message.answer(
            f"💵 <b>Выдача → {name}</b>\n\n💰 Лимит: {rem_text}\n\nВыбери тип:",
            parse_mode="HTML", reply_markup=_give_menu_kb()
        )
        return

    # ── Без ответа: "выдать @id сумма" ────────────────────────────────
    parts = text_arg.split(maxsplit=2)
    if len(parts) == 3:
        rid, recipient = find_user_by_identifier(parts[1].strip(), utils.user_data)
        if not recipient:
            await message.answer("❌ Пользователь не найден.")
            return
        amount = parse_k(parts[2].strip())
        if amount and amount > 0:
            ok, remaining = check_and_use_limit(user_id, "currency", amount)
            if not ok:
                rt = format_amount(remaining) if remaining is not None else "∞"
                await message.answer(f"⛔ Превышен лимит! Доступно: <b>{rt}$</b>", parse_mode="HTML")
                return
            update_balance(rid, get_balance(rid) + amount)
            save_user_data()
            name = recipient.get("name", "?")
            log_action(user_id, message.from_user.full_name, "give_currency", rid, f"+{format_amount(amount)}$")
            kb = _get_admin_kb(user_id)
            await message.answer(
                f"✅ Выдано <b>{format_amount(amount)}$</b> → <b>{name}</b>",
                parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
            )
            try:
                await bot.send_message(rid, f"💵 Вам выдали <b>{format_amount(amount)}$</b> от администратора.", parse_mode="HTML")
            except Exception:
                pass
            return
    elif len(parts) == 2:
        rid, recipient = find_user_by_identifier(parts[1].strip(), utils.user_data)
        if recipient:
            await state.update_data(recipient_id=rid)
            name = recipient.get("name", "?")
            await message.answer(
                f"💵 <b>Выдача → {name}</b>\n\n💰 Лимит: {rem_text}\n\nВыбери тип:",
                parse_mode="HTML", reply_markup=_give_menu_kb()
            )
            return

    # ── Без аргументов — показываем меню ──────────────────────────────
    await message.answer(
        f"💵 <b>Выдача</b>\n\n💰 Лимит: {rem_text}\n\nВведи ID / игровой ID / @username игрока:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await state.set_state(NewAdminGiveState.waiting_user)


@router.callback_query(F.data == "new_admin_cancel")
async def new_admin_cancel_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = _get_admin_kb(callback.from_user.id)
    await callback.message.answer("❌ Отменено.", reply_markup=safe_reply_kb(callback.message, kb))
    await callback.answer()


@router.callback_query(F.data.startswith("reset_user:"))
async def reset_user_inline_cb(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "reset_user"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    rid = int(callback.data.split(":")[1])
    recipient = get_user(rid)
    name = recipient.get("name", "?") if recipient else "?"
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, обнулить", callback_data=f"reset_confirm:{rid}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="new_admin_cancel"),
    ]])
    await callback.message.answer(f"Обнулить <b>{name}</b>?", parse_mode="HTML", reply_markup=confirm_kb)
    await callback.answer()


@router.callback_query(F.data.startswith("reset_confirm:"))
async def reset_confirm_inline_cb(callback: CallbackQuery):
    if not has_permission(callback.from_user.id, "reset_user"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    rid = int(callback.data.split(":")[1])
    recipient = get_user(rid)
    name = recipient.get("name", "?") if recipient else "?"
    reset_user_data(rid)
    log_action(callback.from_user.id, callback.from_user.full_name, "reset_user", rid, name)
    kb = _get_admin_kb(callback.from_user.id)
    await callback.message.answer(f"✅ Аккаунт <b>{name}</b> обнулён.", parse_mode="HTML", reply_markup=safe_reply_kb(callback.message, kb))
    await callback.answer()


@router.callback_query(F.data.startswith("give_money:"))
async def give_money_inline_cb(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "give_currency"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    rid = int(callback.data.split(":")[1])
    u   = get_user(rid)
    await state.update_data(recipient_id=rid)
    rem = get_remaining_limit(callback.from_user.id, "currency")
    rem_text = f"{format_amount(rem)}$" if rem is not None else "∞"
    await callback.message.answer(
        f"💵 <b>Выдача → {u.get('name','?') if u else '?'}</b>\n"
        f"💰 Лимит: {rem_text}\n\nВведите сумму:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await state.set_state(NewAdminGiveState.waiting_amount)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_give_dc:"))
async def adm_give_dc_cb(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "give_currency"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    rid = int(callback.data.split(":")[1])
    u   = get_user(rid)
    await state.update_data(recipient_id=rid)
    await callback.message.answer(
        f"💎 <b>Выдача DC → {u.get('name','?') if u else '?'}</b>\n"
        f"Текущий баланс: {u.get('donate_coins',0) if u else 0} DC\n\nВведите количество DC:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await state.set_state(AdminGiveDcState.waiting_amount)
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════
#  РОУТЕР ВЫДАЧИ — выбор типа
# ═══════════════════════════════════════════════════════════════════

_CANCEL_KB = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="❌ Отмена", callback_data="new_admin_cancel")
]])


@router.callback_query(F.data.startswith("give_type:"))
async def cb_give_type(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "give_currency"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    gtype = callback.data.split(":")[1]
    data  = await state.get_data()
    pre   = data.get("recipient_id")   # уже выбран пользователь?

    if gtype == "money":
        if pre:
            u = get_user(pre)
            await callback.message.answer(
                f"💵 <b>Деньги → {u.get('name','?')}</b>\n\nВведите сумму:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(NewAdminGiveState.waiting_amount)
        else:
            await callback.message.answer(
                "💵 <b>Выдача денег (кошелёк)</b>\n\nВведите ID / game_id / @username:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(NewAdminGiveState.waiting_user)

    elif gtype == "bank":
        if pre:
            u = get_user(pre)
            await callback.message.answer(
                f"🏦 <b>Банк → {u.get('name','?')}</b>\n\nВведите сумму:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminGiveBankState.waiting_amount)
        else:
            await callback.message.answer(
                "🏦 <b>Выдача в банк</b>\n\nВведите ID / game_id / @username:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminGiveBankState.waiting_user)

    elif gtype == "btc":
        if pre:
            u = get_user(pre)
            from farm import get_farm, flush_farm, _fmt_btc
            farm  = get_farm(pre)
            btc_b = farm.get("btc_balance", 0.0)
            await callback.message.answer(
                f"₿ <b>BTC → {u.get('name','?')}</b>  •  Текущий: {_fmt_btc(btc_b)}\n\nВведите количество BTC:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminGiveBtcState.waiting_amount)
        else:
            await callback.message.answer(
                "₿ <b>Выдача BTC</b>\n\nВведите ID / game_id / @username:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminGiveBtcState.waiting_user)

    elif gtype == "dc":
        if pre:
            u = get_user(pre)
            await callback.message.answer(
                f"💎 <b>DC → {u.get('name','?')}</b>  •  Текущий: {u.get('donate_coins',0)} DC\n\nВведите количество DC:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminGiveDcState.waiting_amount)
        else:
            await callback.message.answer(
                "💎 <b>Выдача DC</b>\n\nВведите ID / game_id / @username:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminGiveDcState.waiting_user)

    elif gtype == "donate_item":
        from donate import DONATE_BUSINESSES, DONATE_HOUSES, DONATE_CARS
        rows = []
        rows.append([InlineKeyboardButton(text="⭐ VIP статус", callback_data="give_ditem:vip")])
        for key, biz in DONATE_BUSINESSES.items():
            rows.append([InlineKeyboardButton(
                text=f"💼 {biz['name']}", callback_data=f"give_ditem:biz:{key}"
            )])
        for key, house in DONATE_HOUSES.items():
            rows.append([InlineKeyboardButton(
                text=f"🏛 {house['name']}", callback_data=f"give_ditem:house:{key}"
            )])
        for key, car in DONATE_CARS.items():
            rows.append([InlineKeyboardButton(
                text=f"🏎 {car['name']}", callback_data=f"give_ditem:car:{key}"
            )])
        rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="new_admin_cancel")])
        await callback.message.answer(
            "🎁 <b>Выдача донат-предмета</b>\n\nВыбери предмет:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )

    elif gtype == "level":
        if pre:
            u = get_user(pre)
            await callback.message.answer(
                f"⭐ <b>Уровень и XP → {u.get('name','?')}</b>\n\nВведите уровень и XP через пробел:\n<code>10 250</code>",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminGiveLevelState.waiting_value)
        else:
            await callback.message.answer(
                "⭐ <b>Выдача уровня и XP</b>\n\nВведите ID / game_id / @username:",
                parse_mode="HTML", reply_markup=_CANCEL_KB
            )
            await state.set_state(AdminGiveLevelState.waiting_user)

    await callback.answer()


# ─── Банк ─────────────────────────────────────────────────────────

@router.message(AdminGiveBankState.waiting_user)
async def give_bank_user(message: Message, state: FSMContext):
    uid, u = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not u:
        await message.answer("❌ Не найден. Попробуй ещё:")
        return
    await state.update_data(recipient_id=uid)
    await message.answer(
        f"✅ <b>{u.get('name','?')}</b>  •  Текущий банк: {format_amount(u.get('user_bank',0))}$\n\nВведите сумму:",
        parse_mode="HTML"
    )
    await state.set_state(AdminGiveBankState.waiting_amount)


@router.message(AdminGiveBankState.waiting_amount)
async def give_bank_amount(message: Message, state: FSMContext):
    amount = parse_k(message.text.strip())
    if amount is None or amount <= 0:
        await message.answer("❌ Некорректная сумма.")
        return
    user_id = message.from_user.id
    ok, remaining = check_and_use_limit(user_id, "currency", amount)
    if not ok:
        await message.answer(f"⛔ Превышен лимит! Доступно: <b>{format_amount(remaining) if remaining else '∞'}$</b>", parse_mode="HTML")
        await state.clear()
        return
    data = await state.get_data()
    rid = data["recipient_id"]
    u   = get_user(rid)
    u["user_bank"] = u.get("user_bank", 0) + amount
    save_user_data()
    name = u.get("name", "?")
    log_action(user_id, message.from_user.full_name, "give_bank", rid, f"+{format_amount(amount)}$")
    await state.clear()
    kb = _get_admin_kb(user_id)
    await message.answer(
        f"✅ В банк <b>{name}</b> зачислено <b>{format_amount(amount)}$</b>",
        parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
    )
    try:
        await bot.send_message(rid, f"🏦 Вам зачислили <b>{format_amount(amount)}$</b> прямо в банк от администратора.", parse_mode="HTML")
    except Exception:
        pass


# ─── BTC ──────────────────────────────────────────────────────────

@router.message(AdminGiveBtcState.waiting_user)
async def give_btc_user(message: Message, state: FSMContext):
    uid, u = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not u:
        await message.answer("❌ Не найден. Попробуй ещё:")
        return
    await state.update_data(recipient_id=uid)
    from farm import get_farm, flush_farm, _fmt_btc
    farm   = get_farm(uid)
    btc_b  = farm.get("btc_balance", 0.0)
    await message.answer(
        f"✅ <b>{u.get('name','?')}</b>  •  BTC: {_fmt_btc(btc_b)}\n\nВведите количество BTC (например <code>0.5</code>):",
        parse_mode="HTML"
    )
    await state.set_state(AdminGiveBtcState.waiting_amount)


@router.message(AdminGiveBtcState.waiting_amount)
async def give_btc_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(",", "."))
        assert amount > 0
    except Exception:
        await message.answer("❌ Введи число BTC, например <code>0.5</code>", parse_mode="HTML")
        return
    data   = await state.get_data()
    rid    = data["recipient_id"]
    user_id = message.from_user.id
    from farm import get_farm, flush_farm, _fmt_btc
    farm = get_farm(rid)
    flush_farm(farm)
    if farm.get("farm_level", 0) == 0:
        farm["farm_level"]   = 1
        farm["btc_balance"]  = 0.0
        farm["mining_start"] = 0
    farm["btc_balance"] = round(farm.get("btc_balance", 0.0) + amount, 8)
    save_user_data()
    name = get_user(rid).get("name", "?")
    log_action(user_id, message.from_user.full_name, "give_btc", rid, f"+{_fmt_btc(amount)} BTC")
    await state.clear()
    kb = _get_admin_kb(user_id)
    await message.answer(
        f"✅ Выдано <b>{_fmt_btc(amount)} BTC</b> → <b>{name}</b>",
        parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
    )
    try:
        await bot.send_message(rid, f"₿ Вам выдали <b>{_fmt_btc(amount)} BTC</b> от администратора.", parse_mode="HTML")
    except Exception:
        pass


# ─── DC ───────────────────────────────────────────────────────────

@router.message(AdminGiveDcState.waiting_user)
async def give_dc_user(message: Message, state: FSMContext):
    uid, u = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not u:
        await message.answer("❌ Не найден. Попробуй ещё:")
        return
    await state.update_data(recipient_id=uid)
    await message.answer(
        f"✅ <b>{u.get('name','?')}</b>  •  DC: {u.get('donate_coins',0)}\n\nВведите количество DC:",
        parse_mode="HTML"
    )
    await state.set_state(AdminGiveDcState.waiting_amount)


@router.message(AdminGiveDcState.waiting_amount)
async def give_dc_amount(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("❌ Введи целое число DC.")
        return
    amount  = int(text)
    data    = await state.get_data()
    rid     = data["recipient_id"]
    user_id = message.from_user.id
    u = get_user(rid)
    u["donate_coins"] = u.get("donate_coins", 0) + amount
    save_user_data()
    name = u.get("name", "?")
    log_action(user_id, message.from_user.full_name, "give_dc", rid, f"+{amount} DC")
    await state.clear()
    kb = _get_admin_kb(user_id)
    await message.answer(
        f"✅ Выдано <b>{amount} DC</b> → <b>{name}</b>",
        parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
    )
    try:
        await bot.send_message(rid, f"💎 Вам выдали <b>{amount} DC</b> от администратора.", parse_mode="HTML")
    except Exception:
        pass


@router.message(AdminGiveLevelState.waiting_user)
async def give_level_user(message: Message, state: FSMContext):
    uid, u = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not u:
        await message.answer("❌ Не найден. Попробуй ещё:")
        return
    await state.update_data(recipient_id=uid)
    await message.answer(
        f"⭐ <b>{u.get('name','?')}</b>\n\nВведите уровень и XP через пробел:\n<code>10 250</code>",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await state.set_state(AdminGiveLevelState.waiting_value)


@router.message(AdminGiveLevelState.waiting_value)
async def give_level_value(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.answer("❌ Введите два числа: уровень и XP.")
        return
    try:
        level = int(parts[0])
        xp = int(parts[1])
    except ValueError:
        await message.answer("❌ Нужны целые числа.")
        return
    if level < 0 or xp < 0:
        await message.answer("❌ Значения не могут быть отрицательными.")
        return
    data = await state.get_data()
    recipient_id = data["recipient_id"]
    recipient = get_user(recipient_id)
    recipient["level"] = level
    recipient["experience"] = xp
    save_user_data()
    await state.clear()
    await message.answer(
        f"✅ Установлено <b>Лвл {level}</b> / <b>{xp} XP</b> для {clickable_name(recipient_id, recipient.get('name','?'), recipient.get('clickable_name', True))}",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(recipient_id, f"⭐ Вам установили <b>Лвл {level}</b> и <b>{xp} XP</b>.", parse_mode="HTML")
    except Exception:
        pass


# ─── Донат-предмет ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("give_ditem:"))
async def cb_give_ditem(callback: CallbackQuery, state: FSMContext):
    if not has_permission(callback.from_user.id, "give_currency"):
        await callback.answer("Нет прав.", show_alert=True)
        return
    parts = callback.data.split(":", 2)   # give_ditem:TYPE[:KEY]
    if len(parts) == 2:
        item_id = parts[1]          # "vip"
    else:
        item_id = f"{parts[1]}:{parts[2]}"  # "biz:casino" / "house:whitehouse" / "car:hypercar"

    await state.update_data(give_item_id=item_id)
    await callback.message.answer(
        f"🎁 Предмет выбран.\n\nВведите ID / game_id / @username игрока:",
        reply_markup=_CANCEL_KB
    )
    await state.set_state(AdminGiveDonateItemState.waiting_user)
    await callback.answer()


@router.message(AdminGiveDonateItemState.waiting_user)
async def give_ditem_user(message: Message, state: FSMContext):
    uid, u = find_user_by_identifier(message.text.strip(), utils.user_data)
    if not u:
        await message.answer("❌ Не найден. Попробуй ещё:")
        return
    data     = await state.get_data()
    item_id  = data["give_item_id"]
    user_id  = message.from_user.id
    name     = u.get("name", "?")

    from donate import get_donate_user_data, DONATE_BUSINESSES, DONATE_HOUSES, DONATE_CARS

    don = get_donate_user_data(u)

    if item_id == "vip":
        don["vip"] = True
        item_label = "⭐ VIP"
    elif item_id.startswith("biz:"):
        key = item_id.split(":", 1)[1]
        don["business"]         = key
        don["biz_last_collect"] = __import__("time").time()
        item_label = DONATE_BUSINESSES.get(key, {}).get("name", key)
    elif item_id.startswith("house:"):
        key = item_id.split(":", 1)[1]
        don["house"] = key
        item_label = DONATE_HOUSES.get(key, {}).get("name", key)
    elif item_id.startswith("car:"):
        key = item_id.split(":", 1)[1]
        don["car"] = key
        item_label = DONATE_CARS.get(key, {}).get("name", key)
    else:
        await message.answer("❌ Неизвестный предмет.")
        await state.clear()
        return

    save_user_data()
    log_action(user_id, message.from_user.full_name, "give_donate_item", uid, item_label)
    await state.clear()
    kb = _get_admin_kb(user_id)
    await message.answer(
        f"✅ Выдан <b>{item_label}</b> → <b>{name}</b>",
        parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
    )
    try:
        await bot.send_message(uid, f"🎁 Вам выдали <b>{item_label}</b> от администратора.", parse_mode="HTML")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
#  РОУТЕР ОБНУЛЕНИЯ — выбор типа + вайп сервера
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("reset_type:"))
async def cb_reset_type(callback: CallbackQuery, state: FSMContext):
    rtype   = callback.data.split(":")[1]
    user_id = callback.from_user.id

    if rtype == "player":
        if not has_permission(user_id, "reset_user"):
            await callback.answer("Нет прав.", show_alert=True)
            return
        await state.update_data(reset_kind="player")
        await callback.message.answer(
            "👤 <b>Обнуление игрока</b>\n\nВведите ID / game_id / @username:",
            parse_mode="HTML", reply_markup=_CANCEL_KB
        )
        await state.set_state(NewAdminResetState.waiting_user)
    elif rtype == "clan":
        if not has_permission(user_id, "reset_user"):
            await callback.answer("Нет прав.", show_alert=True)
            return
        await state.update_data(reset_kind="clan")
        await callback.message.answer(
            "🏰 <b>Обнуление клана</b>\n\nВведите ID, номер клана или название клана:",
            parse_mode="HTML", reply_markup=_CANCEL_KB
        )
        await state.set_state(NewAdminResetState.waiting_user)

    elif rtype == "wipe":
        role = get_role(user_id)
        if role not in (ROLE_FOUNDER, ROLE_ZAM_LD):
            await callback.answer("⛔ Только Founder / Зам ЛД.", show_alert=True)
            return
        await callback.message.answer(
            "☢️ <b>ВАЙП СЕРВЕРА</b>\n\n"
            "⚠️ Это обнулит <b>ВСЕХ</b> игроков сервера!\n\n"
            "Напиши <code>ВАЙП</code> для первого подтверждения:",
            parse_mode="HTML", reply_markup=_CANCEL_KB
        )
        await state.set_state(ServerWipeState.waiting_confirm1)

    await callback.answer()


@router.message(ServerWipeState.waiting_confirm1)
async def wipe_confirm1(message: Message, state: FSMContext):
    if message.text.strip() != "ВАЙП":
        await message.answer("❌ Неверно. Напиши ровно <code>ВАЙП</code> или /отмена для отмены:", parse_mode="HTML")
        return
    await message.answer(
        "☢️ <b>ПОСЛЕДНЕЕ ПРЕДУПРЕЖДЕНИЕ!</b>\n\n"
        f"Будет сброшено <b>{len(utils.user_data)}</b> аккаунтов.\n\n"
        "Напиши <code>ПОДТВЕРЖДАЮ ВАЙП</code> чтобы продолжить:",
        parse_mode="HTML", reply_markup=_CANCEL_KB
    )
    await state.set_state(ServerWipeState.waiting_confirm2)


@router.message(ServerWipeState.waiting_confirm2)
async def wipe_confirm2(message: Message, state: FSMContext):
    if message.text.strip() != "ПОДТВЕРЖДАЮ ВАЙП":
        await message.answer("❌ Неверно. Напиши ровно <code>ПОДТВЕРЖДАЮ ВАЙП</code>:", parse_mode="HTML")
        return

    user_id    = message.from_user.id
    admin_name = message.from_user.full_name
    count      = len(utils.user_data)

    for uid in list(utils.user_data.keys()):
        reset_user_data(int(uid))

    # Обнуляем coin_games.json
    try:
        import os, json
        cgfile = os.path.join(os.path.dirname(__file__), "coin_games.json")
        with open(cgfile, "w", encoding="utf-8") as f:
            json.dump({}, f)
    except Exception:
        pass

    log_action(user_id, admin_name, "server_wipe", 0, f"Сброшено {count} аккаунтов")
    await state.clear()
    kb = _get_admin_kb(user_id)
    await message.answer(
        f"☢️ <b>ВАЙП ЗАВЕРШЁН</b>\n\nСброшено аккаунтов: <b>{count}</b>",
        parse_mode="HTML", reply_markup=safe_reply_kb(message, kb)
    )

    for f_id in founders:
        if f_id != user_id:
            try:
                await bot.send_message(
                    f_id,
                    f"☢️ <b>ВАЙП СЕРВЕРА</b>\n\n"
                    f"Выполнил: <b>{admin_name}</b> (<code>{user_id}</code>)\n"
                    f"Сброшено аккаунтов: <b>{count}</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass


# ─── ВЫДАЧА КЕЙСОВ ─────────────────────────────────────────────────────────────

@router.message(F.text.lower().startswith("дать кейс"))
async def cmd_give_case_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not has_permission(user_id, "give_currency"):
        await message.answer("⛔ Нет прав.")
        return
    parts = message.text.strip().split()
    if len(parts) >= 4:
        identifier = parts[2]
        from cases import CASES, add_case_to_user
        uid, u = find_user_by_identifier(identifier, utils.user_data)
        if not u:
            await message.answer("❌ Пользователь не найден.")
            return
        case_id = parts[3]
        if case_id not in CASES:
            cases_list = ", ".join(CASES.keys())
            await message.answer(f"❌ Кейс не найден. Доступные: {cases_list}")
            return
        count = int(parts[4]) if len(parts) >= 5 and parts[4].isdigit() else 1
        for _ in range(count):
            add_case_to_user(uid, case_id)
        save_user_data()
        await message.answer(
            f"✅ Выдано <b>{count}×{CASES[case_id]['name']}</b> → <b>{u.get('name','?')}</b>",
            parse_mode="HTML"
        )
        try:
            await bot.send_message(
                int(uid),
                f"🎁 Вам выдали <b>{count}×{CASES[case_id]['name']}</b> от администратора.",
                parse_mode="HTML"
            )
        except Exception:
            pass
        return
    from cases import CASES
    cases_list = "\n".join(f"  <code>{k}</code> — {v['name']}" for k, v in CASES.items())
    await message.answer(
        f"🎁 <b>Выдача кейса</b>\n\n"
        f"Использование: <code>дать кейс [ID/ник] [тип_кейса] [кол-во]</code>\n\n"
        f"Доступные кейсы:\n{cases_list}",
        parse_mode="HTML"
    )


@router.message(F.text.lower().startswith("удалить кейс"))
async def cmd_delete_case(message: Message):
    user_id = message.from_user.id
    if not has_permission(user_id, "give_currency"):
        await message.answer("⛔ Нет прав.")
        return
    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.answer("❌ Использование: <code>удалить кейс [ID/ник] [тип_кейса]</code>", parse_mode="HTML")
        return
    identifier = parts[2]
    uid, u = find_user_by_identifier(identifier, utils.user_data)
    if not u:
        await message.answer("❌ Пользователь не найден.")
        return
    from cases import CASES, remove_case_from_user
    case_id = parts[3] if len(parts) >= 4 else None
    if not case_id or case_id not in CASES:
        await message.answer("❌ Укажите тип кейса. Пример: <code>удалить кейс 123 rare</code>", parse_mode="HTML")
        return
    ok = remove_case_from_user(uid, case_id)
    if ok:
        save_user_data()
        await message.answer(
            f"✅ Кейс <b>{CASES[case_id]['name']}</b> удалён у <b>{u.get('name','?')}</b>",
            parse_mode="HTML"
        )
    else:
        await message.answer(f"❌ У игрока нет этого кейса.")
