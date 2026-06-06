import asyncio
import random
import re
import json
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram import types
from aiogram.fsm.state import default_state
from config import owners, admins, API_TOKEN
from games import (bet_multipliers, bet_aliases)
from games import CrashState, generate_crash_coef
from aiogram.filters import StateFilter
from keyboards import (
    menu_kb,
    games_kb,
    settings_kb,
    ref_kb,
    admin_kb,
    admin_set_kb,
    get_admin_set_kb,
    get_bank_action_kb,
    get_bank_main_kb,
    get_deposit_terms_kb,
    eco_panel_kb,
    razvitie_kb,
    get_razvitie_inline_kb,
    get_razvitie_shop_inline_kb,
    founder_kb,
    zam_ld_kb,
    tech_admin_kb,
    admin_role_kb,
    designer_kb,
    moder_kb,
)


def get_kb_for_user(user_id: int):
    """Возвращает обычную Reply-клавиатуру для всех пользователей. Админка — только inline."""
    return menu_kb


from admin_panel import router as admin_panel_router
from admin_inline import router as admin_inline_router
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router
import time
from texts import (
    roulette_help_text,
    blackjack_help_text,
    mines_help_text,
    transfer_help_text,
    games_help_text,
    admin_panel_help_text,
    bank_help_text,
    deposit_help_text,
    crash_help_text,
    all_commands_text,
    report_help_text,
    coin_help_text,
    bonus_help_text,
    profile_help_text,
    basket_help_text,
    penka_help_text,
    darts_help_text,
    duel_help_text,
    clan_chat_help_text,
)
from roulette import router as roulette_router
from blackjack import router as blackjack_router
from mines import router as mines_router
from clans import router as clans_router, get_user_clan, ROLE_NAMES, auto_mine_ore, update_market_prices, check_season_end
from clan_center import router as clan_center_router, auto_mine_all_complexes
from jobs import router as jobs_router
from promo import router as promo_router, CreatePromoState, promo_type_kb, load_promos, _build_promo_list_text, _build_promo_list_kb
from raffle import router as raffle_router, process_raffles, CreateRaffleState, raffle_type_kb, load_raffles, build_raffle_text, raffle_join_kb
from farm import router as farm_router, notify_mining_done
from market import router as market_router
from cases import router as cases_router
from donate import router as donate_router, handle_pre_checkout, handle_successful_payment, auto_collect_all_businesses, vip_clan_hourly_rating
from racing_shop import router as racing_router
from top import router as top_router
from player_info import router as player_info_router
from house_shop import router as house_shop_router
from eco_menu import router as eco_router
from business_shop import router as business_shop_router
from auto_shop import router as auto_shop_router, SHOP_CARS, get_owned_car, check_car_rentals
from house_shop import check_house_rentals
from chat_system import router as chat_system_router
from group_commands import router as group_commands_router
from wealth import router as wealth_router
from mini_games import router as mini_games_router
from duel import router as duel_router
from config import admins
from aiogram.filters.command import CommandObject
from aiogram.types import CallbackQuery
import utils
from config import API_TOKEN, owners, bot
from utils import (
    load_user_data,
    save_user_data,
    get_user,
    get_balance,
    update_balance,
    set_name,
    get_name,
    get_game_id,
    parse_k,
    round_amount,
    fix_user_data,
    fix_duplicate_ids,
    grant_founder_stats,
    round_all_balances,
    round_balance,
    update_telegram_username,
    is_emoji_present,
    find_user_by_identifier,
    check_and_pay_deposit,
    process_deposits,
    process_all_deposits,
    format_amount,
    safe_reply_kb,
    reset_user_data,
    clickable_name,
)


help_synonyms = {
    "рулетка": ["рулетка", "рулетки", "рулетку", "рулетке", "рулет", "рулету"],
    "блэкджек": ["блэкджек", "блекджек", "блек", "blackjack", "21", "блэк"],
    "мины": ["мины", "мина", "mines", "минах"],
    "передать": ["передать", "перевод", "перевести", "передачи", "переводы"],
    "работа": ["работа", "работу", "работы", "работе", "работать"],
    "игры": ["игры", "игра", "игру", "игре", "игр", "игрульки"],
    "банк": ["банк", "банка", "банку", "банке", "банки"],
    "вклад": ["вклад", "вклады", "вкладу", "вклада", "вкладах"],
    "краш": ["краш", "краша", "крашу", "краше", "крашик", "crash"],
    "репорт": ["репорт", "репорта", "репорту", "репорте", "поддержка", "support"],
    "монетка": ["монетка", "монетку", "монетки", "монетке", "монеточка", "монеточ", "монет"],
    "бонус": ["бонус", "бонуса", "бонусу", "бонусы"],
    "профиль": ["профиль", "профиля", "профилю", "профиле", "profile", "я", "яша"],
    "ник": ["ник", "имя", "сменить ник", "сменить имя", "изменить имя"],
    "кликабельность": ["кликабельность", "кликабельный", "кликабельность ника"],
    "баскет": ["баскет", "баскетбол", "basket", "баскете", "баскету"],
    "пенка": ["пенка", "пенальти", "penalty", "пенке", "пенку"],
    "дартс": ["дартс", "дартс", "darts", "дарт", "дартсе"],
    "дуэль": ["дуэль", "дуэли", "дуэлью", "дуэле", "дуэлей", "duel"],
    "клан_чат": ["клан чат", "привязать чат", "чат клана", "клан привязать", "клан_чат", "чатклан", "привязать"],
    "help": ["help", "команды", "помощь", "справка", "all commands"],
}



router = Router()
dp = Dispatcher(storage=MemoryStorage())
bets = {}
user_names = {}


from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Any, Callable, Awaitable

class LastSeenMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        from utils import update_last_seen
        try:
            user = data.get("event_from_user")
            if user and user.id:
                update_last_seen(user.id)
        except Exception:
            pass
        return await handler(event, data)

dp.message.middleware(LastSeenMiddleware())
dp.callback_query.middleware(LastSeenMiddleware())

from button_guard import setup_button_guard
setup_button_guard(dp, bot)

game_ids = {}
user_data_file = os.path.join(os.path.dirname(__file__), "users.json")
last_bonus_time = {}
dp.include_router(admin_inline_router)
dp.include_router(admin_panel_router)
dp.include_router(roulette_router)
dp.include_router(blackjack_router)
dp.include_router(mines_router)
dp.include_router(clans_router)
dp.include_router(clan_center_router)
dp.include_router(jobs_router)
dp.include_router(promo_router)
dp.include_router(raffle_router)
dp.include_router(farm_router)
dp.include_router(market_router)
dp.include_router(cases_router)
dp.include_router(donate_router)
dp.include_router(racing_router)
dp.include_router(top_router)
dp.include_router(player_info_router)
dp.include_router(house_shop_router)
dp.include_router(eco_router)
dp.include_router(business_shop_router)
dp.include_router(auto_shop_router)
dp.include_router(chat_system_router)
dp.include_router(group_commands_router)
dp.include_router(wealth_router)
dp.include_router(mini_games_router)
dp.include_router(duel_router)
BANK_DEPOSIT_LIMIT = 1_000_000
BOT_NAME = "Blackline_bot"
REPORTS_FILE = os.path.join(os.path.dirname(__file__), "reports.json")
REPORTS_STATE = {}


class SellState(StatesGroup):
    waiting_for_confirmation = State()

class BankDepositState(StatesGroup):
    waiting_for_deposit_amount = State()


class Reg(StatesGroup):
    waiting_for_name = State()


class SettingsState(StatesGroup):
    waiting_for_new_name = State()


class BankSaveState(StatesGroup):
    waiting_for_bank_save_add = State()
    waiting_for_bank_save_withdraw = State()
    

@dp.message(CommandStart())
async def send_welcome(message: Message, command: CommandObject, state: FSMContext):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    tg_first_name = message.from_user.first_name
    username = message.from_user.username
    if username:
        update_telegram_username(user_id, username)
    args = command.args
    user = get_user(user_id)
    # Если у пользователя ещё нет имени — ставим Telegram first_name
    if not user.get("name"):
        set_name(user_id, tg_first_name)
        user["name"] = tg_first_name
        save_user_data()
    if args and args.startswith("ref"):
        referrer_id = args[3:]
        if referrer_id.isdigit() and int(referrer_id) != user_id:
            referrer_id = int(referrer_id)
            referrer = get_user(referrer_id)
            if referrer:
                user["referrer"] = referrer_id
                referrer["referrals"].append(user_id)
                save_user_data()
                from donate import is_vip
                referrer_bonus = 15000 if is_vip(referrer_id) else 10000
                update_balance(referrer_id, get_balance(referrer_id) + referrer_bonus)
                invited_bonus = 5000
                update_balance(user_id, get_balance(user_id) + invited_bonus)
                await message.answer(
                    f"🎉 Вы были приглашены пользователем {clickable_name(referrer_id, referrer['name'])}!\n"
                    f"Он получил <b>{referrer_bonus}$</b> за приглашение, а вы получили <b>{invited_bonus}$</b>!",
                    reply_markup=safe_reply_kb(message, menu_kb),
                    parse_mode="HTML"
                )
    start_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать игру", callback_data="show_menu")]
        ]
    )
    await message.answer(
        f"╔══════════════════════════╗\n"
        f"      🎮 <b>{BOT_NAME}</b>\n"
        f"╚══════════════════════════╝\n\n"
        f"👋 Привет, {clickable_name(user_id, user.get('name', tg_first_name))}!\n\n"
        f"🏆 <b>Лучший экономический бот!</b>\n\n"
        f"⚡ Что тебя ждёт:\n"
        f"  💰 Зарабатывай деньги и богатей\n"
        f"  🏰 Вступай в кланы и воюй\n"
        f"  🎰 Играй в казино и выигрывай\n"
        f"  🚗 Покупай машины, дома, яхты\n"
        f"  ⛏ Добывай ресурсы и торгуй\n"
        f"  🎖 Участвуй в сезонных турнирах\n\n"
        f"🎁 <b>Новичкам — стартовый бонус!</b>\n\n"
        f"Нажми кнопку ниже чтобы начать 👇",
        reply_markup=start_kb,
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "show_menu")
async def show_menu_callback(callback: CallbackQuery):
    if callback.message.chat.type != "private":
        await callback.message.answer(
            "⚠️ Меню доступно только в личных сообщениях бота.",
            reply_markup=ReplyKeyboardRemove()
        )
        await callback.answer()
        return
    await callback.message.answer("🏠 Главное меню:", reply_markup=safe_reply_kb(callback.message, menu_kb))
    await callback.answer()


