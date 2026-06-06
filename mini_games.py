"""
Мини-игры: баскет 🏀 (3×), пенка ⚽ (2.5×), дартс 🎯 (5×)
"""
import asyncio
from aiogram import Router, F
from aiogram.types import Message
from config import bot
from utils import (
    get_balance, update_balance, format_amount,
    get_user, round_amount, clickable_name, save_user_data,
)

router = Router()
MIN_BET = 10

GAMES = {
    "баскет":  {"emoji": "🏀", "dice_emoji": "🏀", "multiplier": 3.0,  "win_values": {4, 5}, "label": "Баскетбол"},
    "пенка":   {"emoji": "⚽", "dice_emoji": "⚽", "multiplier": 2.5,  "win_values": {4, 5}, "label": "Пенальти"},
    "дартс":   {"emoji": "🎯", "dice_emoji": "🎯", "multiplier": 5.0,  "win_values": {6},    "label": "Дартс"},
}

GAME_ALIASES = {
    "баскет":  "баскет",
    "баскетбол": "баскет",
    "basket":  "баскет",
    "пенка":   "пенка",
    "пенальти":"пенка",
    "пена":    "пенка",
    "дартс":   "дартс",
    "дарт":    "дартс",
    "darts":   "дартс",
}


def _win_text(g: dict, won: bool, amount: int, win_amount: int, new_balance: int, dice_val: int) -> str:
    label = g["label"]
    emoji = g["emoji"]
    mult  = g["multiplier"]
    win_vals = g["win_values"]
    # Показываем результат броска
    if g["dice_emoji"] == "🏀":
        outcome = "🔥 Мяч в кольце!" if won else "💨 Промах!"
    elif g["dice_emoji"] == "⚽":
        outcome = "⚽ Гол!" if won else "🧤 Вратарь поймал!"
    else:  # дартс
        outcome = "🎯 Яблочко!" if won else f"❌ Промах (выпало {dice_val})"
    if won:
        return (
            f"{emoji} <b>{label}</b>\n\n"
            f"{outcome}\n"
            f"🏆 Победа! Множитель ×{mult:.1f}\n"
            f"💰 Выигрыш: <b>+{format_amount(win_amount)}$</b>\n"
            f"💼 Баланс: <b>{format_amount(new_balance)}$</b>"
        )
    else:
        return (
            f"{emoji} <b>{label}</b>\n\n"
            f"{outcome}\n"
            f"😢 Проигрыш\n"
            f"💸 Потеряно: <b>{format_amount(amount)}$</b>\n"
            f"💼 Баланс: <b>{format_amount(new_balance)}$</b>"
        )


async def play_mini_game(message: Message, game_key: str, amount: int):
    user_id = message.from_user.id
    g = GAMES[game_key]
    balance = get_balance(user_id)

    if amount > balance:
        await message.answer(
            f"❌ Недостаточно средств.\n💰 Баланс: <b>{format_amount(balance)}$</b>",
            parse_mode="HTML",
        )
        return
    if amount < MIN_BET:
        await message.answer(f"❌ Минимальная ставка: <b>{MIN_BET}$</b>", parse_mode="HTML")
        return

    update_balance(user_id, balance - amount)
    save_user_data()

    # Отправляем анимацию кубика
    dice_msg = await message.answer_dice(emoji=g["dice_emoji"])
    dice_val = dice_msg.dice.value

    # Ждём пока анимация проиграется
    await asyncio.sleep(3)

    won = dice_val in g["win_values"]
    new_balance = get_balance(user_id)
    win_amount = 0
    if won:
        win_amount = round_amount(amount * g["multiplier"])
        new_balance += win_amount
        update_balance(user_id, new_balance)
        save_user_data()

    text = _win_text(g, won, amount, win_amount, new_balance, dice_val)
    await message.answer(text, parse_mode="HTML")


@router.message(F.text.lower().startswith(("баскет ", "баскет", "пенка ", "пенка", "дартс ", "дартс")))
async def mini_game_handler(message: Message):
    raw = message.text.strip().lower()
    parts = raw.split(maxsplit=1)
    game_key = GAME_ALIASES.get(parts[0])
    if not game_key:
        return

    g = GAMES[game_key]
    user_id = message.from_user.id
    balance = get_balance(user_id)

    if len(parts) < 2 or parts[1].strip() == "":
        await message.answer(
            f"{g['emoji']} <b>{g['label']}</b>\n\n"
            f"Укажи ставку: <code>{parts[0]} 1000</code> или <code>{parts[0]} вб</code>\n"
            f"Множитель при победе: <b>×{g['multiplier']:.1f}</b>",
            parse_mode="HTML",
        )
        return

    raw_amount = parts[1].strip()
    from roulette import parse_amount
    amount = parse_amount(raw_amount, balance)
    if amount is None or amount <= 0:
        await message.answer("❌ Неверная сумма.", parse_mode="HTML")
        return

    await play_mini_game(message, game_key, amount)
