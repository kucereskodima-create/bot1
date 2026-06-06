import random
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from utils import get_balance, update_balance, format_amount, round_amount, get_user, clickable_name

router = Router()

MIN_BET = 10

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

WIN_PHRASES = [
    "💪 Дилер в шоке!",
    "🤑 Ты обчистил казино!",
    "👑 Король стола!",
    "😎 Красавчик!",
    "🎉 Казино рыдает!",
]

LOSE_PHRASES = [
    "💸 Слив засчитан...",
    "😂 Дилер смеётся над тобой!",
    "🤡 Попытка засчитана!",
    "🪦 RIP кошелёк...",
    "😈 Казино всегда побеждает!",
]


class BlackjackState(StatesGroup):
    playing = State()


def make_deck() -> list:
    deck = [(rank, suit) for suit in SUITS for rank in RANKS]
    random.shuffle(deck)
    return deck


def card_value(rank: str) -> int:
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def hand_score(hand: list) -> int:
    score = sum(card_value(r) for r, _ in hand)
    aces = sum(1 for r, _ in hand if r == "A")
    while score > 21 and aces:
        score -= 10
        aces -= 1
    return score


def fmt_card(rank: str, suit: str) -> str:
    return f"{rank}{suit}"


def fmt_hand(hand: list) -> str:
    return "  ".join(fmt_card(r, s) for r, s in hand)


def build_game_text(name: str, player_hand: list, dealer_hand: list,
                    hide_dealer: bool = True, extra: str = "") -> str:
    p_score = hand_score(player_hand)
    if hide_dealer:
        d_display = f"{fmt_card(*dealer_hand[0])}  🂠"
        d_score = card_value(dealer_hand[0][0])
    else:
        d_display = fmt_hand(dealer_hand)
        d_score = hand_score(dealer_hand)

    text = (
        f"🃏 <b>Блэкджек (21)</b> — {name}\n\n"
        f"🤵‍♂️ Дилер: {d_display} ({d_score})\n"
        f"👤 Вы: {fmt_hand(player_hand)} ({p_score})"
    )
    if extra:
        text += f"\n\n{extra}"
    return text


bj_kb = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="🃏 Взять карту", callback_data="bj_hit"),
    InlineKeyboardButton(text="✋ Стоп", callback_data="bj_stand"),
]])


@router.message(F.text.lower().startswith("бд"))
async def blackjack_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Игрок")
    balance = get_balance(user_id)

    current = await state.get_state()
    if current is not None:
        await message.answer(
            "❌ Вы уже в игре! Завершите текущую игру.",
            parse_mode="HTML",
        )
        return

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите ставку.\n"
            "Пример: <code>блек 1000</code>, <code>блек 10к</code>, <code>блек вб</code>",
            parse_mode="HTML",
        )
        return

    from roulette import parse_amount
    amount = parse_amount(parts[1].lower().strip(), balance)

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

    deck = make_deck()
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]

    await state.set_state(BlackjackState.playing)
    await state.update_data(
        player=player_hand,
        dealer=dealer_hand,
        deck=deck,
        amount=amount,
        name=name,
    )

    p_score = hand_score(player_hand)
    if p_score == 21:
        win_amount = round_amount(amount * 2.5)
        update_balance(user_id, get_balance(user_id) + win_amount)
        await state.clear()
        phrase = random.choice(WIN_PHRASES)
        text = build_game_text(
            name, player_hand, dealer_hand, hide_dealer=False,
            extra=(
                f"🎰 Блэкджек!\n"
                f"🏆 Ты победитель! {phrase}\n"
                f"💰 Выплата: +<b>{format_amount(win_amount)}$</b>\n"
                f"💼 Баланс: <b>{format_amount(get_balance(user_id))}$</b>"
            ),
        )
        await message.answer(text, parse_mode="HTML")
        return

    await message.answer(
        build_game_text(name, player_hand, dealer_hand),
        parse_mode="HTML",
        reply_markup=bj_kb,
    )