@dp.message(Command("myid"))
async def my_id_command(message: Message):
    await message.answer(
        f"🆔 Ваш Telegram ID: <code>{message.from_user.id}</code>",
        parse_mode="HTML"
    )


@dp.message(Command("дать"))
async def admin_give_command(message: Message):
    from admin_roles import has_permission
    from admin_logs import log_action

    user_id = message.from_user.id
    if not has_permission(user_id, "give_currency"):
        await message.answer("⛔ Нет прав.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "❌ Неверный формат.\n\nИспользуй: <code>/дать [ид] [сумма]</code>\nПример: <code>/дать 123456789 5000</code>",
            parse_mode="HTML"
        )
        return

    try:
        recipient_id = int(args[1].strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
        return

    amount = parse_k(args[2].strip())
    if not amount or amount <= 0:
        await message.answer("❌ Некорректная сумма.")
        return

    recipient = get_user(recipient_id)
    if not recipient:
        await message.answer("❌ Пользователь не найден.")
        return

    update_balance(recipient_id, get_balance(recipient_id) + amount)
    save_user_data()

    name = recipient.get("name", "Без имени")
    log_action(user_id, message.from_user.full_name, "give_currency", recipient_id, f"+{format_amount(amount)}$")

    await message.answer(
        f"✅ Выдано <b>{format_amount(amount)}$</b> → <b>{name}</b> (<code>{recipient_id}</code>)",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(recipient_id, f"💵 Вам выдали <b>{format_amount(amount)}$</b> от администратора.", parse_mode="HTML")
    except Exception:
        pass




TRANSFER_DAILY_VIP   = 10_000_000
TRANSFER_DAILY_NOVIP =  5_000_000


@dp.message(Command("лимит"))
async def transfer_limit_command(message: Message):
    import datetime
    from admin_roles import is_admin_any
    from donate import is_vip

    user_id = message.from_user.id

    if is_admin_any(user_id):
        await message.answer(
            "📋 <b>Информация о лимите переводов</b>\n\n"
            "⚡️ Статус: <b>Администратор</b>\n"
            "♾️ Суточный лимит: <b>Без ограничений</b>\n"
            "📤 Отправлено: <b>—</b>\n"
            "✅ Доступно: <b>∞</b>",
            parse_mode="HTML"
        )
        return

    vip = is_vip(user_id)
    daily_cap = TRANSFER_DAILY_VIP if vip else TRANSFER_DAILY_NOVIP

    user = get_user(user_id)
    today = datetime.date.today().isoformat()
    used = user.get("transfer_today", 0) if user.get("transfer_date") == today else 0
    remaining = max(daily_cap - used, 0)

    now = datetime.datetime.now()
    midnight = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time.min)
    delta = midnight - now
    hours, rem = divmod(int(delta.total_seconds()), 3600)
    minutes = rem // 60
    reset_str = f"{hours}ч. {minutes}м."

    filled = int((used / daily_cap) * 10) if daily_cap > 0 else 0
    bar = "🟩" * (10 - filled) + "🟥" * filled

    status = "💎 VIP" if vip else "👤 Стандарт"
    vip_hint = "" if vip else f"\n\n💡 <i>С VIP-статусом лимит увеличится до {format_amount(TRANSFER_DAILY_VIP)}$</i>"

    await message.answer(
        f"📋 <b>Информация о лимите переводов</b>\n\n"
        f"{bar}\n\n"
        f"⚡️ Статус: <b>{status}</b>\n"
        f"💸 Суточный лимит: <b>{format_amount(daily_cap)}$</b>\n"
        f"📤 Отправлено: <b>{format_amount(used)}$</b>\n"
        f"✅ Доступно: <b>{format_amount(remaining)}$</b>\n"
        f"⏳ До сброса: <b>{reset_str}</b>"
        f"{vip_hint}",
        parse_mode="HTML"
    )


@dp.message(F.text.lower().in_(["лимит", "/лимит", "лимиты", "мой лимит"]))
async def transfer_limit_text_command(message: Message):
    await transfer_limit_command(message)


@dp.message(Command("вип"))
@dp.message(F.text.lower().in_(["вип", "vip", "/вип", "/vip", "привилегии вип", "вип привилегии"]))
async def vip_info_command(message: Message):
    from donate import is_vip, VIP_BONUS_COOLDOWN, NONVIP_BONUS_COOLDOWN, VIP_BONUS_AMOUNT, NONVIP_BONUS_AMOUNT

    user_id = message.from_user.id
    has_vip = is_vip(user_id)

    vip_cd_h  = VIP_BONUS_COOLDOWN    // 3600
    novip_cd_h = NONVIP_BONUS_COOLDOWN // 3600

    status_line = "⭐ Статус: <b>VIP активен</b>" if has_vip else "👤 Статус: <b>Стандарт</b>"

    text = (
        f"💎 <b>VIP-привилегии</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{status_line}\n\n"
        f"<b>Что даёт VIP:</b>\n\n"
        f"🎁 <b>Бонус</b>\n"
        f"   • VIP: {format_amount(VIP_BONUS_AMOUNT)}$ каждые {vip_cd_h}ч.\n"
        f"   • Без VIP: {format_amount(NONVIP_BONUS_AMOUNT)}$ каждые {novip_cd_h}ч.\n\n"
        f"💼 <b>Работа</b>\n"
        f"   • Зарплата увеличена на <b>+50%</b>\n\n"
        f"💸 <b>Переводы</b>\n"
        f"   • VIP: <b>{format_amount(TRANSFER_DAILY_VIP)}$</b> в день\n"
        f"   • Без VIP: <b>{format_amount(TRANSFER_DAILY_NOVIP)}$</b> в день\n\n"
        f"👥 <b>Рефералы</b>\n"
        f"   • VIP: <b>15,000$</b> за приглашённого друга\n"
        f"   • Без VIP: <b>10,000$</b> за приглашённого друга\n\n"
        f"🏆 <b>Розыгрыши</b>\n"
        f"   • Доступ к эксклюзивным VIP-розыгрышам\n\n"
        f"⭐ <b>Значок</b>\n"
        f"   • VIP-звезда ⭐ рядом с именем\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    if not has_vip:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Купить VIP", callback_data="donate_vip")]
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer(text, parse_mode="HTML")


def _get_today_str() -> str:
    import datetime
    return datetime.date.today().isoformat()


def _get_transfer_used(sender_id: int) -> int:
    """Сколько уже переведено сегодня."""
    user = get_user(sender_id)
    if not user:
        return 0
    today = _get_today_str()
    if user.get("transfer_date") != today:
        user["transfer_date"]  = today
        user["transfer_today"] = 0
        save_user_data()
    return user.get("transfer_today", 0)


def _add_transfer_used(sender_id: int, amount: int):
    """Записываем сумму перевода в дневной счётчик."""
    user = get_user(sender_id)
    if not user:
        return
    today = _get_today_str()
    if user.get("transfer_date") != today:
        user["transfer_date"]  = today
        user["transfer_today"] = 0
    user["transfer_today"] = user.get("transfer_today", 0) + amount
    save_user_data()


def reset_all_daily_transfer_limits():
    """Сброс дневных лимитов у всех игроков — вызывается в 00:00."""
    today = _get_today_str()
    for uid, u in utils.user_data.items():
        u["transfer_date"]  = today
        u["transfer_today"] = 0
    save_user_data()


