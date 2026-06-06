import random
from aiogram import Router, F
import math
import json
import os
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from utils import get_balance, update_balance, parse_k, round_amount, get_user, save_user_data, safe_reply_kb
from keyboards import menu_kb
from aiogram.filters import Command
from utils import format_amount, clickable_name
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import bot
from aiogram.fsm.state import State, StatesGroup
COIN_GAMES_FILE = os.path.join(os.path.dirname(__file__), "coin_games.json")

class RouletteState(StatesGroup):
    waiting_for_bet_type = State()
    waiting_for_bet_amount = State()

class CrashState(StatesGroup):
    waiting_for_coef = State()
    waiting_for_amount = State()


class CoinState(StatesGroup):
    waiting_for_accept = State()


def load_coin_games():
    if os.path.exists(COIN_GAMES_FILE):
        try:
            with open(COIN_GAMES_FILE, "r", encoding="utf-8") as f:
                return {int(k): v for k, v in json.load(f).items()}
        except Exception:
            return {}
    return {}

def save_coin_games():
    try:
        with open(COIN_GAMES_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in coin_games.items()}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass



coin_games = load_coin_games()

router = Router()








# Данные рулетки
roulette_numbers = {
    "ряд3": [3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36],
    "ряд2": [2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35],
    "ряд1": [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34],
    "1-12": list(range(1, 13)),
    "13-24": list(range(13, 25)),
    "25-36": list(range(25, 37)),
    "малые": list(range(1, 19)),
    "большие": list(range(19, 37)),
    "красное": [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36],
    "черное": [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35],
    "зеленое": [0],
    "чет": [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36],
    "нечет": [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35],
}

bet_multipliers = {
    "число": 36,
    "зеленое": 36,
    "ряд1": 3,
    "ряд2": 3,
    "ряд3": 3,
    "1-12": 3,
    "13-24": 3,
    "25-36": 3,
    "красное": 2,
    "черное": 2,
    "чет": 2,
    "нечет": 2,
    "малые": 2,
    "большие": 2,
}

# Словарь для преобразования сокращений
bet_aliases = {
    "к": "красное",
    "ч": "черное",
    "з": "зеленое",
    "зеро": "зеленое",
}

@router.message(F.text.lower().startswith("р "))
async def roulette_bet_short(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    balance = get_balance(user_id)

    try:
        parts = message.text.lower().split()
        if len(parts) != 3:
            raise ValueError("Неправильный формат. Пример: р к 100")

        if balance <= 0:
            await message.answer("❌ Недостаточно средств на балансе")
            return

        bet_type = parts[1]
        amount_str = parts[2].replace("ё", "е")

        # Преобразуем сокращения в полные названия
        bet_type = bet_aliases.get(bet_type, bet_type)

        if amount_str == "все":
            amount = balance
        else:
            amount = parse_k(amount_str, balance)

        if amount is None or amount <= 0:
            await message.answer("❌ Неверная сумма. Пример: 100, 1к, 2.5кк или 'все'")
            return

        if amount > balance:
            await message.answer("Недостаточно средств на балансе")
            return

        # Проверка на конкретное число
        if bet_type.isdigit():
            number = int(bet_type)
            if 0 <= number <= 36:
                bet_type = "число"
                selected_number = number
            else:
                await message.answer("Число должно быть от 0 до 36")
                return
        elif bet_type not in roulette_numbers:
            await message.answer(
                "Неверный тип ставки. Напишите помощь рулетка для списка ставок"
            )
            return

        # Принимаем ставку
        balance -= amount
        result_number = random.randint(0, 36)

        # Определяем свойства выпавшего числа
        result_props = {
            "color": "зеленое"
            if result_number == 0
            else "красное"
            if result_number in roulette_numbers["красное"]
            else "черное",
            "parity": "чет" if result_number in roulette_numbers["чет"] else "нечет",
            "range": "1-12"
            if result_number in roulette_numbers["1-12"]
            else "13-24"
            if result_number in roulette_numbers["13-24"]
            else "25-36"
            if result_number in roulette_numbers["25-36"]
            else None,
            "size": "малые"
            if result_number in roulette_numbers["малые"]
            else "большие"
            if result_number in roulette_numbers["большие"]
            else None,
        }

        # Проверяем выигрыш
        win = False
        if bet_type == "число":
            win = result_number == selected_number
        else:
            win = result_number in roulette_numbers[bet_type]

        if win:
            multiplier = bet_multipliers[bet_type]
            win_amount = round_amount(amount * multiplier)
            balance += win_amount
            update_balance(user_id, balance)
            result_message = (
                f"{name}\n"
                f"🎰 Выпало: {result_number} ({result_props['color']})\n"
                f"🎉 Вы выиграли {win_amount}$ (x{multiplier})!\n"
                f"💰 Баланс: {balance}$"
            )
        else:
            update_balance(user_id, balance)
            result_message = (
                f"{name}\n"
                f"🎰 Выпало: {result_number} ({result_props['color']})\n"
                f"😢 Вы проиграли {amount}$\n"
                f"💰 Баланс: {balance}$"
            )

        # Сохраняем последнюю ставку
        user = get_user(user_id)
        user["last_bet"] = {"amount": amount, "type": bet_type}
        save_user_data()

        repeat_bet_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Повторить ставку",
                        callback_data=f"repeat_bet:{user_id}:{amount}:{bet_type}",
                    )
                ]
            ]
        )

        await message.answer(result_message, reply_markup=repeat_bet_kb)

    except ValueError as e:
        await message.answer(str(e), reply_markup=safe_reply_kb(message, menu_kb))
    except Exception:
        await message.answer("Ошибка обработки ставки", reply_markup=safe_reply_kb(message, menu_kb))


