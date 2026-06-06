"""
Дуэль — пошаговая перестрелка в группе.
Формат: дуэль [сумма/вб]
"""
import asyncio
import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import bot
from utils import (
    get_user, get_balance, update_balance, save_user_data,
    format_amount, clickable_name, round_amount,
)
from roulette import parse_amount

router = Router()

_duels: dict[int, dict] = {}
_next_id = 1
HIT_CHANCE = 0.45  # 45% шанс попасть за выстрел


def _new_id() -> int:
    global _next_id
    eid = _next_id
    _next_id += 1
    return eid


# ─── Клавиатуры ──────────────────────────────────────────────────────────────

def _pending_kb(duel_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⚔️ Принять дуэль", callback_data=f"duel_accept:{duel_id}"),
        InlineKeyboardButton(text="❌ Удалить",        callback_data=f"duel_cancel:{duel_id}"),
    ]])


def _shoot_kb(duel_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔫 Стрелять", callback_data=f"duel_shoot:{duel_id}"),
    ]])


# ─── Текст состояния дуэли ───────────────────────────────────────────────────

def _status_text(d: dict) -> str:
    p1 = d["p1_name"]
    p2 = d.get("p2_name", "???")
    amount = d["amount"]
    turn = d.get("turn", 1)
    turn_name = p1 if turn == 1 else p2
    log = d.get("log", [])
    log_lines = "\n".join(f"  {line}" for line in log[-8:]) if log else "  —"
    return (
        f"⚔️ <b>ДУЭЛЬ</b>\n\n"
        f"🔫 <b>{p1}</b>  vs  <b>{p2}</b>\n"
        f"💰 Ставка: <b>{format_amount(amount)}$</b>\n\n"
        f"📜 Ход событий:\n{log_lines}\n\n"
        f"🎯 Сейчас стреляет: <b>{turn_name}</b>"
    )


def _result_text(d: dict, winner_name: str, loser_name: str, reason: str = "") -> str:
    amount = d["amount"]
    win_amount = round_amount(amount * 2)
    extra = f"\n⏰ {reason}" if reason else ""
    return (
        f"⚔️ <b>ДУЭЛЬ — ИТОГИ</b>{extra}\n\n"
        f"🔫 <b>{d['p1_name']}</b>  vs  <b>{d['p2_name']}</b>\n\n"
        f"💰 Ставка: <b>{format_amount(amount)}$</b>\n"
        f"🏆 Победитель: <b>{winner_name}</b> (+{format_amount(win_amount)}$)\n"
        f"😵 Проигравший: <b>{loser_name}</b>"
    )


# ─── Таймаут ─────────────────────────────────────────────────────────────────

async def _run_timeout(duel_id: int):
    """Ждёт 2 минуты и объявляет поражение игроку чей ход."""
    await asyncio.sleep(120)
    d = _duels.get(duel_id)
    if not d or d.get("done"):
        return
    d["done"] = True
    turn = d.get("turn", 1)
    loser_id   = d["p1_id"] if turn == 1 else d["p2_id"]
    winner_id  = d["p2_id"] if turn == 1 else d["p1_id"]
    loser_name  = d["p1_name"] if turn == 1 else d["p2_name"]
    winner_name = d["p2_name"] if turn == 1 else d["p1_name"]
    win_amount = round_amount(d["amount"] * 2)
    update_balance(winner_id, get_balance(winner_id) + win_amount)
    save_user_data()
    text = _result_text(d, winner_name, loser_name, reason=f"{loser_name} не выстрелил вовремя!")
    chat_id = d.get("chat_id")
    msg_id  = d.get("msg_id")
    if chat_id and msg_id:
        try:
            await bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id,
                                        parse_mode="HTML", reply_markup=None)
        except Exception:
            try:
                await bot.send_message(chat_id, text, parse_mode="HTML")
            except Exception:
                pass
    _duels.pop(duel_id, None)


def _start_timeout(duel_id: int):
    d = _duels.get(duel_id)
    if not d:
        return
    old = d.get("_task")
    if old and not old.done():
        old.cancel()
    d["_task"] = asyncio.create_task(_run_timeout(duel_id))


# ─── Команда создания дуэли ───────────────────────────────────────────────────

@router.message(F.text.lower().startswith("дуэль"))
async def duel_create(message: Message):
    if message.chat.type == "private":
        await message.answer("⚔️ Дуэль доступна только в групповых чатах!", parse_mode="HTML")
        return

    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Игрок")
    clickable = user.get("clickable_name", True)
    balance = get_balance(user_id)
    parts = message.text.strip().split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "⚔️ <b>Дуэль</b>\n\n"
            "Вызови соперника на дуэль!\n"
            "Команда: <code>дуэль [сумма]</code>\n"
            "Пример: <code>дуэль 5000</code> или <code>дуэль вб</code>",
            parse_mode="HTML",
        )
        return

    amount = parse_amount(parts[1].lower().strip(), balance)
    if amount is None or amount <= 0:
        await message.answer("❌ Неверная сумма.", parse_mode="HTML")
        return
    if amount < 10:
        await message.answer("❌ Минимальная ставка: <b>10$</b>", parse_mode="HTML")
        return
    if amount > balance:
        await message.answer(
            f"❌ Недостаточно средств.\n💰 Баланс: <b>{format_amount(balance)}$</b>",
            parse_mode="HTML",
        )
        return

    # Проверяем нет ли уже активной дуэли от этого пользователя
    for d in _duels.values():
        if d.get("p1_id") == user_id and not d.get("done"):
            await message.answer("❌ У тебя уже есть активная дуэль!", parse_mode="HTML")
            return

    update_balance(user_id, balance - amount)
    save_user_data()

    duel_id = _new_id()
    _duels[duel_id] = {
        "p1_id":   user_id,
        "p1_name": name,
        "p2_id":   None,
        "p2_name": None,
        "amount":  amount,
        "chat_id": message.chat.id,
        "msg_id":  None,
        "turn":    1,
        "log":     [],
        "done":    False,
        "_task":   None,
    }

    text = (
        f"⚔️ <b>ВЫЗОВ НА ДУЭЛЬ!</b>\n\n"
        f"🔫 {clickable_name(user_id, name, clickable)} бросает вызов!\n"
        f"💰 Ставка: <b>{format_amount(amount)}$</b>\n\n"
        f"Кто примет вызов?"
    )
    sent = await message.answer(text, parse_mode="HTML", reply_markup=_pending_kb(duel_id))
    _duels[duel_id]["msg_id"] = sent.message_id

    # Таймаут на принятие (2 мин)
    _start_timeout(duel_id)