async def _do_transfer(message: Message, sender_id: int, recipient_id: int, amount_text: str):
    from donate import is_vip
    sender      = get_user(sender_id)
    sender_name = sender.get("name", "Без имени")

    if sender_id == recipient_id:
        await message.answer("❌ Нельзя перевести самому себе.", parse_mode="HTML")
        return

    sender_balance = get_balance(sender_id)
    amount = sender_balance if amount_text.lower() in ("все", "всё", "вб", "all") else parse_k(amount_text, sender_balance)
    if amount is None or amount <= 0:
        await message.answer(
            f"❌ {clickable_name(sender_id, sender_name)}, некорректная сумма.",
            parse_mode="HTML"
        )
        return

    # ── Дневной лимит (не применяется к админам) ──────────────────
    from admin_roles import is_admin_any
    is_admin = is_admin_any(sender_id)

    if not is_admin:
        vip        = is_vip(sender_id)
        daily_cap  = TRANSFER_DAILY_VIP if vip else TRANSFER_DAILY_NOVIP
        used_today = _get_transfer_used(sender_id)
        remaining  = daily_cap - used_today

        if remaining <= 0:
            vip_hint = "" if vip else f"\n💡 VIP увеличивает дневной лимит до {format_amount(TRANSFER_DAILY_VIP)}$!"
            await message.answer(
                f"❌ Дневной лимит переводов исчерпан!\n"
                f"📅 Лимит: <b>{format_amount(daily_cap)}$</b> в день\n"
                f"⏰ Обновляется в <b>00:00</b>{vip_hint}",
                parse_mode="HTML"
            )
            return

        if amount > remaining:
            vip_hint = "" if vip else f"\n💡 VIP увеличивает дневной лимит до {format_amount(TRANSFER_DAILY_VIP)}$!"
            await message.answer(
                f"❌ {clickable_name(sender_id, sender_name)}, превышен дневной лимит!\n"
                f"💸 Осталось сегодня: <b>{format_amount(remaining)}$</b>\n"
                f"📤 Вы хотите отправить: <b>{format_amount(amount)}$</b>\n"
                f"⏰ Лимит обновится в 00:00{vip_hint}",
                parse_mode="HTML"
            )
            return

    if sender_balance < amount:
        await message.answer(
            f"❌ {clickable_name(sender_id, sender_name)}, недостаточно средств.\n"
            f"💰 Ваш баланс: <b>{format_amount(sender_balance)}$</b>",
            parse_mode="HTML"
        )
        return

    recipient = get_user(recipient_id)
    if not recipient:
        await message.answer("❌ Получатель не найден.", parse_mode="HTML")
        return

    recipient_name = recipient.get("name", "Без имени")
    update_balance(sender_id, sender_balance - amount)
    update_balance(recipient_id, get_balance(recipient_id) + amount)
    if not is_admin:
        _add_transfer_used(sender_id, amount)
    save_user_data()

    if is_admin:
        remaining_line = ""
    else:
        new_remaining = remaining - amount
        remaining_line = f"\n📅 Осталось сегодня: <b>{format_amount(new_remaining)}$</b>"
    await message.answer(
        f"✅ {clickable_name(sender_id, sender_name)} перевёл "
        f"<b>{format_amount(amount)}$</b> → {clickable_name(recipient_id, recipient_name)}"
        f"{remaining_line}",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            recipient_id,
            f"💸 <b>{clickable_name(sender_id, sender_name)}</b> перевёл вам <b>{format_amount(amount)}$</b>!",
            parse_mode="HTML"
        )
    except Exception:
        pass


def _parse_transfer_args(text: str, has_reply: bool):
    """
    Парсит аргументы команды перевода.
    Возвращает (identifier_or_none, amount_text_or_none)
    """
    parts = text.split(maxsplit=2)
    if has_reply:
        # "дать 1000" или "дать"
        amount = parts[1].strip() if len(parts) >= 2 else None
        return None, amount
    else:
        # "дать @user 1000" или "передать 12345 500"
        if len(parts) >= 3:
            return parts[1].strip(), parts[2].strip()
        return None, None


@dp.message(F.text.lower().startswith(("передать", "дать")), StateFilter(default_state))
async def handle_transfer(message: Message):
    user_id = message.from_user.id
    text    = message.text.strip()
    has_reply = bool(message.reply_to_message and message.reply_to_message.from_user)

    identifier, amount_text = _parse_transfer_args(text, has_reply)

    # Определяем получателя
    if has_reply:
        recipient_id = message.reply_to_message.from_user.id
    elif identifier:
        from utils import user_data as _ud
        recipient_id, _ = find_user_by_identifier(identifier, _ud)
        if not recipient_id:
            await message.answer(
                f"❌ Игрок <b>{identifier}</b> не найден.", parse_mode="HTML"
            )
            return
    else:
        await message.answer(
            "❌ Укажи получателя или ответь на его сообщение.\n\n"
            "📌 Форматы:\n"
            "<code>дать 5000</code> — ответом на сообщение\n"
            "<code>дать @username 5000</code>\n"
            "<code>дать 12345 5000</code> — по ID",
            parse_mode="HTML"
        )
        return

    if not amount_text:
        await message.answer(
            "❌ Укажи сумму.\n\n"
            "📌 Форматы:\n"
            "<code>дать 5000</code> — ответом на сообщение\n"
            "<code>дать @username 5000</code>",
            parse_mode="HTML"
        )
        return

    await _do_transfer(message, user_id, recipient_id, amount_text)
    
    

    
    
@dp.message(F.text.lower().in_(["авто", "машина", "/авто", "/машина", "гараж", "/гараж"]))
async def show_cars(message: Message):
    from smart_assets import build_shop_car_response, build_shop_car_shop_response

    user_id = message.from_user.id
    result = build_shop_car_response(user_id)
    if result:
        text, kb = result
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        text, kb = build_shop_car_shop_response(user_id)
        await message.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query(F.data == "cshop_open")
async def cb_cshop_open(callback: CallbackQuery):
    from auto_shop import get_car_shop_kb, car_shop_text
    user_id = callback.from_user.id
    user = get_user(user_id)
    owned_key = user.get("shop_car")
    await callback.message.edit_text(
        car_shop_text(0, owned_key),
        parse_mode="HTML",
        reply_markup=get_car_shop_kb(0, owned_key)
    )
    await callback.answer()