# Обработчик команды "рулетка"
@router.message(F.text.lower().startswith("рулетка"))
async def roulette_bet(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    balance = get_balance(user_id)

    try:
        parts = message.text.lower().split()
        if len(parts) != 3:
            raise ValueError("Неправильный формат. Пример: рулетка красное 100")

        if balance <= 0:
            await message.answer("❌ Недостаточно средств на балансе")
            return

        bet_type = parts[1]
        amount_str = parts[2].replace("ё", "е")

        # Преобразуем сокращения в полные названия
        bet_type = bet_aliases.get(bet_type, bet_type)

        if amount_str == "все":
            amount = balance
        else:
            amount = parse_k(amount_str, balance)

        if amount is None or amount <= 0:
            await message.answer("❌ Неверная сумма. Пример: 100, 1к, 2.5кк или 'все'")
            return

        if amount > balance:
            await message.answer("Недостаточно средств на балансе")
            return

        # Проверка на конкретное число
        if bet_type.isdigit():
            number = int(bet_type)
            if 0 <= number <= 36:
                bet_type = "число"
                selected_number = number
            else:
                await message.answer("Число должно быть от 0 до 36")
                return
        elif bet_type not in roulette_numbers:
            await message.answer(
                "Неверный тип ставки. Напишите помощь рулетка для списка ставок"
            )
            return

        # Принимаем ставку
        balance -= amount
        result_number = random.randint(0, 36)

        # Определяем свойства выпавшего числа
        result_props = {
            "color": "зеленое"
            if result_number == 0
            else "красное"
            if result_number in roulette_numbers["красное"]
            else "черное",
            "parity": "чет" if result_number in roulette_numbers["чет"] else "нечет",
            "range": "1-12"
            if result_number in roulette_numbers["1-12"]
            else "13-24"
            if result_number in roulette_numbers["13-24"]
            else "25-36"
            if result_number in roulette_numbers["25-36"]
            else None,
            "size": "малые"
            if result_number in roulette_numbers["малые"]
            else "большие"
            if result_number in roulette_numbers["большие"]
            else None,
        }

        # Проверяем выигрыш
        win = False
        if bet_type == "число":
            win = result_number == selected_number
        else:
            win = result_number in roulette_numbers[bet_type]

        if win:
            multiplier = bet_multipliers[bet_type]
            win_amount = round_amount(amount * multiplier)
            balance += win_amount
            update_balance(user_id, balance)
            result_message = (
                f"{name}\n"
                f"🎰 Выпало: {result_number} ({result_props['color']})\n"
                f"🎉 Вы выиграли {win_amount}$ (x{multiplier})!\n"
                f"💰 Баланс: {balance}$"
            )
        else:
            update_balance(user_id, balance)
            result_message = (
                f"{name}\n"
                f"🎰 Выпало: {result_number} ({result_props['color']})\n"
                f"😢 Вы проиграли {amount}$\n"
                f"💰 Баланс: {balance}$"
            )

        # Сохраняем последнюю ставку
        user = get_user(user_id)
        user["last_bet"] = {"amount": amount, "type": bet_type}
        save_user_data()


        repeat_bet_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Повторить ставку",
                        callback_data=f"repeat_bet:{user_id}:{amount}:{bet_type}",
                    )
                ]
            ]
        )

        await message.answer(result_message, reply_markup=repeat_bet_kb)

    except ValueError as e:
        await message.answer(str(e), reply_markup=safe_reply_kb(message, menu_kb))
    except Exception:
        await message.answer("Ошибка обработки ставки", reply_markup=safe_reply_kb(message, menu_kb))


