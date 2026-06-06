import random
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from utils import get_balance, update_balance, format_amount, round_amount, get_user

router = Router()

MIN_BET = 10
GRID = 16        # 4×4
MIN_MINES = 1
MAX_MINES = 13   # at least 3 safe cells remain


class MinesState(StatesGroup):
    playing = State()


def calc_multiplier(mines: int, safe_found: int) -> float:
    """
    Fair multiplier = product of (remaining / safe_remaining) for each safe pick,
    with 0.97 house-edge factor per step.
    """
    if safe_found <= 0:
        return 1.0
    safe_total = GRID - mines
    mult = 1.0
    for i in range(safe_found):
        remaining = GRID - i
        safe_left = safe_total - i
        if safe_left <= 0:
            break
        mult *= (remaining / safe_left) * 0.99
    return round(mult, 2)


def build_kb(revealed: list, mines: list, game_over: bool = False,
             has_safe: bool = False) -> InlineKeyboardMarkup:
    rows = []
    for row in range(4):
        kb_row = []
        for col in range(4):
            idx = row * 4 + col
            if idx in revealed:
                if idx in mines:
                    kb_row.append(InlineKeyboardButton(text="💣", callback_data="mn_noop"))
                else:
                    kb_row.append(InlineKeyboardButton(text="💎", callback_data="mn_noop"))
            elif game_over:
                if idx in mines:
                    kb_row.append(InlineKeyboardButton(text="💣", callback_data="mn_noop"))
                else:
                    kb_row.append(InlineKeyboardButton(text="⬜", callback_data="mn_noop"))
            else:
                kb_row.append(InlineKeyboardButton(
                    text="🟦", callback_data=f"mn_click:{idx}",
                ))
        rows.append(kb_row)

    if not game_over and has_safe:
        rows.append([InlineKeyboardButton(
            text="💰 Забрать выигрыш", callback_data="mn_cashout",
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_text(mines_count: int, safe_found: int, amount: int,
               multiplier: float, extra: str = "") -> str:
    potential = round_amount(amount * multiplier)
    text = (
        f"💣 <b>Мины</b>\n\n"
        f"💣 Мин на поле: <b>{mines_count}</b>\n"
        f"💎 Найдено безопасных: <b>{safe_found}</b>\n"
        f"📈 Множитель: <b>×{multiplier:.2f}</b>\n"
        f"💰 Возможный выигрыш: <b>{format_amount(potential)}$</b>"
    )
    if extra:
        text += f"\n\n{extra}"
    return text


@router.message(F.text.lower().startswith("мины"))
async def mines_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    balance = get_balance(user_id)

    current = await state.get_state()
    if current is not None:
        await message.answer("❌ Вы уже в игре! Завершите текущую игру.")
        return

    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.answer(
            "❌ Укажите количество мин и ставку.\n"
            "Пример: <code>мины 5 1000</code> или <code>мины 10 вб</code>",
            parse_mode="HTML",
        )
        return

    try:
        mines_count = int(parts[1])
    except ValueError:
        await message.answer("❌ Количество мин должно быть числом.", parse_mode="HTML")
        return

    if mines_count < MIN_MINES or mines_count > MAX_MINES:
        await message.answer(
            f"❌ Количество мин: от <b>{MIN_MINES}</b> до <b>{MAX_MINES}</b>.",
            parse_mode="HTML",
        )
        return

    from roulette import parse_amount
    amount = parse_amount(parts[2].lower(), balance)

    if amount is None or amount <= 0:
        await message.answer("❌ Неверная сумма.", parse_mode="HTML")
        return
    if amount < MIN_BET:
        await message.answer(f"❌ Минимальная ставка: <b>{MIN_BET}$</b>", parse_mode="HTML")
        return
    if amount > balance:
        await message.answer(
            f"❌ Недостаточно средств.\n💰 Баланс: <b>{format_amount(balance)}$</b>",
            parse_mode="HTML",
        )
        return

    update_balance(user_id, balance - amount)
    mines_pos = random.sample(range(GRID), mines_count)

    await state.set_state(MinesState.playing)
    await state.update_data(
        mines=mines_pos,
        revealed=[],
        mines_count=mines_count,
        amount=amount,
        multiplier=1.0,
        safe_found=0,
    )

    kb = build_kb([], mines_pos, game_over=False, has_safe=False)
    await message.answer(
        build_text(mines_count, 0, amount, 1.0),
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("mn_click:"), MinesState.playing)
async def mines_click(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    mines: list = data["mines"]
    revealed: list = list(data["revealed"])
    mines_count: int = data["mines_count"]
    amount: int = data["amount"]
    safe_found: int = data["safe_found"]
    user_id = callback.from_user.id

    idx = int(callback.data.split(":")[1])
    if idx in revealed:
        await callback.answer()
        return

    revealed.append(idx)

    if idx in mines:
        await state.clear()
        text = build_text(
            mines_count, safe_found, amount, 0.0,
            extra=(
                f"💥 БУМ! Ты наступил на мину!\n"
                f"💸 Потеряно: <b>{format_amount(amount)}$</b>\n"
                f"💼 Баланс: <b>{format_amount(get_balance(user_id))}$</b>"
            ),
        )
        kb = build_kb(revealed, mines, game_over=True)
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass
        await callback.answer("💥 МИНА!", show_alert=True)
        return

    safe_found += 1
    multiplier = calc_multiplier(mines_count, safe_found)
    safe_total = GRID - mines_count

    if safe_found >= safe_total:
        win_amount = round_amount(amount * multiplier)
        update_balance(user_id, get_balance(user_id) + win_amount)
        await state.clear()
        text = build_text(
            mines_count, safe_found, amount, multiplier,
            extra=(
                f"🏆 Все клетки открыты!\n"
                f"💰 Выигрыш: +<b>{format_amount(win_amount)}$</b>\n"
                f"💼 Баланс: <b>{format_amount(get_balance(user_id))}$</b>"
            ),
        )
        kb = build_kb(revealed, mines, game_over=True)
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass
        await callback.answer("🏆 Победа!", show_alert=True)
        return

    await state.update_data(revealed=revealed, safe_found=safe_found, multiplier=multiplier)
    kb = build_kb(revealed, mines, game_over=False, has_safe=True)
    text = build_text(mines_count, safe_found, amount, multiplier)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "mn_cashout", MinesState.playing)
async def mines_cashout(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    mines: list = data["mines"]
    revealed: list = data["revealed"]
    mines_count: int = data["mines_count"]
    amount: int = data["amount"]
    multiplier: float = data["multiplier"]
    safe_found: int = data["safe_found"]
    user_id = callback.from_user.id

    win_amount = round_amount(amount * multiplier)
    update_balance(user_id, get_balance(user_id) + win_amount)
    await state.clear()

    text = build_text(
        mines_count, safe_found, amount, multiplier,
        extra=(
            f"✅ Выигрыш забран!\n"
            f"💰 +<b>{format_amount(win_amount)}$</b>\n"
            f"💼 Баланс: <b>{format_amount(get_balance(user_id))}$</b>"
        ),
    )
    kb = build_kb(revealed, mines, game_over=True)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer("✅ Выигрыш забран!")


@router.callback_query(F.data == "mn_noop")
async def mines_noop(callback: CallbackQuery):
    await callback.answer()