@dp.message(F.text.lower().in_(["баланс", "балик", "💰 баланс", 'balance', 'б', '/баланс', '/balance', '/б']))
async def show_balance(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    balance = get_balance(user_id)
    await message.answer(
        f"💰 Баланс {clickable_name(user_id, name)}: <b>{format_amount(balance)}$</b>",
        parse_mode="HTML"
    )


@dp.message(F.text.lower().in_(["битки", "биткоин", "мои биткоины", "btc", "/btc", "/битки", "₿"]))
async def cmd_btc_balance(message: Message):
    from farm import get_farm, get_btc_price, flush_farm, _fmt_btc
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    farm = get_farm(user_id)
    flush_farm(farm)
    btc_bal = farm.get("btc_balance", 0.0)
    btc_price = get_btc_price()
    btc_usd = int(btc_bal * btc_price)
    farm_lvl = farm.get("farm_level", 0)
    if farm_lvl == 0:
        await message.answer(
            f"₿ {clickable_name(user_id, name)}: у тебя нет BTC фермы.\n"
            f"Напиши <b>ферма</b> чтобы купить.",
            parse_mode="HTML"
        )
        return
    await message.answer(
        f"₿ <b>Bitcoin кошелёк</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {clickable_name(user_id, name)}\n\n"
        f"₿ Баланс: <b>{_fmt_btc(btc_bal)} BTC</b>\n"
        f"💵 В долларах: <b>~{format_amount(btc_usd)}$</b>\n"
        f"📈 Курс BTC: <b>{format_amount(int(btc_price))}$</b>",
        parse_mode="HTML"
    )


@dp.message(F.text.lower().in_(["🎁 бонус", "бонус", "/бонус", "/bonus"]))
async def bonus_command(message: Message):
    from donate import is_vip, VIP_BONUS_COOLDOWN, NONVIP_BONUS_COOLDOWN, VIP_BONUS_AMOUNT, NONVIP_BONUS_AMOUNT
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    current_time = time.time()
    last_bonus_time = user.get("last_bonus_time", 0)
    elapsed_time = current_time - last_bonus_time
    vip = is_vip(user_id)
    cooldown = VIP_BONUS_COOLDOWN if vip else NONVIP_BONUS_COOLDOWN
    bonus_amount = VIP_BONUS_AMOUNT if vip else NONVIP_BONUS_AMOUNT
    try:
        from house_shop import get_shop_house_boosts
        _cd_pct = get_shop_house_boosts(user_id).get("bonus_cd_pct", 0)
        if _cd_pct:
            cooldown = int(cooldown * (1 - _cd_pct / 100))
    except Exception:
        pass
    if elapsed_time < cooldown:
        remaining = int((cooldown - elapsed_time) / 60)
        hours, mins = divmod(remaining, 60)
        time_str = f"{hours}ч {mins}мин" if hours else f"{mins} мин"
        vip_hint = "" if vip else "\n\n💡 VIP: бонус каждые 12 часов + 500$ сверху!"
        await message.answer(
            f"❌ {clickable_name(user_id, name)}, вы уже получали бонус.\n"
            f"Попробуйте через <b>{time_str}</b>.{vip_hint}",
            parse_mode="HTML"
        )
        return
    update_balance(user_id, get_balance(user_id) + bonus_amount)
    user["last_bonus_time"] = current_time
    save_user_data()
    vip_badge = " ⭐" if vip else ""
    # Воблер — баннер бонуса
    try:
        from image_gen import gen_wobbler
        from aiogram.types import BufferedInputFile
        buf = gen_wobbler(format_amount(bonus_amount), name, is_vip=bool(vip))
        photo = BufferedInputFile(buf.read(), filename="bonus.png")
        await message.answer_photo(photo=photo)
    except Exception:
        pass
    await message.answer(
        f"🎉 {clickable_name(user_id, name)}{vip_badge}, вы получили бонус: <b>{format_amount(bonus_amount)}$</b>!\n"
        f"💰 Новый баланс: <b>{format_amount(get_balance(user_id))}$</b>",
        parse_mode="HTML"
    )

@dp.message(F.text.lower().in_(["реф", "реферальная система", "рефка", "/ref", "🔗 реферальная система", "/реф"]))
async def send_referral_link(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    referral_link = f"https://t.me/{bot_username}?start=ref{user_id}"
    if message.chat.type == "private":
        await message.answer(
            f"🔗 {clickable_name(user_id, name, clickable)} ваша реферальная ссылка:\n{referral_link}\n\n"
            "Приглашайте друзей и получайте бонусы за каждого приглашенного!",
            reply_markup=safe_reply_kb(message, ref_kb),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"🔗 {clickable_name(user_id, name, clickable)} ваша реферальная ссылка:\n{referral_link}\n\n"
            "Приглашайте друзей и получайте бонусы за каждого приглашенного!\n\n"
            "Клавиатура доступна только в личных сообщениях с ботом.",
            parse_mode="HTML"
        )


@dp.message(F.text.lower().startswith("помощь"))
async def help_command(message: Message):
    text = message.text.lower().replace("ё", "е").split()
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    if len(text) < 2:
        await message.answer(
            f"❓ {clickable_name(message.from_user.id, name, clickable)}, укажите тему или команду для получения инструкции.\n\n"
            "📌 <b>Пример:</b> <code>помощь краш</code>\n"
            "📋 Для списка всех команд: <code>команды</code>\n\n"
            "💡 Если нашли баг или есть предложение — напишите <b>репорт</b> или <b>поддержка</b> и ваш текст.\n"
            "✉️ Пример: <code>репорт не работает банк</code>",
            parse_mode="HTML",
        )
        return

    # Поддержка одно- и двухсловных тем (напр. "помощь клан чат")
    topic = text[1]
    topic2 = " ".join(text[1:3]) if len(text) >= 3 else ""
    found_key = None
    for key, synonyms in help_synonyms.items():
        if topic2 and topic2 in synonyms:
            found_key = key
            break
        if topic in synonyms:
            found_key = key
            break

    help_texts = {
        "рулетка": roulette_help_text,
        "блэкджек": blackjack_help_text,
        "мины": mines_help_text,
        "передать": transfer_help_text,
        "игры": games_help_text,
        "банк": bank_help_text,
        "вклад": deposit_help_text,
        "краш": crash_help_text,
        "репорт": report_help_text,
        "монетка": coin_help_text,
        "бонус": bonus_help_text,
        "профиль": profile_help_text,
        "ник": profile_help_text,
        "кликабельность": profile_help_text,
        "баскет": basket_help_text,
        "пенка": penka_help_text,
        "дартс": darts_help_text,
        "дуэль": duel_help_text,
        "клан_чат": clan_chat_help_text,
        "help": all_commands_text,
    }

    if found_key and found_key in help_texts:
        await message.answer(help_texts[found_key], parse_mode="HTML")
    else:
        await message.answer(
            f"❌ {clickable_name(message.from_user.id, name, clickable)}, нет инструкции по теме: {topic}\n"
            "Для списка всех команд используйте <code>команды</code>.",
            parse_mode="HTML"
        )


@dp.message(F.text.lower().in_(["команды", "список команд", "all commands"]))
async def all_commands_handler(message: Message):
    await message.answer(all_commands_text, parse_mode="HTML")


@dp.message(F.text.lower().in_(["✏️ изменить имя", "изменить имя"]))
async def change_name_prompt(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    await message.answer("Введите новое имя:")
    await state.set_state(SettingsState.waiting_for_new_name)


@dp.message(
    F.text.lower().in_(["рефералы", "мои рефералы", "/referrals", "👥 рефералы"])
)
async def show_referrals(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    referrals = user.get("referrals", [])
    if not referrals:
        await message.answer(
            f"❌ {clickable_name(user_id, name)}, у вас пока нет приглашённых пользователей.",
            parse_mode="HTML"
        )
        return

    referral_list = ""
    for i, ref in enumerate(referrals):
        ref_user = get_user(ref)
        if not ref_user:
            continue  # Пропускаем несуществующих пользователей
        ref_name = ref_user.get("name", "Без имени")
        referral_list += f"{i + 1}. {clickable_name(ref, ref_name)} — {get_balance(ref)}$\n"

    if not referral_list:
        referral_list = "Нет активных приглашённых пользователей."

    await message.answer(
        f"👥 {clickable_name(user_id, name)}, ваши приглашённые пользователи:\n\n{referral_list}",
        reply_markup=safe_reply_kb(message, menu_kb),
        parse_mode="HTML"
    )


@dp.message(SettingsState.waiting_for_new_name)
async def process_new_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    new_name = message.text.strip()
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    if len(new_name) > 30:
        await message.answer("❌ Имя слишком длинное. Максимум 30 символов.")
        return

    set_name(user_id, new_name)  # Сохраняем новое имя
    await message.answer(f"✅ Ваше имя изменено на: {new_name}", reply_markup=safe_reply_kb(message, menu_kb))
    await state.clear()


@dp.message(F.text.lower() == "жопа")
async def handle_caczka_command(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Жопа", callback_data="жопа")]
        ]
    )
    await message.answer("ㅤ", reply_markup=keyboard)

@dp.callback_query(F.data == "жопа")
async def handle_caczka_callback(callback: CallbackQuery):
    await callback.answer("ㅤ\nㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤЖопа", show_alert=True)




@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: CallbackQuery):
    kb = get_kb_for_user(callback.from_user.id)
    await callback.message.answer("Меню:", reply_markup=safe_reply_kb(callback.message, kb))
    await callback.answer()

@dp.message(F.text.lower().in_(["🔗 кликабельность ника", "кликабельность ника"]))
async def toggle_clickable_name(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    # Переключаем состояние кликабельности
    user["clickable_name"] = not user.get("clickable_name", True)
    save_user_data()

    # Отправляем сообщение о текущем состоянии
    if user["clickable_name"]:
        await message.answer(
            "✅ Кликабельность ника включена.", reply_markup=safe_reply_kb(message, settings_kb)
        )
    else:
        await message.answer(
            "❌ Кликабельность ника отключена.", reply_markup=safe_reply_kb(message, settings_kb)
        )
        

@dp.message(F.text.lower().in_(["🎰 рулетка", "рулетка", "/рулетка"]))
async def roulette_info(message: Message):
    await message.answer(roulette_help_text, parse_mode="HTML")


@dp.message(F.text.lower().in_(["🃏 блэкджек", "блэкджек", "🃏 блек джек", "блек джек", "/бд", "/блэкджек"]))
async def blackjack_info(message: Message):
    await message.answer(blackjack_help_text, parse_mode="HTML")


@dp.message(F.text.lower().in_(["💣 мины", "/мины"]))
async def mines_info(message: Message):
    await message.answer(mines_help_text, parse_mode="HTML")


@dp.message(F.text.lower().in_(["💥 краш", "краш", "/краш"]))
async def crash_instruction(message: Message):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    await message.answer(
        f"💥 {clickable_name(message.from_user.id, name, clickable)} — инструкция по крашу:\n"
        "Напиши: <code>краш [коэффициент] [сумма]</code>\n"
        "Пример: <code>краш 2.5 1000</code>\n"
        "Подробнее: <code>помощь краш</code>",
        parse_mode="HTML"
    )


def _get_shop_house_name(user_id: int) -> str:
    try:
        from house_shop import get_shop_house_boosts, SHOP_HOUSES
        user = get_user(user_id)
        key = user.get("shop_house")
        if key and key in SHOP_HOUSES:
            h = SHOP_HOUSES[key]
            return f"{h['name']} ({h['desc']})"
    except Exception:
        pass
    return "Нет"


@dp.message(F.text.lower().in_(["profile", "профиль", "проф", "я", "z", "👤 профиль", "/профиль", "/profile", "/проф"]))
async def show_profile(message: Message):
    from player_info import _send_info
    user_id = message.from_user.id
    username = message.from_user.username
    if username:
        update_telegram_username(user_id, username)
    await _send_info(message, user_id, viewer_uid=user_id)


@dp.pre_checkout_query()
async def dp_pre_checkout(pre_checkout_query):
    await handle_pre_checkout(pre_checkout_query)


@dp.message(F.successful_payment)
async def dp_successful_payment(message: Message):
    await handle_successful_payment(message)


@dp.message(
    F.text.lower().in_(["настройки", "settings", "/settings", "/setting", "настройка", "⚙️ настройки"])
)
async def show_settings(message: Message):
    if message.chat.type == "private":
        await message.answer("⚙️ Настройки:", reply_markup=safe_reply_kb(message, settings_kb)
        )
    else:
        await message.answer("⚙️ Настройки доступны только в личных сообщениях с ботом.")


@dp.message(F.text.lower().in_(["сайт", "/сайт", "сайт топа", "/site", "site"]))
async def show_site(message: Message):
    site_url = os.environ.get("REPLIT_DEV_DOMAIN", "")
    url = f"https://{site_url}" if site_url else "временно недоступен"
    await message.answer(
        f"🌐 <b>Blackline — Таблица лидеров</b>\n\n"
        f"💰 Баланс · ⭐ Уровень · 👥 Рефералы\n\n"
        f"{url}",
        parse_mode="HTML",
    )


@dp.message(F.text.lower().in_(["menu", "меню", "менюшка", "/menu", "🏠 меню", 'м', 'm']))
async def show_menu(message: Message):
    if message.chat.type == "private":
        kb = get_kb_for_user(message.from_user.id)
        await message.answer("Меню:", reply_markup=safe_reply_kb(message, kb))
    else:
        await message.answer("Меню доступно только в личных сообщениях с ботом.")


@dp.message(F.text.lower().in_(["🌱 развитие", "развитие"]))
async def show_razvitie(message: Message):
    if message.chat.type == "private":
        await message.answer(
            "🌱 <b>Развитие</b>\n\n"
            "• 🏦 <b>Банк</b> — храни деньги, открывай вклады\n"
            "• 🛡 <b>Кланы</b> — вступай в клан или создай свой\n"
            "• 🖥 <b>Ферма</b> — добывай биткоины, продавай и переводи\n\n"
            "• 🏡 <b>Дом</b> — твоё жильё или магазин домов\n"
            "• 🏎 <b>Авто</b> — твоё авто или магазин\n"
            "• 🏢 <b>Бизнес</b> — твои бизнесы или купить новый\n"
            "• 🏪 <b>Магазин</b> — купить дом, авто или бизнес",
            parse_mode="HTML",
            reply_markup=get_razvitie_inline_kb()
        )
    else:
        await message.answer("Меню доступно только в личных сообщениях с ботом.")


@dp.callback_query(F.data == "rzv_back")
async def cb_rzv_back(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌱 <b>Развитие</b>\n\n"
        "• 🏦 <b>Банк</b> — храни деньги, открывай вклады\n"
        "• 🛡 <b>Кланы</b> — вступай в клан или создай свой\n"
        "• 🖥 <b>Ферма</b> — добывай биткоины, продавай и переводи\n\n"
        "• 🏡 <b>Дом</b> — твоё жильё или магазин домов\n"
        "• 🏎 <b>Авто</b> — твоё авто или магазин\n"
        "• 🏢 <b>Бизнес</b> — твои бизнесы или купить новый\n"
        "• 🏪 <b>Магазин</b> — купить дом, авто или бизнес",
        parse_mode="HTML",
        reply_markup=get_razvitie_inline_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "rzv_bank")
async def cb_rzv_bank(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    bank_sum = user.get("user_bank", 0)
    text = (
        f"🏦 <b>Банк {clickable_name(user_id, name, clickable)}</b>\n\n"
        f"📦 <b>Счёт:</b> <code>{format_amount(bank_sum)}$</code>\n\n"
        "➕ <b>Пополнить</b>: <code>банк (сумма)</code>\n"
        "➖ <b>Снять</b>: <code>банк -(сумма)</code>\n"
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=get_bank_main_kb())
    await callback.answer()


@dp.callback_query(F.data == "rzv_klan")
async def cb_rzv_klan(callback: CallbackQuery):
    from clans import get_user_clan, _clan_main_text, _clan_main_kb, _no_clan_kb, _get_role
    user_id = callback.from_user.id
    clan = get_user_clan(user_id)
    if clan:
        await callback.message.answer(
            _clan_main_text(clan, user_id),
            parse_mode="HTML",
            reply_markup=_clan_main_kb(clan["id"], user_role=_get_role(clan, user_id))
        )
    else:
        await callback.message.answer(
            "🛡 <b>КЛАНОВАЯ СИСТЕМА</b>\n\n"
            "Вы не состоите ни в одном клане.\n"
            "Создайте свой или вступите в существующий!",
            parse_mode="HTML",
            reply_markup=_no_clan_kb()
        )
    await callback.answer()


@dp.callback_query(F.data == "rzv_ferma")
async def cb_rzv_ferma(callback: CallbackQuery):
    from farm import _send_farm
    await _send_farm(callback.message, callback.from_user.id)
    await callback.answer()


@dp.callback_query(F.data == "rzv_dom")
async def cb_rzv_dom(callback: CallbackQuery):
    from smart_assets import build_house_response, build_house_shop_response
    user_id = callback.from_user.id
    result = build_house_response(user_id)
    if result:
        text, kb = result
    else:
        text, kb = build_house_shop_response(user_id)
    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "rzv_avto")
async def cb_rzv_avto(callback: CallbackQuery):
    from smart_assets import build_car_response
    from racing_shop import _page_text, _page_kb
    user_id = callback.from_user.id
    result = build_car_response(user_id)
    if result:
        text, kb = result
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.answer(_page_text(0, user_id), reply_markup=_page_kb(0, user_id), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "rzv_biz")
async def cb_rzv_biz(callback: CallbackQuery):
    from smart_assets import build_donate_biz_card
    from business_shop import biz_shop_text, get_biz_shop_kb, my_biz_text, my_biz_kb
    from utils import get_user
    user_id = callback.from_user.id
    user = get_user(user_id)
    owned = user.get("businesses", [])
    if owned:
        await callback.message.answer(my_biz_text(user, 0), reply_markup=my_biz_kb(user, 0), parse_mode="HTML")
        don_card = build_donate_biz_card(user_id)
        if don_card:
            text, kb = don_card
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        don_card = build_donate_biz_card(user_id)
        if don_card:
            text, kb = don_card
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.answer(biz_shop_text(0, owned), reply_markup=get_biz_shop_kb(0, owned), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "rzv_magazin")
async def cb_rzv_magazin(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "🏪 <b>Магазин</b>\n\nВыбери что хочешь купить:",
            parse_mode="HTML",
            reply_markup=get_razvitie_shop_inline_kb()
        )
    except Exception:
        await callback.message.answer(
            "🏪 <b>Магазин</b>\n\nВыбери что хочешь купить:",
            parse_mode="HTML",
            reply_markup=get_razvitie_shop_inline_kb()
        )
    await callback.answer()


@dp.callback_query(F.data == "rzv_mag_dom")
async def cb_rzv_mag_dom(callback: CallbackQuery):
    from house_shop import house_shop_text, get_house_shop_kb
    from utils import get_user
    user_id = callback.from_user.id
    user = get_user(user_id)
    owned_key = user.get("shop_house")
    await callback.message.answer(
        house_shop_text(0, owned_key),
        parse_mode="HTML",
        reply_markup=get_house_shop_kb(0, owned_key)
    )
    await callback.answer()


@dp.callback_query(F.data == "rzv_mag_avto")
async def cb_rzv_mag_avto(callback: CallbackQuery):
    from racing_shop import rcar_text, rcar_kb
    user_id = callback.from_user.id
    await callback.message.answer(
        rcar_text(0, user_id),
        reply_markup=rcar_kb(0, user_id),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "rzv_mag_biz")
async def cb_rzv_mag_biz(callback: CallbackQuery):
    from business_shop import biz_shop_text, get_biz_shop_kb
    from utils import get_user
    user_id = callback.from_user.id
    user = get_user(user_id)
    owned = user.get("businesses", [])
    await callback.message.answer(biz_shop_text(0, owned), reply_markup=get_biz_shop_kb(0, owned), parse_mode="HTML")
    await callback.answer()


@dp.message(F.text.lower().in_(["игры", "games", "игрульки", "🎮 игры", "/игры"]))
async def show_games(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    games_text = (
        f"🎮 {clickable_name(user_id, name, clickable)}, вот доступные игры:\n\n"
        "• 🎰 <b>Рулетка</b> — ставь на цвет или дюжину!\n"
        "   Пример: <code>р к 10к</code> (x2), <code>р з 1м</code> (x35)\n"
        "• 🃏 <b>Блэкджек</b> — набери 21 и обыграй дилера!\n"
        "   Пример: <code>бд 5000</code>\n"
        "• 💣 <b>Мины</b> — открывай клетки и не попади на мину!\n"
        "   Пример: <code>мины 5 10к</code>\n"
        "• 💥 <b>Краш</b> — угадай коэффициент и забери выигрыш!\n"
        "   Пример: <code>краш 2.5 1000</code>\n"
        "• 🪙 <b>Монетка</b> — орёл или решка против соперника!\n"
        "   Пример: <code>монетка орел 1000</code>\n"
        "• 💼 <b>Работа</b> — выбери профессию и зарабатывай!\n"
        "\nПодробнее: <code>помощь [игра]</code>"
    )
    if message.chat.type == "private":
        await message.answer(
            games_text,
            parse_mode="HTML",
            reply_markup=safe_reply_kb(message, games_kb),
        )
    else:
        await message.answer(
            f"🎮 {clickable_name(user_id, name, clickable)}, клавиатура доступна только в личных сообщениях с ботом.",
            parse_mode="HTML"
        )
        
        
@dp.message(F.text.lower().in_(["🪙 монетка"]))
async def coin_game_instruction(message: Message):
    from games import coin_games
    from utils import clickable_name as cn
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    waiting = [(gid, g) for gid, g in coin_games.items() if g.get("status") == "waiting"]
    if not waiting:
        await message.answer(
            "🪙 <b>Монетка</b> — активных игр нет.\n\n"
            "Создай игру:\n"
            "<code>монетка о 1000</code> — орёл\n"
            "<code>монетка р 1000</code> — решка",
            parse_mode="HTML"
        )
        return
    text = "🪙 <b>Активные игры монетка:</b>\n\n"
    kb_rows = []
    for gid, game in waiting:
        side_emoji = "🦅" if game["choice"] == "орел" else "🪙"
        text += (
            f"<b>№{gid}</b> {side_emoji} {game['choice'].capitalize()} | "
            f"<b>{format_amount(game['amount'])}$</b> | "
            f"{cn(game['creator_id'], game['creator_name'], True)}\n"
        )
        kb_rows.append([InlineKeyboardButton(
            text=f"Принять монетку #{gid}",
            callback_data=f"coin_accept:{gid}"
        )])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)
        


@dp.message(F.text.lower().startswith("ник"))
async def change_name_command(message: Message):
    user_id = message.from_user.id
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "❌ Укажите новое имя. Пример: <code>ник Иван</code>", parse_mode="HTML"
        )
        return

    new_name = parts[1].strip()

    if len(new_name) > 30:
        await message.answer("❌ Имя слишком длинное. Максимум 30 символов.")
        return

    set_name(user_id, new_name)
    await message.answer(f"✅ Ваше имя изменено на: {new_name}", reply_markup=safe_reply_kb(message, menu_kb))
    


@dp.message(F.text.lower().in_(["❓ помощь"]))
async def help_short(message: Message):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    await message.answer(
        f"❓ {clickable_name(message.from_user.id, name, clickable)}, укажите тему или команду для получения инструкции.\n"
        "Пример: <code>помощь краш</code>\n"
        "Для списка всех команд используйте <code>команды</code>.\n"
        "Если вы нашли баг или у вас есть предложение по улучшению бота — напишите в поддержку.\n"
        "Команда: Репорт (сообщение)\n",
        parse_mode="HTML",
    )


@dp.message(F.text.lower().in_(["банк", "bank", "/bank", "🏦 банк", "/банк"]))
async def show_bank_menu(message: Message):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    bank_sum = user.get('user_bank', 0)
    await message.answer(
        f"🏦 <b>Банк {clickable_name(message.from_user.id, name, clickable)}</b>\n\n"
        f"📦 <b>Счёт:</b> <code>{format_amount(bank_sum)}$</code>\n\n\n"
        "➕ <b>Пополнить</b>: <code>банк (сумма)</code>\n"
        "➖ <b>Снять</b>: <code>банк -(сумма)</code>\n",
        parse_mode="HTML",
        reply_markup=get_bank_main_kb()
    )


@dp.callback_query(F.data == "bank_deposits")
async def bank_deposits_callback(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    deposits = user.get("user_deposits", [])
    text = "📈 <b>Ваши вклады:</b>\n\n"
    total = 0
    if not deposits:
        text += "Нет активных вкладов.\n"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать вклад", callback_data="create_deposit")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")],
            ]
        )
    else:
        for i, dep in enumerate(deposits, 1):
            text += (
            f"{i}. {format_amount(dep['amount'])}$ — {dep['days']} дн., {dep['percent']}%/день\n"
        )
            total += dep['amount']
        text += f"\n<b>Сумма всех вкладов:</b> <code>{format_amount(total)}$</code>\n"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать вклад", callback_data="create_deposit")],
                [InlineKeyboardButton(text="❌ Закрыть вклад", callback_data="close_deposit")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")],
            ]
        )
    text += "\nМаксимум 3 вклада, общая сумма не более 1 000 000$."
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb,
    )
    await callback.answer()
    
    
    