@router.callback_query(F.data.startswith("repeat_bet"))
async def handle_repeat_bet(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data.split(":")
    owner_id = int(data[1]) if len(data) > 3 else user_id
    if owner_id != user_id:
        await callback.answer("❌ Это чужая кнопка!", show_alert=True)
        return
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    amount_str = data[2] if len(data) > 3 else data[1]
    bet_type = data[3] if len(data) > 3 else data[2]

    balance = get_balance(user_id)
    amount = parse_k(str(amount_str), balance)
    if amount is None or amount <= 0:
        await callback.message.answer("❌ Неверная сумма для повторения ставки.")
        await callback.answer()
        return
    if balance < amount:
        await callback.message.answer("❌ У вас недостаточно средств для повторения ставки.")
        await callback.answer()
        return

    # Списываем ставку
    update_balance(user_id, balance - amount)

    # Генерируем результат рулетки
    result_number = random.randint(0, 36)
    result_color = (
        "зеленое"
        if result_number == 0
        else "красное"
        if result_number in roulette_numbers["красное"]
        else "черное"
    )

    # Проверяем выигрыш
    win_multiplier = bet_multipliers.get(bet_type, 0)
    win_amount = amount * win_multiplier if result_number in roulette_numbers.get(bet_type, []) else 0

    # Обновляем баланс, если пользователь выиграл
    if win_amount > 0:
        update_balance(user_id, get_balance(user_id) + win_amount)

    # Формируем сообщение о результате
    if win_amount > 0:
        result_message = (
            f"{name}\n"
            f"🎰 Выпало: {result_number} ({result_color})\n"
            f"🎉 Вы выиграли {win_amount}$!\n"
            f"💰 Баланс: {get_balance(user_id)}$"
        )
    else:
        result_message = (
            f"{name}\n"
            f"🎰 Выпало: {result_number} ({result_color})\n"
            f"😢 Вы проиграли {amount}$\n"
            f"💰 Баланс: {get_balance(user_id)}$"
        )

    repeat_bet_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Повторить ставку",
                    callback_data=f"repeat_bet:{user_id}:{amount}:{bet_type}",
                )
            ]
        ]
    )

    await callback.message.answer(result_message, reply_markup=repeat_bet_kb)
    await callback.answer()
    
    
    
    
@router.callback_query(F.data == "roulette_start")
async def roulette_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Выберите тип ставки (например, красное, черное, число и т.д.):\n\n Подробнее: `Помощь рулетка`",
        reply_markup=None,
        parse_mode="markdown",
    )
    await state.set_state(RouletteState.waiting_for_bet_type)
    await callback.answer()