# ─── Принять дуэль ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("duel_accept:"))
async def duel_accept(callback: CallbackQuery):
    user_id = callback.from_user.id
    duel_id = int(callback.data.split(":")[1])
    d = _duels.get(duel_id)

    if not d or d.get("done"):
        await callback.answer("Дуэль уже завершена или не найдена.", show_alert=True)
        return
    if d["p2_id"] is not None:
        await callback.answer("Дуэль уже принята.", show_alert=True)
        return
    if user_id == d["p1_id"]:
        await callback.answer("Ты не можешь принять свою же дуэль!", show_alert=True)
        return

    user = get_user(user_id)
    name = user.get("name", "Игрок")
    balance = get_balance(user_id)
    amount = d["amount"]

    if balance < amount:
        await callback.answer(
            f"Недостаточно средств! Нужно {format_amount(amount)}$",
            show_alert=True,
        )
        return

    update_balance(user_id, balance - amount)
    save_user_data()

    d["p2_id"]   = user_id
    d["p2_name"] = name
    d["turn"]    = 1
    d["log"]     = [f"Дуэль начата! Ход у {d['p1_name']}"]

    # Отменяем таймаут ожидания, ставим таймаут хода
    _start_timeout(duel_id)

    text = _status_text(d)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_shoot_kb(duel_id))
    except Exception:
        pass
    await callback.answer()


# ─── Отменить дуэль ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("duel_cancel:"))
async def duel_cancel(callback: CallbackQuery):
    user_id = callback.from_user.id
    duel_id = int(callback.data.split(":")[1])
    d = _duels.get(duel_id)

    if not d:
        await callback.answer("Дуэль не найдена.", show_alert=True)
        return
    if d.get("done"):
        await callback.answer("Дуэль уже завершена.", show_alert=True)
        return
    if d["p2_id"] is not None:
        await callback.answer("Дуэль уже началась, нельзя отменить.", show_alert=True)
        return
    if user_id != d["p1_id"]:
        await callback.answer("Только создатель может отменить дуэль.", show_alert=True)
        return

    d["done"] = True
    task = d.get("_task")
    if task and not task.done():
        task.cancel()

    # Возвращаем ставку
    update_balance(user_id, get_balance(user_id) + d["amount"])
    save_user_data()
    _duels.pop(duel_id, None)

    try:
        await callback.message.edit_text(
            f"❌ <b>{d['p1_name']}</b> отменил(а) дуэль. Ставка возвращена.",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await callback.answer("Дуэль отменена.")


# ─── Выстрел ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("duel_shoot:"))
async def duel_shoot(callback: CallbackQuery):
    user_id = callback.from_user.id
    duel_id = int(callback.data.split(":")[1])
    d = _duels.get(duel_id)

    if not d or d.get("done"):
        await callback.answer("Дуэль завершена.", show_alert=True)
        return

    # Проверяем, участник ли нажимает
    if user_id not in (d["p1_id"], d["p2_id"]):
        await callback.answer("Ты не участник этой дуэли!", show_alert=True)
        return

    turn = d["turn"]
    current_player_id = d["p1_id"] if turn == 1 else d["p2_id"]

    if user_id != current_player_id:
        other_name = d["p1_name"] if turn == 1 else d["p2_name"]
        await callback.answer(f"Сейчас ход {other_name}!", show_alert=True)
        return

    shooter_name = d["p1_name"] if turn == 1 else d["p2_name"]
    target_name  = d["p2_name"] if turn == 1 else d["p1_name"]
    target_id    = d["p2_id"]   if turn == 1 else d["p1_id"]
    winner_id    = user_id

    import random
    hit = random.random() < HIT_CHANCE

    if hit:
        # Попал — победа
        d["done"] = True
        task = d.get("_task")
        if task and not task.done():
            task.cancel()

        win_amount = round_amount(d["amount"] * 2)
        update_balance(winner_id, get_balance(winner_id) + win_amount)
        save_user_data()

        d["log"].append(f"🔫 {shooter_name} → 💥 ПОПАЛ в {target_name}!")

        text = _result_text(d, shooter_name, target_name)
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
        await callback.answer(f"💥 Попал! Ты победил!", show_alert=True)
        _duels.pop(duel_id, None)
    else:
        # Промах — ход переходит
        d["log"].append(f"🔫 {shooter_name} → 💨 Промах!")
        d["turn"] = 2 if turn == 1 else 1
        next_name = d["p2_name"] if d["turn"] == 2 else d["p1_name"]

        # Перезапускаем таймаут
        _start_timeout(duel_id)

        text = _status_text(d)
        try:
            await callback.message.edit_text(text, parse_mode="HTML",
                                             reply_markup=_shoot_kb(duel_id))
        except Exception:
            pass
        await callback.answer("💨 Промах! Ход переходит к сопернику.", show_alert=True)
