import random
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from utils import (
    get_balance, update_balance, get_user, save_user_data,
    format_amount, clickable_name, round_amount, parse_k,
)

router = Router()

MIN_BET = 10

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}
EVEN_NUMBERS = {n for n in range(1, 37) if n % 2 == 0}
ODD_NUMBERS  = {n for n in range(1, 37) if n % 2 != 0}

COLOR_ALIASES = {
    # красный
    "к":        "красный",
    "кр":       "красный",
    "красный":  "красный",
    "красного": "красный",
    "красное":  "красный",
    # чёрный
    "ч":        "чёрный",
    "чёрный":   "чёрный",
    "черный":   "чёрный",
    "чёрного":  "чёрный",
    "черного":  "чёрный",
    # зелёный / ноль
    "з":        "зелёный",
    "зел":      "зелёный",
    "зелёный":  "зелёный",
    "зеленый":  "зелёный",
    "зелёного": "зелёный",
    "зеленого": "зелёный",
    "0":        "зелёный",
    "ноль":     "зелёный",
    "нуль":     "зелёный",
    # чётное
    "чет":      "чёт",
    "чёт":      "чёт",
    "четное":   "чёт",
    "чётное":   "чёт",
    "even":     "чёт",
    # нечётное
    "нечет":    "нечет",
    "нечёт":    "нечет",
    "нечетное": "нечет",
    "нечётное": "нечет",
    "odd":      "нечет",
    "нч":       "нечет",
    # дюжины
    "д1": "д1",
    "д2": "д2",
    "д3": "д3",
}

MULTIPLIERS = {
    "красный": 2,
    "чёрный":  2,
    "зелёный": 35,
    "чёт":     2,
    "нечет":   2,
    "д1":      3,
    "д2":      3,
    "д3":      3,
}

COLOR_EMOJI = {
    "красный": "🔴",
    "чёрный":  "⚫",
    "зелёный": "🟢",
}

BET_DISPLAY = {
    "красный": "🔴 Красный",
    "чёрный":  "⚫ Чёрный",
    "зелёный": "🟢 Зелёный",
    "чёт":     "2️⃣ Чётное",
    "нечет":   "1️⃣ Нечётное",
    "д1":      "📊 Дюжина 1–12",
    "д2":      "📊 Дюжина 13–24",
    "д3":      "📊 Дюжина 25–36",
}


def get_number_color(n: int) -> str:
    if n == 0:
        return "зелёный"
    return "красный" if n in RED_NUMBERS else "чёрный"


def get_number_dozen(n: int) -> str | None:
    if 1 <= n <= 12:
        return "д1"
    elif 13 <= n <= 24:
        return "д2"
    elif 25 <= n <= 36:
        return "д3"
    return None


def get_number_emoji(n: int) -> str:
    return COLOR_EMOJI.get(get_number_color(n), "⬜")


def parse_amount(text: str, balance: int | float = 0) -> int | None:
    text = text.strip().lower().replace("ё", "е").replace(",", ".")
    if text in ("вб", "все", "всё", "all", "ва"):
        return round_amount(balance)
    if text.endswith("м"):
        inner = text[:-1]
        try:
            num = float(inner) if inner else 1.0
            return round_amount(num * 1_000_000)
        except ValueError:
            return None
    return parse_k(text, balance)


def check_win(bet: str, result_number: int) -> bool:
    if bet in ("д1", "д2", "д3"):
        return bet == get_number_dozen(result_number)
    if bet == "чёт":
        return result_number in EVEN_NUMBERS
    if bet == "нечет":
        return result_number in ODD_NUMBERS
    return bet == get_number_color(result_number)


def build_repeat_kb(bet: str, amount: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔄 Повторить ставку",
            callback_data=f"rl_repeat:{bet}:{amount}",
        )
    ]])


def build_result_text(result_number: int, won: bool, bet: str,
                      amount: int, new_balance: int) -> str:
    result_color = get_number_color(result_number)
    num_emoji = COLOR_EMOJI.get(result_color, "⬜")
    multiplier = MULTIPLIERS[bet]
    bet_label = BET_DISPLAY.get(bet, bet)

    # Дополнительная пометка чётности
    if result_number == 0:
        parity = ""
    elif result_number in EVEN_NUMBERS:
        parity = " (чётное)"
    else:
        parity = " (нечётное)"

    if won:
        win_amount = round_amount(amount * multiplier)
        return (
            f"{num_emoji} Выпало: <b>{result_number}</b>{parity}\n"
            f"🎉 Вы выиграли <b>{format_amount(win_amount)}$</b> (x{multiplier})!\n"
            f"💰 Баланс: <b>{format_amount(new_balance)}$</b>"
        )
    else:
        return (
            f"{num_emoji} Выпало: <b>{result_number}</b>{parity}\n"
            f"😢 Вы проиграли <b>{format_amount(amount)}$</b>\n"
            f"💰 Баланс: <b>{format_amount(new_balance)}$</b>"
        )