@router.message(RouletteState.waiting_for_bet_type)
async def roulette_bet_type(message: Message, state: FSMContext):
    bet_type = message.text.lower().replace("ё", "е")
    await state.update_data(bet_type=bet_type)
    await message.answer("Введите сумму ставки:")
    await state.set_state(RouletteState.waiting_for_bet_amount)

    
@router.callback_query(F.data == "crash_start")
async def crash_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите коэффициент (например, 2.5):")
    await state.set_state(CrashState.waiting_for_coef)
    await callback.answer()

@router.message(CrashState.waiting_for_coef)
async def crash_coef_input(message: Message, state: FSMContext):
    try:
        coef = float(message.text.replace(",", "."))
        if coef < 1.01 or coef > 1_000_000:
            await message.answer("Коэффициент должен быть от 1.01 до 1.000.000")
            return
        await state.update_data(coef=coef)
        await message.answer("Введите сумму ставки:")
        await state.set_state(CrashState.waiting_for_amount)
    except ValueError:
        await message.answer("Некорректный коэффициент. Пример: 2.5")


    
    
def generate_crash_coef():
    """
    4% игр — коэффициент 0
    70% игр — до 2
    95% — до 5
    99% — до 100
    Остальное — до 1 000 000
    """
    min_coef = 1.01
    max_coef = 1_000_000
    p = random.random()
    if p < 0.04:
        return 0
    elif p < 0.74:
        log_min = math.log(min_coef)
        log_max = math.log(2)
    elif p < 0.95:
        log_min = math.log(2)
        log_max = math.log(5)
    elif p < 0.99:
        log_min = math.log(5)
        log_max = math.log(100)
    else:
        log_min = math.log(100)
        log_max = math.log(max_coef)
    log_value = random.uniform(log_min, log_max)
    coef = math.exp(log_value)
    return round(coef, 2)



@router.message(F.text.lower().startswith("краш"))
async def crash_game(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    balance = get_balance(user_id)

    try:
        parts = message.text.lower().replace(",", ".").split()
        if len(parts) != 3:
            await message.answer("Пример: краш 2.5 100")
            return

        if balance < 10:
            await message.answer("❌ Минимальная ставка — 10$")
            return

        # Коэффициент
        try:
            coef = float(parts[1])
            if coef < 1.01 or coef > 1_000_000:
                await message.answer("Коэффициент должен быть от 1.01 до 1.000.000")
                return
        except ValueError:
            await message.answer("Некорректный коэффициент. Пример: 2.5")
            return

        # Сумма
        amount_str = parts[2].replace("ё", "е")
        if amount_str == "все":
            amount = balance
        else:
            amount = parse_k(amount_str, balance)

        if amount is None or amount < 10:
            await message.answer("❌ Минимальная ставка — 10$")
            return

        if amount > balance:
            await message.answer("Недостаточно средств на балансе")
            return

        crash_coef = generate_crash_coef()

        win = coef <= crash_coef
        update_balance(user_id, balance - amount)

        if win:
            win_amount = round_amount(amount * coef)
            update_balance(user_id, get_balance(user_id) + win_amount)
            result_message = (
                f"{name}\n"
                f"Краш остановился на: x{crash_coef}\n"
                f"Ваш коэффициент: x{coef}\n"
                f"🎉 Победа! Ваш приз: +{format_amount(win_amount - amount)}$\n"
                f"💰 Баланс: {format_amount(get_balance(user_id))}$"
            )
        else:
            result_message = (
                f"{name}\n"
                f"Краш остановился на: x{crash_coef}\n"
                f"Ваш коэффициент: x{coef}\n"
                f"❌ Вы проиграли {format_amount(amount)}$ (x{coef})\n"
                f"💰 Баланс: {format_amount(get_balance(user_id))}$"
            )

        repeat_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Повторить ставку",
                        callback_data=f"repeat_crash:{coef}:{amount}"
                    )
                ]
            ]
        )
        await message.answer(result_message, reply_markup=repeat_kb)

    except Exception:
        await message.answer("Ошибка обработки ставки", reply_markup=safe_reply_kb(message, menu_kb))