@dp.callback_query(F.data == "close_deposit")
async def close_deposit_callback(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    deposits = user.get("user_deposits", [])
    if not deposits:
        await callback.answer("У вас нет вкладов.", show_alert=True)
        return
    # Кнопки по номерам вкладов
    buttons = [
        [InlineKeyboardButton(text=f"Вклад {i+1}", callback_data=f"close_deposit_{i}")]
        for i in range(len(deposits))
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_deposits")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        "Выберите вклад для закрытия:",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("close_deposit_"))
async def close_deposit_number_callback(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    deposits = user.get("user_deposits", [])
    try:
        idx = int(callback.data.replace("close_deposit_", ""))
        deposit = deposits[idx]
    except (ValueError, IndexError):
        await callback.answer("Некорректный номер вклада.", show_alert=True)
        return

    # Проверяем, истёк ли срок вклада
    now = int(time.time())
    days_passed = (now - deposit["start"]) // 86400
    is_early = days_passed < deposit["days"]

    if is_early:
        # Сохраняем индекс вклада в FSM для подтверждения
        await state.update_data(close_deposit_idx=idx)
        await callback.message.edit_text(
            f"⚠️ Вы собираетесь закрыть вклад досрочно!\n"
            f"Вам будет возвращена только исходная сумма: <b>{format_amount(deposit['amount'])}$</b> (без процентов).\n\n"
            "Вы уверены, что хотите закрыть вклад?\n\n"
            "Напишите <code>да</code> для подтверждения или <code>нет</code> для отмены.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_deposits")]
                ]
            ),
            parse_mode="HTML"
        )
        await state.set_state("waiting_for_close_deposit_confirm")
    else:
        update_balance(callback.from_user.id, get_balance(callback.from_user.id) + deposit["amount"])
        deposits.pop(idx)
        save_user_data()
        await callback.message.edit_text(
            f"✅ Вклад на <b>{format_amount(deposit['amount'])}$</b> закрыт и возвращён на счёт.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📈 Вклады", callback_data="bank_deposits")],
                    [InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")],
                ]
            ),
            parse_mode="HTML"
        )
        await callback.answer()
    
    