async def play_roulette(send_target, bet: str, amount: int, user_id: int, chat_id: int = None):
    result_number = random.randint(0, 36)
    won = check_win(bet, result_number)
    multiplier = MULTIPLIERS[bet]
    new_balance = get_balance(user_id)

    if won:
        win_amount = round_amount(amount * multiplier)
        new_balance += win_amount
        update_balance(user_id, new_balance)
        if chat_id and chat_id != user_id:
            from chat_system import update_chat_stats
            update_chat_stats(chat_id, user_id, spent=amount, won=win_amount)
    else:
        if chat_id and chat_id != user_id:
            from chat_system import add_to_treasury, update_chat_stats
            add_to_treasury(chat_id, amount)
            update_chat_stats(chat_id, user_id, spent=amount, won=0)
            from clans import _find_clan_by_chat, save_clans
            linked_clan = _find_clan_by_chat(chat_id)
            if linked_clan:
                cut = max(1, int(amount * 0.01))
                linked_clan["treasury"] = linked_clan.get("treasury", 0) + cut
                save_clans()

    result_text = build_result_text(result_number, won, bet, amount, new_balance)
    repeat_kb = build_repeat_kb(bet, amount)
    await send_target.answer(result_text, parse_mode="HTML", reply_markup=repeat_kb)


@router.message(F.text.lower().startswith("р "))
async def roulette_bet(message: Message):
    user_id = message.from_user.id
    balance = get_balance(user_id)

    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "❌ Неверный формат.\n"
            "Пример: <code>р к 1000</code>, <code>р чет 10к</code>, <code>р з вб</code>",
            parse_mode="HTML",
        )
        return

    raw_bet = parts[1].lower().replace("ё", "е")
    raw_amount = parts[2].lower()

    bet = COLOR_ALIASES.get(raw_bet)
    if not bet:
        await message.answer(
            "❌ Неверная ставка. Доступные:\n"
            "• <code>к</code> / <code>красный</code> — 🔴 Красный (x2)\n"
            "• <code>ч</code> / <code>чёрный</code> — ⚫ Чёрный (x2)\n"
            "• <code>з</code> / <code>зелёный</code> — 🟢 Зелёный (x35)\n"
            "• <code>чет</code> / <code>чётное</code> — 2️⃣ Чётное (x2)\n"
            "• <code>нечет</code> / <code>нечётное</code> — 1️⃣ Нечётное (x2)\n"
            "• <code>д1</code> / <code>д2</code> / <code>д3</code> — 📊 Дюжина (x3)",
            parse_mode="HTML",
        )
        return

    amount = parse_amount(raw_amount, balance)
    if amount is None or amount <= 0:
        await message.answer(
            "❌ Неверная сумма. Примеры: <code>1000</code>, <code>10к</code>, <code>1м</code>, <code>вб</code>",
            parse_mode="HTML",
        )
        return

    if amount < MIN_BET:
        await message.answer(f"❌ Минимальная ставка: <b>{MIN_BET}$</b>", parse_mode="HTML")
        return

    if amount > balance:
        await message.answer(
            f"❌ Недостаточно средств.\n💰 Ваш баланс: <b>{format_amount(balance)}$</b>",
            parse_mode="HTML",
        )
        return

    update_balance(user_id, balance - amount)
    chat_id = message.chat.id if message.chat else None
    await play_roulette(message, bet, amount, user_id, chat_id=chat_id)


@router.callback_query(F.data.startswith("rl_repeat:"))
async def roulette_repeat(callback: CallbackQuery):
    user_id = callback.from_user.id
    balance = get_balance(user_id)

    try:
        _, bet, amount_str = callback.data.split(":", 2)
        amount = int(amount_str)
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных ставки.", show_alert=True)
        return

    if amount < MIN_BET:
        await callback.answer(f"Минимальная ставка: {MIN_BET}$", show_alert=True)
        return
    if amount > balance:
        await callback.answer(
            f"Недостаточно средств. Баланс: {format_amount(balance)}$",
            show_alert=True,
        )
        return

    update_balance(user_id, balance - amount)
    await callback.answer()
    chat_id = callback.message.chat.id if callback.message and callback.message.chat else None
    await play_roulette(callback.message, bet, amount, user_id, chat_id=chat_id)