@router.callback_query(F.data.startswith("repeat_crash"))
async def handle_repeat_crash(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    try:
        _, coef_str, amount_str = callback.data.split(":")
        coef = float(coef_str)
        balance = get_balance(user_id)
        # amount_str может быть числом, дробью или "все"
        if amount_str.lower() in ["все", "всё", "all"]:
            amount = balance
        else:
            amount = parse_k(amount_str, balance)
        if amount is None or amount < 10:
            await callback.message.answer("❌ Минимальная ставка — 10$")
            await callback.answer()
            return
        if amount > balance:
            await callback.message.answer("❌ Недостаточно средств на балансе")
            await callback.answer()
            return
        crash_coef = generate_crash_coef()
        win = coef <= crash_coef
        update_balance(user_id, balance - amount)
        if win:
            win_amount = round_amount(amount * coef)
            update_balance(user_id, get_balance(user_id) + win_amount)
            result_message = (
                f"{name}\n"
                f"Краш остановился на: x{crash_coef}\n"
                f"Ваш коэффициент: x{coef}\n"
                f"🎉 Победа! Ваш приз: +{format_amount(win_amount - amount)}$\n"
                f"💰 Баланс: {format_amount(get_balance(user_id))}$"
            )
        else:
            result_message = (
                f"{name}\n"
                f"Краш остановился на: x{crash_coef}\n"
                f"Ваш коэффициент: x{coef}\n"
                f"❌ Вы проиграли {format_amount(amount)}$ (x{coef})\n"
                f"💰 Баланс: {format_amount(get_balance(user_id))}$"
            )
        repeat_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Повторить ставку",
                        callback_data=f"repeat_crash:{coef}:{amount_str}"
                    )
                ]
            ]
        )
        await callback.message.answer(result_message, reply_markup=repeat_kb)
    except Exception:
        await callback.message.answer("Ошибка при повторе ставки")
    await callback.answer()
    
    
def get_next_coin_game_id():
    if coin_games:
        return max(coin_games.keys()) + 1
    return 1