@dp.callback_query(F.data == "create_deposit")
async def create_deposit_callback(callback: CallbackQuery, state: FSMContext):
    user = get_user(callback.from_user.id)
    deposits = user.get("user_deposits", [])
    total = sum(dep['amount'] for dep in deposits)
    if len(deposits) >= 3:
        await callback.message.answer("❌ У вас уже 3 вклада. Сначала закройте один из них.")
        await callback.answer()
        return
    if total >= 1_000_000:
        await callback.message.answer("❌ Сумма всех вкладов не может превышать 1 000 000$.")
        await callback.answer()
        return
    await callback.message.edit_text(
        "Выберите срок вклада:",
        reply_markup=get_deposit_terms_kb()
    )
    await state.set_state(BankDepositState.waiting_for_deposit_amount)
    await callback.answer()

@dp.callback_query(F.data == "bank_main")
async def bank_main_callback(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    process_deposits(user)
    bank_sum = user.get('user_bank', 0)
    deposits = user.get("user_deposits", [])
    deposits_text = ""
    if deposits:
        deposits_text = "\n📈 <b>Вклады:</b>\n"
        for i, dep in enumerate(deposits, 1):
            deposits_text += f"{i}. {format_amount(dep['amount'])}$ — {dep['days']} дн., {dep['percent']}%/день\n"
        deposits_text += f"\n<b>Сумма всех вкладов:</b> <code>{sum(dep['amount'] for dep in deposits):,}$</code>\n"
    else:
        deposits_text = "\n📈 Вклады: отсутствуют\n"

    await callback.message.answer(
        f"🏦 <b>Банк</b>\n\n"
        f"📦 <b>Счёт:</b> <code>{bank_sum:,}$</code>\n\n\n"
        "➕ <b>Пополнить</b>: <code>банк (сумма)</code>\n"
        "➖ <b>Снять</b>: <code>банк -(сумма)</code>\n",
        parse_mode="HTML",
        reply_markup=get_bank_main_kb()
    )
    await callback.answer()


@dp.message(StateFilter("waiting_for_close_deposit_confirm"))
async def confirm_close_deposit(message: Message, state: FSMContext):
    answer = message.text.strip().lower()
    data = await state.get_data()
    idx = data.get("close_deposit_idx")
    user = get_user(message.from_user.id)
    deposits = user.get("user_deposits", [])
    if answer == "да" and idx is not None and 0 <= idx < len(deposits):
        deposit = deposits[idx]
        update_balance(message.from_user.id, get_balance(message.from_user.id) + deposit["amount"])
        deposits.pop(idx)
        save_user_data()
        await message.answer(
            f"✅ Вклад на {format_amount(deposit['amount'])}$ досрочно закрыт и возвращён на счёт (без процентов).",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📈 Вклады", callback_data="bank_deposits")],
                    [InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")],
                ]
            )
        )
        await state.clear()
    elif answer == "нет":
        await message.answer("❌ Закрытие вклада отменено.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📈 Вклады", callback_data="bank_deposits")]]
        ))
        await state.clear()
    else:
        await message.answer("❓ Напишите `да` для подтверждения или `нет` для отмены.")


@dp.message(F.text.lower().in_(["вклады", "вклад"]))
async def show_deposits_command(message: Message):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    deposits = user.get("user_deposits", [])
    text = f"📈 <b>Вклады {clickable_name(message.from_user.id, name, clickable)}:</b>\n\n"
    total = 0
    if not deposits:
        text += "Нет активных вкладов.\n"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать вклад", callback_data="create_deposit")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")],
            ]
        )
    else:
        for i, dep in enumerate(deposits, 1):
            text += (
                f"{i}. {dep['amount']:,}$ — {dep['days']} дн., {dep['percent']}%/день\n"
            )
            total += dep['amount']
        text += f"\n<b>Сумма всех вкладов:</b> <code>{total:,}$</code>\n"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать вклад", callback_data="create_deposit")],
                [InlineKeyboardButton(text="❌ Закрыть вклад", callback_data="close_deposit")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")],
            ]
        )
    text += "\nМаксимум 3 вклада, общая сумма не более 1 000 000$."
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb,
    )


@dp.callback_query(F.data.in_(["deposit_1d", "deposit_3d", "deposit_7d"]))
async def deposit_choose_term(callback: CallbackQuery, state: FSMContext):
    terms = {
        "deposit_1d": (1, 3),
        "deposit_3d": (3, 5),
        "deposit_7d": (7, 7),
    }
    days, percent = terms[callback.data]
    await callback.message.edit_text(
        f"Введите сумму для депозита (до {format_amount(BANK_DEPOSIT_LIMIT)}$):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_deposits")]]
        )
    )
    await state.update_data(deposit_days=days, deposit_percent=percent)
    await state.set_state(BankDepositState.waiting_for_deposit_amount)
    await callback.answer()


@dp.message(StateFilter(BankDepositState.waiting_for_deposit_amount))
async def deposit_amount_input(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    data = await state.get_data()
    if "deposit_days" not in data or "deposit_percent" not in data:
        await message.answer("❌ Сначала выберите срок вклада через кнопки!")
        await state.clear()
        return
    days = data["deposit_days"]
    percent = data["deposit_percent"]
    text = message.text.lower().replace(" ", "")
    if text in ["все", "всё", "all"]:
        available = get_balance(message.from_user.id)
        amount = min(available, BANK_DEPOSIT_LIMIT)
        if amount < 100:
            await message.answer("❌ Недостаточно средств для открытия вклада (минимум 100$).")
            return
    else:
        text = text.replace("к", "000").replace("k", "000")
        try:
            amount = int(text)
        except ValueError:
            await message.answer("❌ Введите корректную сумму.")
            return
    if amount < 100 or amount > BANK_DEPOSIT_LIMIT:
        await message.answer(f"❌ Сумма вклада должна быть от 100 до {format_amount(BANK_DEPOSIT_LIMIT)}$.")
        return
    if get_balance(message.from_user.id) < amount:
        await message.answer("❌ Недостаточно средств на балансе.")
        return
    deposit = {
        "amount": amount,
        "start": int(time.time()),
        "days": days,
        "percent": percent,
    }
    user.setdefault("user_deposits", []).append(deposit)
    update_balance(message.from_user.id, get_balance(message.from_user.id) - amount)
    save_user_data()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📈 Вклады", callback_data="bank_deposits")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")],
        ]
    )
    await message.answer(
        f"✅ Депозит на {format_amount(amount)}$ открыт на {days} дн. под {percent}% в день.",
        reply_markup=kb
    )
    await state.clear()
    
    