@router.callback_query(F.data == "bj_hit", BlackjackState.playing)
async def blackjack_hit(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player_hand = data["player"]
    dealer_hand = data["dealer"]
    deck = data["deck"]
    amount = data["amount"]
    name = data.get("name", "Игрок")
    user_id = callback.from_user.id

    if not deck:
        await callback.answer("Колода закончилась!", show_alert=True)
        return

    player_hand.append(deck.pop())
    p_score = hand_score(player_hand)
    await state.update_data(player=player_hand, deck=deck)

    if p_score > 21:
        await state.clear()
        phrase = random.choice(LOSE_PHRASES)
        text = build_game_text(
            name, player_hand, dealer_hand, hide_dealer=False,
            extra=(
                f"💥 Перебор! {phrase}\n"
                f"💸 Потеряно: <b>{format_amount(amount)}$</b>\n"
                f"💼 Баланс: <b>{format_amount(get_balance(user_id))}$</b>"
            ),
        )
        try:
            await callback.message.edit_text(text, parse_mode="HTML")
        except Exception:
            await callback.message.answer(text, parse_mode="HTML")
        await callback.answer()
        return

    if p_score == 21:
        # Авто-победа с коэффициентом 2.5×
        await state.clear()
        win_amount = round_amount(amount * 2.5)
        update_balance(user_id, get_balance(user_id) + win_amount)
        phrase = random.choice(WIN_PHRASES)
        text = build_game_text(
            name, player_hand, dealer_hand, hide_dealer=False,
            extra=(
                f"🎰 <b>21! Авто-победа!</b> {phrase}\n"
                f"💰 Выплата: +<b>{format_amount(win_amount)}$</b> (×2.5)\n"
                f"💼 Баланс: <b>{format_amount(get_balance(user_id))}$</b>"
            ),
        )
        try:
            await callback.message.edit_text(text, parse_mode="HTML")
        except Exception:
            await callback.message.answer(text, parse_mode="HTML")
        await callback.answer("🎰 21! Авто-победа!")
        return

    try:
        await callback.message.edit_text(
            build_game_text(name, player_hand, dealer_hand),
            parse_mode="HTML",
            reply_markup=bj_kb,
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "bj_stand", BlackjackState.playing)
async def blackjack_stand(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await _finish_game(
        callback, state,
        data["player"], data["dealer"], data["deck"],
        data["amount"], data.get("name", "Игрок"),
        callback.from_user.id,
    )


async def _finish_game(callback, state, player_hand, dealer_hand, deck, amount, name, user_id):
    while hand_score(dealer_hand) < 17 and deck:
        dealer_hand.append(deck.pop())

    p_score = hand_score(player_hand)
    d_score = hand_score(dealer_hand)
    new_balance = get_balance(user_id)

    if d_score > 21 or p_score > d_score:
        win_amount = round_amount(amount * 2)
        update_balance(user_id, new_balance + win_amount)
        phrase = random.choice(WIN_PHRASES)
        extra = (
            f"🏆 Ты победитель! {phrase}\n"
            f"💰 Выплата: +<b>{format_amount(win_amount)}$</b>\n"
            f"💼 Баланс: <b>{format_amount(get_balance(user_id))}$</b>"
        )
    elif p_score == d_score:
        update_balance(user_id, new_balance + amount)
        extra = (
            f"🤝 Ничья! Ставка возвращена.\n"
            f"💼 Баланс: <b>{format_amount(get_balance(user_id))}$</b>"
        )
    else:
        phrase = random.choice(LOSE_PHRASES)
        extra = (
            f"😢 Ты проиграл. {phrase}\n"
            f"💸 Потеряно: <b>{format_amount(amount)}$</b>\n"
            f"💼 Баланс: <b>{format_amount(get_balance(user_id))}$</b>"
        )

    text = build_game_text(name, player_hand, dealer_hand, hide_dealer=False, extra=extra)
    try:
        await callback.message.edit_text(text, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()