@router.message(F.text.lower().startswith("монетка"))
async def coin_create_or_accept(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    clickable = user.get("clickable_name", True)
    chat_id = message.chat.id
    parts = message.text.lower().split()
    
    if (
        len(parts) == 3
        and parts[1] in ["удалить", "отмена", "cancel", "delete"]
        and parts[2].isdigit()
    ):
        game_id = int(parts[2])
        game = coin_games.get(game_id)
        if not game:
            await message.answer(f"❌ Игра №{game_id} не найдена.", parse_mode="HTML")
            return
        if game["status"] != "waiting":
            await message.answer(f"❌ Игра №{game_id} уже принята или завершена.", parse_mode="HTML")
            return
        if game["creator_id"] != user_id:
            await message.answer("❌ Только создатель может удалить свою игру.", parse_mode="HTML")
            return
        # Возвращаем ставку
        update_balance(user_id, get_balance(user_id) + game["amount"])
        save_user_data()
        del coin_games[game_id]
        save_coin_games()
        await message.answer(f"✅ Игра монетка №{game_id} успешно удалена, ставка возвращена.", parse_mode="HTML")
        return
    
    if len(parts) == 1:
        # Список активных игр
        waiting = [(gid, g) for gid, g in coin_games.items() if g["status"] == "waiting"]
        if not waiting:
            await message.answer("🪙 <b>Активных игр монетка нет.</b>\n\nСоздай: <code>монетка о 1000</code> или <code>монетка р 1000</code>", parse_mode="HTML")
            return
        text = "🪙 <b>Активные игры монетка:</b>\n\n"
        kb_rows = []
        for gid, game in waiting:
            side_emoji = "🦅" if game["choice"] == "орел" else "🪙"
            text += (
                f"<b>№{gid}</b> {side_emoji} {game['choice'].capitalize()} | "
                f"<b>{format_amount(game['amount'])}$</b> | "
                f"{clickable_name(game['creator_id'], game['creator_name'], True)}\n"
            )
            kb_rows.append([InlineKeyboardButton(
                text=f"Принять монетку #{gid}",
                callback_data=f"coin_accept:{gid}"
            )])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
        return

    # Создание игры
    if len(parts) == 3 and parts[1] in ["орел", "орёл", "решка", "о", "р", "орла", "решки", "orел", "resh"]:
        choice = "орел" if parts[1] in ["орел", "орёл", "о"] else "решка"
        amount_text = parts[2]
        balance = get_balance(user_id)
        if amount_text in ["все", "всё", "all"]:
            amount = balance
        else:
            amount = parse_k(amount_text, balance)
        if amount is None or amount <= 0:
            await message.answer("❌ Введите корректную сумму ставки.", parse_mode="HTML")
            return
        if balance < amount:
            await message.answer("❌ Недостаточно средств для ставки.", parse_mode="HTML")
            return
        # Списываем ставку
        update_balance(user_id, balance - amount)
        save_user_data()
        game_id = get_next_coin_game_id()
        coin_games[game_id] = {
            "creator_id": user_id,
            "creator_name": name,
            "choice": choice,
            "amount": amount,
            "status": "waiting",
            "opponent_id": None,
            "chat_id": chat_id,  # сохраняем чат, где создана игра
        }
        save_coin_games()
        side_emoji = "🦅" if choice == "орел" else "🪙"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"🪙 Принять монетку #{game_id}", callback_data=f"coin_accept:{game_id}")],
                [InlineKeyboardButton(text="📋 Список игр", callback_data="coin_list")]
            ]
        )
        await message.answer(
            f"🪙 <b>Монетка #{game_id}</b>\n\n"
            f"👤 Создатель: {clickable_name(user_id, name, clickable)}\n"
            f"{side_emoji} Ставка: <b>{choice.capitalize()}</b> | <b>{format_amount(amount)}$</b>\n\n"
            f"⏳ Ожидается соперник...",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    # Принятие по номеру
    if len(parts) == 2 and parts[1].isdigit():
        game_id = int(parts[1])
        game = coin_games.get(game_id)
        if not game or game["status"] != "waiting":
            await message.answer("❌ Игра не найдена или уже принята.", parse_mode="HTML")
            return
        if user_id == game["creator_id"]:
            await message.answer("❌ Вы не можете принять свою же игру.", parse_mode="HTML")
            return
        if get_balance(user_id) < game["amount"]:
            await message.answer("❌ Недостаточно средств для ставки.", parse_mode="HTML")
            return
        # Списываем ставку второго игрока
        update_balance(user_id, get_balance(user_id) - game["amount"])
        save_user_data()
        game["status"] = "playing"
        game["opponent_id"] = user_id
        game["opponent_name"] = name
        # Разыгрываем монетку честно
        import random
        result = random.choice(["орел", "решка"])
        if result == game["choice"]:
            winner_id = game["creator_id"]
            loser_id = user_id
        else:
            winner_id = user_id
            loser_id = game["creator_id"]
        win_amount = game["amount"] * 2
        update_balance(winner_id, get_balance(winner_id) + win_amount)
        save_user_data()
        # Удаляем игру
        chat_id = game.get("chat_id")
        del coin_games[game_id]
        save_coin_games()
        winner_name = get_user(winner_id).get("name", "Без имени")
        loser_name = get_user(loser_id).get("name", "Без имени")
        # Формируем индивидуальные сообщения
        winner_balance = get_balance(winner_id)
        loser_balance = get_balance(loser_id)
        winner_text = (
            f"Выпала «{result.capitalize()}» [🔘] 👍🏻\n"
            f"💸 Приз: {format_amount(win_amount)}$\n"
            f"💰 Баланс: {format_amount(winner_balance)}$"
        )
        loser_text = (
            f"Выпала «{result.capitalize()}» [🔘] 👎🏻\n"
            f"💸 Приз: 0$\n"
            f"💰 Баланс: {format_amount(loser_balance)}$"
        )
        # Сообщение обоим игрокам в личку
        try:
            await bot.send_message(winner_id, winner_text, parse_mode="HTML")
        except Exception:
            pass
        try:
            await bot.send_message(loser_id, loser_text, parse_mode="HTML")
        except Exception:
            pass
        # Сообщение в чат, если игра была создана не в личке
        if chat_id and chat_id != user_id:
            try:
                await bot.send_message(chat_id, winner_text, parse_mode="HTML")
            except Exception:
                pass
        return

    await message.answer(
        "❌ Неверный формат.\n"
        "Создать игру: <code>монетка орел 1000</code> или <code>монетка решка все</code>\n"
        "Принять игру: <code>монетка 1</code>\n"
        "Посмотреть список: <code>монетка</code>",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("coin_accept:"))
async def coin_accept_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")
    game_id = int(callback.data.split(":")[1])
    game = coin_games.get(game_id)
    if not game or game["status"] != "waiting":
        await callback.answer("Игра не найдена или уже принята.", show_alert=True)
        return
    if user_id == game["creator_id"]:
        await callback.answer("Вы не можете принять свою же игру.", show_alert=True)
        return
    if get_balance(user_id) < game["amount"]:
        await callback.answer("Недостаточно средств для ставки.", show_alert=True)
        return
    # Списываем ставку второго игрока
    update_balance(user_id, get_balance(user_id) - game["amount"])
    save_user_data()
    game["status"] = "playing"
    game["opponent_id"] = user_id
    game["opponent_name"] = name
    # Разыгрываем монетку честно
    import random
    result = random.choice(["орел", "решка"])
    if result == game["choice"]:
        winner_id = game["creator_id"]
        loser_id = user_id
    else:
        winner_id = user_id
        loser_id = game["creator_id"]
    win_amount = game["amount"] * 2
    update_balance(winner_id, get_balance(winner_id) + win_amount)
    save_user_data()
    # Удаляем игру
    chat_id = game.get("chat_id")
    del coin_games[game_id]
    save_coin_games()
    winner_name = get_user(winner_id).get("name", "Без имени")
    loser_name = get_user(loser_id).get("name", "Без имени")
    winner_balance = get_balance(winner_id)
    loser_balance = get_balance(loser_id)
    winner_text = (
        f"Выпала «{result.capitalize()}» [🔘] 👍🏻\n"
        f"💸 Приз: {format_amount(win_amount)}$\n"
        f"💰 Баланс: {format_amount(winner_balance)}$"
    )
    loser_text = (
        f"Выпала «{result.capitalize()}» [🔘] 👎🏻\n"
        f"💸 Приз: 0$\n"
        f"💰 Баланс: {format_amount(loser_balance)}$"
    )
    try:
        await bot.send_message(winner_id, winner_text, parse_mode="HTML")
    except Exception:
        pass
    try:
        await bot.send_message(loser_id, loser_text, parse_mode="HTML")
    except Exception:
        pass
    if chat_id and chat_id != user_id:
        try:
            await bot.send_message(chat_id, winner_text, parse_mode="HTML")
        except Exception:
            pass
    await callback.answer("Игра сыграна!", show_alert=True)

@router.callback_query(F.data == "coin_list")
async def coin_list_callback(callback: CallbackQuery):
    if not coin_games:
        await callback.message.edit_text("❌ Нет активных игр монетка.", parse_mode="HTML")
        await callback.answer()
        return
    text = "<b>🎲 Активные игры монетка:</b>\n\n"
    for gid, game in coin_games.items():
        if game["status"] == "waiting":
            text += (
                f"№{gid}: {clickable_name(game['creator_id'], game['creator_name'], True)} — "
                f"{game['choice'].capitalize()}, ставка: <b>{format_amount(game['amount'])}$</b>\n" 
            )
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()