@dp.callback_query(F.data == "bank_save_add")
async def bank_save_add_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите сумму для пополнения счёта (например, 1000, 1к, все):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")]]
        ),
    )
    await state.set_state(BankSaveState.waiting_for_bank_save_add)
    await callback.answer()


@dp.callback_query(F.data == "bank_save_withdraw")
async def bank_save_withdraw_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите сумму для снятия со счёта (например, 1000, 1к, все):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="bank_main")]]
        ),
    )
    await state.set_state(BankSaveState.waiting_for_bank_save_withdraw)
    await callback.answer()
    
    

@dp.message(StateFilter(BankSaveState.waiting_for_bank_save_add))
async def bank_save_add_amount(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    text = message.text.lower().replace(" ", "")
    if text in ["все", "всё", "all"]:
        amount = get_balance(message.from_user.id)
    else:
        text = text.replace("к", "000").replace("k", "000")
        try:
            amount = int(text)
        except ValueError:
            await message.answer("❌ Введите корректную сумму.")
            return
    if amount <= 0 or get_balance(message.from_user.id) < amount:
        await message.answer("❌ Недостаточно средств.")
        return
    user["user_bank"] = user.get("user_bank", 0) + amount
    update_balance(message.from_user.id, get_balance(message.from_user.id) - amount)
    save_user_data()
    await message.answer(
        f"✅ <code>{format_amount(amount)}</code>$ добавлено на счёт.\nВсего на счёте: <code>{format_amount(user.get('user_bank', 0))}$</code>.",
        parse_mode="HTML")
    await state.clear()


@dp.message(StateFilter(BankSaveState.waiting_for_bank_save_withdraw))
async def bank_save_withdraw_amount(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    text = message.text.lower().replace(" ", "")
    if text in ["все", "всё", "all"]:
        amount = user.get("user_bank", 0)
    else:
        text = text.replace("к", "000").replace("k", "000")
        try:
            amount = int(text)
        except ValueError:
            await message.answer("❌ Введите корректную сумму.")
            return
    if amount <= 0 or user.get("user_bank", 0) < amount:
        await message.answer("❌ Недостаточно средств на счёте.")
        return
    user["user_bank"] = user.get("user_bank", 0) - amount
    update_balance(message.from_user.id, get_balance(message.from_user.id) + amount)
    save_user_data()
    await message.answer(
        f"✅ <code>{format_amount(amount)}</code>$ снято со счёта.\nОсталось на счёте: <code>{format_amount(user.get('user_bank', 0))}$</code>.",
        parse_mode="HTML")
    await state.clear()




@dp.message(F.text.lower().startswith("банк"))
async def bank_command(message: Message):
    user = get_user(message.from_user.id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    parts = message.text.lower().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            f"❌ {clickable_name(message.from_user.id, name, clickable)}, укажите сумму. Пример:\n"
            "<code>банк 1000</code>\n"
            "<code>банк -500</code>\n"
            "<code>банк все</code>\n"
            "<code>банк -все</code>\n"
            "<code>банк 1/3</code>\n"
            "<code>банк -1/3</code>",
            parse_mode="HTML"
        )
        return

    text = parts[1].replace(" ", "")
    if text in ["все", "всё", "all"]:
        amount = get_balance(message.from_user.id)
    elif text in ["-все", "-всё", "-all"]:
        amount = -user.get("user_bank", 0)
    else:
        sign = -1 if text.startswith("-") else 1
        text_num = text.lstrip("-")
        try:
            amount_parsed = parse_k(text_num)
        except Exception:
            amount_parsed = None
        if amount_parsed is None:
            await message.answer(
                f"❌ {clickable_name(message.from_user.id, name, clickable)}, введите корректную сумму. Пример:\n"
                "<code>банк 1000</code>\n"
                "<code>банк -500</code>\n"
                "<code>банк все</code>\n"
                "<code>банк -все</code>\n"
                "<code>банк 1/3</code>\n"
                "<code>банк -1/3</code>",
                parse_mode="HTML"
            )
            return
        amount = amount_parsed * sign

    # Пополнение
    if amount > 0:
        if get_balance(message.from_user.id) < amount:
            await message.answer(
                f"❌ {clickable_name(message.from_user.id, name, clickable)}, недостаточно средств на балансе.",
                parse_mode="HTML"
            )
            return
        user["user_bank"] = user.get("user_bank", 0) + amount
        update_balance(message.from_user.id, get_balance(message.from_user.id) - amount)
        save_user_data()
        await message.answer(
            f"✅ {clickable_name(message.from_user.id, name, clickable)}, <code>{format_amount(amount)}$</code> добавлено на счёт.\n"
            f"Всего на счёте: <code>{format_amount(user['user_bank'])}$</code>.",
            parse_mode="HTML"
        )
    # Снятие
    elif amount < 0:
        amount = abs(amount)
        if user.get("user_bank", 0) < amount:
            await message.answer(
                f"❌ {clickable_name(message.from_user.id, name, clickable)}, недостаточно средств на счёте.",
                parse_mode="HTML"
            )
            return
        user["user_bank"] -= amount
        update_balance(message.from_user.id, get_balance(message.from_user.id) + amount)
        save_user_data()
        await message.answer(
            f"✅ {clickable_name(message.from_user.id, name, clickable)}, <code>{format_amount(amount)}$</code> снято со счёта.\n"
            f"Осталось на счёте: <code>{format_amount(user['user_bank'])}$</code>.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ {clickable_name(message.from_user.id, name, clickable)}, сумма должна быть больше 0.",
            parse_mode="HTML"
        )
        
        
        

@dp.message(F.text.lower().startswith("обнулить"))
async def reset_user_command(message: Message):
    user_id = message.from_user.id
    from admin_roles import has_permission
    if not has_permission(user_id, "reset_user"):
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("❌ Укажите ID пользователя для обнуления. Пример: `обнулить 123456789`")
        return
    target_user_id = int(parts[1])
    reset_user_data(target_user_id)
    recipient = get_user(target_user_id)
    name = recipient.get("name", "Без имени") if recipient else "Без имени"
    clickable = recipient.get("clickable_name", True) if recipient else True
    await message.answer(
        f"✅ Пользователь {clickable_name(target_user_id, name, clickable)} полностью удалён из базы.",
        parse_mode="HTML",
        reply_markup=safe_reply_kb(message, admin_kb),
    )







def _build_admin_info_kb(recipient_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🗑️ Обнулить", callback_data=f"reset_user:{recipient_id}"),
            InlineKeyboardButton(text="💵 Выдать",    callback_data=f"give_money:{recipient_id}"),
        ]]
    )


def _build_admin_info_text(recipient_id: int, recipient: dict) -> str:
    from farm import get_farm, get_btc_price, flush_farm, FARM_LEVELS, _fmt_btc
    import time as _t

    name              = recipient.get("name", "Без имени")
    clickable         = recipient.get("clickable_name", True)
    game_id           = recipient.get("game_id", "Не указан")
    balance           = recipient.get("balance", 0)
    bank_account      = recipient.get("user_bank", 0)
    telegram_username = recipient.get("telegram_username", "Не указан")
    referrals         = len(recipient.get("referrals", []))
    level             = recipient.get("level", 1)
    donate_coins      = recipient.get("donate_coins", 0)
    business          = recipient.get("business") or "Отсутствует"
    work_map = {
        "engineer": "Инженер 👨‍🔧", "chef": "Повар 👨‍🍳",
        "police": "Полицейский 👮", "programmer": "Программист 💻",
        "firefighter": "Пожарный 🔥", "doctor": "Доктор 🏥",
    }
    work_name = work_map.get(recipient.get("current_work"), "Не выбрана")

    # Вклады
    deposits = recipient.get("user_deposits", [])
    if deposits:
        deposits_text = "\n".join(
            [f"   • {format_amount(d['amount'])}$ / {d['days']}д / {d['percent']}%" for d in deposits]
        )
        deposits_sum = sum(d['amount'] for d in deposits)
    else:
        deposits_text = "   Нет активных вкладов"
        deposits_sum  = 0

    # Имущество
    assets   = recipient.get("assets", {})
    cars     = assets.get("cars",     [])
    houses   = assets.get("houses",   [])
    yachts   = assets.get("yachts",   [])
    planes   = assets.get("planes",   [])
    assets_lines = []
    if houses:  assets_lines.append(f"   🏠 Домов: {len(houses)}")
    if cars:    assets_lines.append(f"   🚗 Авто: {len(cars)}")
    if yachts:  assets_lines.append(f"   🛥 Яхт: {len(yachts)}")
    if planes:  assets_lines.append(f"   ✈️ Самолётов: {len(planes)}")
    assets_text = "\n".join(assets_lines) if assets_lines else "   Нет имущества"

    # Ферма
    farm      = get_farm(recipient_id)
    flush_farm(farm)
    btc_bal   = farm.get("btc_balance", 0.0)
    farm_lvl  = max(farm.get("farm_level", 0), 1)
    farm_info = FARM_LEVELS.get(farm_lvl, FARM_LEVELS[1])
    farm_status = "⚡ Активен" if farm.get("farm_level", 0) > 0 else "💤 Нет фермы"
    btc_price = get_btc_price()

    # Клан
    user_clan = get_user_clan(recipient_id)
    if user_clan:
        role_key   = user_clan.get("members", {}).get(str(recipient_id), "member")
        role_label = ROLE_NAMES.get(role_key, "👤 Участник")
        clan_text  = f"{user_clan.get('icon','🛡')} {user_clan['name']} — {role_label}"
    else:
        clan_text = "Отсутствует"

    return (
        f"┏━━━ 👤 ИНФО ИГРОКА ━━━┓\n\n"
        f"🧾 Имя: {clickable_name(recipient_id, name, clickable)}\n"
        f"🆔 Игровой ID: <code>{game_id}</code>\n"
        f"💳 Telegram ID: <code>{recipient_id}</code>\n"
        f"📱 Telegram: @{telegram_username}\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"💰 Баланс: <b>{format_amount(balance)}$</b>\n"
        f"🏦 Банк: <b>{format_amount(bank_account)}$</b>\n"
        f"₿  BTC: <b>{_fmt_btc(btc_bal)} BTC</b> (~{format_amount(int(btc_bal * btc_price))}$)\n"
        f"💎 Донат: <b>{donate_coins} DC</b>\n\n"
        f"📈 Вклады ({format_amount(deposits_sum)}$):\n{deposits_text}\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"📊 Уровень: {level}\n"
        f"💼 Работа: {work_name}\n"
        f"🏢 Бизнес: {business}\n\n"
        f"🏠 Имущество:\n{assets_text}\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"🖥 Ферма: {farm_info['name']} (ур. {farm_lvl})\n"
        f"   └ {farm_info['btc_per_hour']} BTC/ч  |  {farm_status}\n\n"
        f"🛡 Клан: {clan_text}\n\n"
        f"👥 Рефералов: {referrals}\n\n"
        f"┗━━━━━━━━━━━━━━━━┛"
    )


def load_reports():
    if os.path.exists(REPORTS_FILE):
        try:
            with open(REPORTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_reports(reports):
    try:
        with open(REPORTS_FILE, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_next_report_id():
    reports = load_reports()
    if reports:
        return str(int(max(reports.keys(), key=int)) + 1)
    return "1"

@dp.message(F.text.lower().startswith(("репорт", "поддержка")))
async def report_command(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите текст сообщения для поддержки. Пример: <code>репорт не работает банк</code>",
            parse_mode="HTML"
        )
        return
    report_text = parts[1].strip()
    report_id = get_next_report_id()
    reports = load_reports()
    reports[report_id] = {
        "user_id": user_id,
        "user_name": name,
        "text": report_text,
        "status": "open",
        "chat_id": chat_id,
    }
    save_reports(reports)

    # Новый стиль подтверждения
    confirm_text = (
        f"{name}, ваше сообщение отправлено (№{report_id}) ✅\n"
        f"▶️ Ответ вы получите в данном диалоге"
    )
    await message.answer(confirm_text, parse_mode="HTML")

    # Сообщение админу (всем владельцам)
    for owner_id in owners:
        owner_user = get_user(owner_id)
        if not owner_user:
            continue
        try:
            msg = await bot.send_message(
                owner_id,
                f"Репорт #{report_id} от пользователя {clickable_name(user_id, name, clickable)}:\n{report_text}",
                parse_mode="HTML"
            )
            REPORTS_STATE[report_id] = {"user_id": user_id, "admin_msg_id": msg.message_id}
        except Exception:
            pass
        

# Ответ на репорт (админ отвечает на сообщение-репорт)
@dp.message(lambda m: (
    m.reply_to_message and
    m.from_user.id in owners and
    m.reply_to_message.text and
    "Репорт #" in m.reply_to_message.text
))
async def reply_to_report(message: Message):
    reply = message.reply_to_message
    text = message.text.strip()
    # Поиск report_id по тексту сообщения-репорта
    report_id = None
    for line in (reply.text or "").splitlines():
        if line.startswith("Репорт #"):
            report_id = line.split("#")[1].split()[0]
            break
    if not report_id:
        return
    reports = load_reports()
    report = reports.get(report_id)
    if not report:
        await message.answer("Репорт не найден.")
        return
    user_id = report["user_id"]
    chat_id = report.get("chat_id", user_id)
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    dt = datetime.now().strftime("%d.%m.%Y %H:%M")
    answer_text = (
        f"🔔 {clickable_name(user_id, name, clickable)}, на твоё сообщение №{report_id} поступил ответ:\n"
        f"💬 {text}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Помогло", callback_data=f"report_helpful:{report_id}"),
                InlineKeyboardButton(text="👎 Не помогло", callback_data=f"report_not_helpful:{report_id}")
            ]
        ]
    )
    errors = []
    # Отправляем в личку
    try:
        await bot.send_message(user_id, answer_text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        errors.append(f"Не удалось отправить в ЛС: {e}")
    # Если репорт был из группы — отправляем и туда
    if chat_id != user_id:
        try:
            await bot.send_message(chat_id, answer_text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            errors.append(f"Не удалось отправить в группу: {e}")
    report["status"] = "answered"
    save_reports(reports)
    if errors:
        await message.answer(f"Ответ на репорт #{report_id} отправлен, но есть ошибки:\n" + "\n".join(errors))
    else:
        await message.answer(f"Ответ на репорт #{report_id} отправлен пользователю.")
        

@dp.callback_query(F.data.startswith("report_helpful:"))
async def report_helpful_callback(callback: CallbackQuery):
    report_id = callback.data.split(":")[1]
    reports = load_reports()
    report = reports.get(report_id)
    if report:
        report["status"] = "closed_helpful"
        save_reports(reports)
    await callback.message.edit_text(f"👍 Спасибо за ваш отклик. Репорт #{report_id} закрыт как решённый.")

@dp.callback_query(F.data.startswith("report_not_helpful:"))
async def report_not_helpful_callback(callback: CallbackQuery):
    report_id = callback.data.split(":")[1]
    reports = load_reports()
    report = reports.get(report_id)
    if report:
        report["status"] = "closed_not_helpful"
        save_reports(reports)
    await callback.message.edit_text(
        f"👍 Спасибо за ваш отклик. Репорт №{report_id} отмечен как нерешённый. Если вопрос не решён, напишите новый репорт с уточнением."
    )


@dp.message(F.text.lower().startswith(("/alert", "alert", "алерт")))
async def alert_command(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("❌ Укажите текст для алерта. Пример: <code>алерт Привет!</code>", parse_mode="HTML")
        return
    alert_text = parts[1].strip()
    # Ограничение 50 символов (чтобы с запасом влезло в 64 байта)
    if len(alert_text.encode("utf-8")) > 50:
        await message.answer("❌ Текст для алерта слишком длинный. Максимум 50 символов (или меньше, если используются эмодзи/русские буквы).", parse_mode="HTML")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Показать алерт", callback_data=f"show_alert:{alert_text}")]
        ]
    )
    await message.answer("ㅤ", reply_markup=kb)

@dp.callback_query(F.data.startswith("show_alert:"))
async def show_alert_callback(callback: CallbackQuery):
    alert_text = callback.data[len("show_alert:") :]
    await callback.answer(alert_text, show_alert=True)



async def on_polling_error(update, exception):
    print(f"[ОШИБКА] {type(exception).__name__}: {exception}")
    return True

if __name__ == "__main__":
    import asyncio
    import traceback
    from aiohttp import web
    import website

    async def main():
        load_user_data()
        round_all_balances()
        fix_user_data()
        fix_duplicate_ids()
        grant_founder_stats()
        scheduler = AsyncIOScheduler()
        scheduler.add_job(process_all_deposits, "interval", minutes=10)
        scheduler.add_job(auto_mine_all_complexes, "interval", minutes=1)
        scheduler.add_job(auto_mine_ore, "interval", hours=1)
        scheduler.add_job(update_market_prices, "interval", hours=1)
        scheduler.add_job(check_season_end, "interval", minutes=10)
        scheduler.add_job(process_raffles, "interval", seconds=30)
        scheduler.add_job(notify_mining_done, "interval", minutes=2)
        scheduler.add_job(auto_collect_all_businesses, "interval", hours=1)
        scheduler.add_job(vip_clan_hourly_rating, "interval", hours=1)
        scheduler.add_job(reset_all_daily_transfer_limits, "cron", hour=0, minute=0)
        scheduler.add_job(check_house_rentals, "interval", minutes=2, args=[bot])
        scheduler.add_job(check_car_rentals, "interval", minutes=2, args=[bot])
        scheduler.start()

        try:
            from aiogram.types import (
                BotCommandScopeAllGroupChats,
                BotCommandScopeAllPrivateChats,
                BotCommandScopeDefault,
                MenuButtonDefault,
            )
            await bot.delete_my_commands()
            await bot.delete_my_commands(scope=BotCommandScopeDefault())
            await bot.delete_my_commands(scope=BotCommandScopeAllGroupChats())
            await bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())
            await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        except Exception:
            pass

        runner = web.AppRunner(website.make_app())
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", 5000).start()
        print("Веб-сервер запущен на порту 5000")

        while True:
            try:
                print("[БОТ] Запуск polling...")
                await dp.start_polling(bot, allowed_updates=["message", "callback_query", "pre_checkout_query"])
            except Exception as e:
                print(f"[БОТ] Ошибка polling: {type(e).__name__}: {e}")
                traceback.print_exc()
                print("[БОТ] Перезапуск через 5 секунд...")
                await asyncio.sleep(5)

    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            print(f"[БОТ] Критическая ошибка: {type(e).__name__}: {e}")
            traceback.print_exc()
            print("[БОТ] Перезапуск через 5 секунд...")
            import time as _t
            _t.sleep(5)