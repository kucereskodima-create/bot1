import json
import os
import random
import time
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import owners, admins, bot
from utils import (
    save_user_data,
    get_user,
    get_balance,
    update_balance,
    format_amount,
    clickable_name,
    parse_k,
)

router = Router()

RAFFLES_FILE = os.path.join(os.path.dirname(__file__), "raffles.json")


def load_raffles() -> dict:
    if os.path.exists(RAFFLES_FILE):
        try:
            with open(RAFFLES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_raffles(data: dict):
    try:
        with open(RAFFLES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения raffles.json: {e}")


def generate_raffle_id() -> str:
    raffles = load_raffles()
    existing = [int(k) for k in raffles.keys() if k.isdigit()]
    return str(max(existing, default=0) + 1)


class CreateRaffleState(StatesGroup):
    waiting_for_type = State()
    waiting_for_amount = State()
    waiting_for_winners = State()
    waiting_for_duration = State()
    waiting_for_criteria = State()
    waiting_for_criteria_level = State()
    waiting_for_criteria_channel = State()


def is_admin_or_owner(user_id: int) -> bool:
    return user_id in owners or user_id in admins


def raffle_type_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💵 Деньги", callback_data="raffle_type_money"),
            InlineKeyboardButton(text="💎 Битки (DC)", callback_data="raffle_type_bits"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="raffle_cancel")],
    ])


def raffle_criteria_kb(criteria: dict) -> InlineKeyboardMarkup:
    level_text = (
        f"🎚 Уровень: {criteria['min_level']}+ ✅"
        if criteria.get("min_level")
        else "🎚 Мин. уровень"
    )
    channel_text = (
        f"📢 Канал: {criteria['channel']} ✅"
        if criteria.get("channel")
        else "📢 Подписка на канал"
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=level_text, callback_data="raffle_crit_level")],
        [InlineKeyboardButton(text=channel_text, callback_data="raffle_crit_channel")],
        [InlineKeyboardButton(text="✅ Готово — создать розыгрыш", callback_data="raffle_crit_done")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="raffle_cancel")],
    ])


def raffle_join_kb(raffle_id: str, count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🎉 Принять участие  •  {count}",
            callback_data=f"raffle_join_{raffle_id}",
        )]
    ])


def format_duration(seconds: int) -> str:
    if seconds < 3600:
        return f"{seconds // 60} мин."
    elif seconds < 86400:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}ч {m}мин." if m else f"{h}ч"
    else:
        d = seconds // 86400
        h = (seconds % 86400) // 3600
        return f"{d}д {h}ч" if h else f"{d}д"


def parse_duration(text: str):
    text = text.strip().lower()
    try:
        if text.endswith("д") or text.endswith("d"):
            return int(text[:-1]) * 86400
        elif text.endswith("ч") or text.endswith("h"):
            return int(text[:-1]) * 3600
        else:
            mins = int(text)
            return mins * 60 if mins > 0 else None
    except ValueError:
        return None


def build_raffle_text(raffle_id: str, data: dict) -> str:
    reward_type = "💵" if data["type"] == "money" else "💎"
    unit = "$" if data["type"] == "money" else " DC"
    amount = data["amount"]
    winners = data["winners_count"]
    per_winner = amount // winners
    participants = data.get("participants", [])
    end_time = data["end_time"]
    criteria = data.get("criteria", {})
    end_dt = datetime.fromtimestamp(end_time).strftime("%d.%m %H:%M")

    crit_lines = ""
    if criteria.get("min_level"):
        crit_lines += f"\n   🎚 Мин. уровень: <b>{criteria['min_level']}</b>"
    if criteria.get("channel"):
        crit_lines += f"\n   📢 Подписка: <b>{criteria['channel']}</b>"
    if not crit_lines:
        crit_lines = "\n   ✅ Без критериев"

    prize_line = (
        f"{reward_type} <b>{format_amount(amount)}{unit}</b>"
        if winners == 1
        else f"{reward_type} <b>{format_amount(per_winner)}{unit}</b> × {winners} победителя"
    )

    return (
        f"🎰 <b>РОЗЫГРЫШ #{raffle_id}</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"🏆 Приз: {prize_line}\n"
        f"👑 Победителей: <b>{winners}</b>\n\n"
        f"⏰ Конец: <b>{end_dt}</b>\n\n"
        f"📋 Критерии:{crit_lines}\n\n"
        f"👥 Участников: <b>{len(participants)}</b>\n"
        f"━━━━━━━━━━━━━━━"
    )


# ─── Создание розыгрыша ─────────────────────────────────────────────────────

@router.message(F.text.lower().in_(["создать розыгрыш", "🎰 создать розыгрыш"]))
async def cmd_create_raffle(message: Message, state: FSMContext):
    user_id = message.from_user.id
    has_access = is_admin_or_owner(user_id)
    if not has_access:
        try:
            from donate import is_vip
            has_access = is_vip(user_id)
        except Exception:
            pass
    if not has_access:
        await message.answer("❌ Создание розыгрышей доступно администраторам и VIP игрокам.\n\n💡 Получите VIP статус в донат магазине!")
        return
    await message.answer(
        "🎰 <b>Создание розыгрыша</b>\n\nВыберите тип награды:",
        parse_mode="HTML",
        reply_markup=raffle_type_kb(),
    )
    await state.set_state(CreateRaffleState.waiting_for_type)


@router.callback_query(
    F.data.in_(["raffle_type_money", "raffle_type_bits"]),
    CreateRaffleState.waiting_for_type,
)
async def raffle_set_type(callback: CallbackQuery, state: FSMContext):
    reward_type = "money" if callback.data == "raffle_type_money" else "bits"
    label = "💵 деньги ($)" if reward_type == "money" else "💎 битки (DC)"
    await state.update_data(raffle_type=reward_type)
    await callback.message.edit_text(
        f"Тип: <b>{label}</b>\n\n"
        "Введите <b>сумму</b> приза:\n\n"
        "📌 Примеры: <code>1000</code> / <code>100к</code> / <code>1кк</code>",
        parse_mode="HTML",
    )
    await state.set_state(CreateRaffleState.waiting_for_amount)
    await callback.answer()


@router.callback_query(F.data == "raffle_cancel")
async def raffle_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Создание розыгрыша отменено.")
    await callback.answer()


@router.message(CreateRaffleState.waiting_for_amount)
async def raffle_set_amount(message: Message, state: FSMContext):
    amount = parse_k(message.text.strip())
    if amount is None or amount <= 0:
        await message.answer(
            "❌ Некорректная сумма. Пример: <code>1кк</code>", parse_mode="HTML"
        )
        return
    user_id = message.from_user.id
    data = await state.get_data()
    reward_type = data["raffle_type"]
    if reward_type == "money":
        balance = get_balance(user_id)
        if balance < amount:
            await message.answer(
                f"❌ Недостаточно средств.\n"
                f"Ваш баланс: <b>{format_amount(balance)}$</b>, нужно: <b>{format_amount(amount)}$</b>",
                parse_mode="HTML",
            )
            return
    else:
        user = get_user(user_id)
        dc = user.get("donate_coins", 0)
        if dc < amount:
            await message.answer(
                f"❌ Недостаточно биток.\n"
                f"У вас: <b>{format_amount(dc)} DC</b>, нужно: <b>{format_amount(amount)} DC</b>",
                parse_mode="HTML",
            )
            return
    await state.update_data(raffle_amount=amount)
    await message.answer(
        f"Сумма: <b>{format_amount(amount)}</b>\n\nВведите <b>количество победителей</b>:",
        parse_mode="HTML",
    )
    await state.set_state(CreateRaffleState.waiting_for_winners)


@router.message(CreateRaffleState.waiting_for_winners)
async def raffle_set_winners(message: Message, state: FSMContext):
    try:
        winners = int(message.text.strip())
        if winners <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое положительное число:")
        return
    await state.update_data(raffle_winners=winners)
    await message.answer(
        f"Победителей: <b>{winners}</b>\n\n"
        "Введите <b>длительность</b> розыгрыша:\n\n"
        "📌 Примеры:\n"
        "• <code>30</code> — 30 минут\n"
        "• <code>2ч</code> — 2 часа\n"
        "• <code>1д</code> — 1 день",
        parse_mode="HTML",
    )
    await state.set_state(CreateRaffleState.waiting_for_duration)


@router.message(CreateRaffleState.waiting_for_duration)
async def raffle_set_duration(message: Message, state: FSMContext):
    secs = parse_duration(message.text.strip())
    if secs is None or secs < 60:
        await message.answer(
            "❌ Минимум 1 минута. Примеры: <code>30</code>, <code>2ч</code>, <code>1д</code>",
            parse_mode="HTML",
        )
        return
    if secs > 7 * 86400:
        await message.answer("❌ Максимум 7 дней.")
        return
    await state.update_data(raffle_duration=secs, raffle_criteria={})
    await message.answer(
        f"Длительность: <b>{format_duration(secs)}</b>\n\n"
        "⚙️ Настройте <b>критерии</b> участия:",
        parse_mode="HTML",
        reply_markup=raffle_criteria_kb({}),
    )
    await state.set_state(CreateRaffleState.waiting_for_criteria)


@router.callback_query(F.data == "raffle_crit_level", CreateRaffleState.waiting_for_criteria)
async def raffle_crit_level_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите <b>минимальный уровень</b> (например: <code>3</code>):",
        parse_mode="HTML",
    )
    await state.set_state(CreateRaffleState.waiting_for_criteria_level)
    await callback.answer()


@router.message(CreateRaffleState.waiting_for_criteria_level)
async def raffle_crit_level_set(message: Message, state: FSMContext):
    try:
        level = int(message.text.strip())
        if level <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректный уровень:")
        return
    data = await state.get_data()
    criteria = data.get("raffle_criteria", {})
    criteria["min_level"] = level
    await state.update_data(raffle_criteria=criteria)
    await message.answer(
        f"✅ Мин. уровень: <b>{level}</b>\n\nВыберите ещё критерии или нажмите «Готово»:",
        parse_mode="HTML",
        reply_markup=raffle_criteria_kb(criteria),
    )
    await state.set_state(CreateRaffleState.waiting_for_criteria)


@router.callback_query(F.data == "raffle_crit_channel", CreateRaffleState.waiting_for_criteria)
async def raffle_crit_channel_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите <b>юзернейм канала</b> (например: <code>@mychannel</code>):",
        parse_mode="HTML",
    )
    await state.set_state(CreateRaffleState.waiting_for_criteria_channel)
    await callback.answer()


@router.message(CreateRaffleState.waiting_for_criteria_channel)
async def raffle_crit_channel_set(message: Message, state: FSMContext):
    channel = message.text.strip()
    if not channel.startswith("@"):
        channel = "@" + channel
    data = await state.get_data()
    criteria = data.get("raffle_criteria", {})
    criteria["channel"] = channel
    await state.update_data(raffle_criteria=criteria)
    await message.answer(
        f"✅ Канал: <b>{channel}</b>\n\nВыберите ещё критерии или нажмите «Готово»:",
        parse_mode="HTML",
        reply_markup=raffle_criteria_kb(criteria),
    )
    await state.set_state(CreateRaffleState.waiting_for_criteria)


@router.callback_query(F.data == "raffle_crit_done", CreateRaffleState.waiting_for_criteria)
async def raffle_crit_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    raffle_type = data["raffle_type"]
    amount = data["raffle_amount"]
    winners = data["raffle_winners"]
    duration = data["raffle_duration"]
    criteria = data.get("raffle_criteria", {})
    per_winner = amount // winners
    type_label = "💵 деньги ($)" if raffle_type == "money" else "💎 битки (DC)"

    crit_lines = ""
    if criteria.get("min_level"):
        crit_lines += f"\n   🎚 Мин. уровень: {criteria['min_level']}"
    if criteria.get("channel"):
        crit_lines += f"\n   📢 Канал: {criteria['channel']}"
    if not crit_lines:
        crit_lines = "\n   ✅ Без критериев"

    tmp_id = generate_raffle_id()
    await state.update_data(raffle_tmp_id=tmp_id)

    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━\n"
        "🎰 <b>Итог розыгрыша</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        f"🎁 Тип: {type_label}\n"
        f"💰 Общий приз: <b>{format_amount(amount)}</b>\n"
        f"👑 Победителей: <b>{winners}</b>\n"
        f"🏅 Каждому: <b>{format_amount(per_winner)}</b>\n"
        f"⏰ Длительность: <b>{format_duration(duration)}</b>\n"
        f"📋 Критерии:{crit_lines}\n\n"
        "━━━━━━━━━━━━━━━\n"
        "⚠️ Сумма будет списана с баланса при создании.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Создать", callback_data=f"raffle_confirm_{tmp_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="raffle_cancel"),
            ]
        ]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("raffle_confirm_"))
async def raffle_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    creator_id = callback.from_user.id
    raffle_type = data.get("raffle_type")
    amount = data.get("raffle_amount")
    winners = data.get("raffle_winners")
    duration = data.get("raffle_duration")
    criteria = data.get("raffle_criteria", {})

    if not all([raffle_type, amount, winners, duration]):
        await callback.answer("Ошибка данных, попробуйте снова.", show_alert=True)
        await state.clear()
        return

    if raffle_type == "money":
        balance = get_balance(creator_id)
        if balance < amount:
            await callback.answer("Недостаточно средств!", show_alert=True)
            return
        update_balance(creator_id, balance - amount)
    else:
        user = get_user(creator_id)
        dc = user.get("donate_coins", 0)
        if dc < amount:
            await callback.answer("Недостаточно биток!", show_alert=True)
            return
        user["donate_coins"] = dc - amount
        save_user_data()

    raffle_id = generate_raffle_id()
    end_time = int(time.time()) + duration

    raffle_data = {
        "creator_id": creator_id,
        "type": raffle_type,
        "amount": amount,
        "winners_count": winners,
        "end_time": end_time,
        "criteria": criteria,
        "participants": [],
        "status": "active",
        "chat_id": callback.message.chat.id,
        "message_id": None,
    }

    raffles = load_raffles()
    raffles[raffle_id] = raffle_data
    save_raffles(raffles)
    await state.clear()

    sent = await callback.message.answer(
        build_raffle_text(raffle_id, raffle_data),
        parse_mode="HTML",
        reply_markup=raffle_join_kb(raffle_id, 0),
    )
    raffles[raffle_id]["message_id"] = sent.message_id
    save_raffles(raffles)

    await callback.message.edit_text(
        f"✅ Розыгрыш <b>#{raffle_id}</b> создан! Удачи участникам 🎰",
        parse_mode="HTML",
    )
    await callback.answer("Розыгрыш создан!")


# ─── Участие в розыгрыше ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("raffle_join_"))
async def raffle_join(callback: CallbackQuery):
    user_id = callback.from_user.id
    raffle_id = callback.data.replace("raffle_join_", "")
    raffles = load_raffles()

    if raffle_id not in raffles:
        await callback.answer("Розыгрыш не найден.", show_alert=True)
        return

    raffle = raffles[raffle_id]

    if raffle["status"] != "active":
        await callback.answer("Этот розыгрыш уже завершён.", show_alert=True)
        return

    if int(time.time()) >= raffle["end_time"]:
        await callback.answer("Время розыгрыша истекло.", show_alert=True)
        return

    if user_id in raffle["participants"]:
        await callback.answer("Вы уже участвуете в этом розыгрыше! ✅", show_alert=True)
        return

    user = get_user(user_id)
    criteria = raffle.get("criteria", {})

    if criteria.get("min_level"):
        user_level = user.get("level", 1)
        req = criteria["min_level"]
        if user_level < req:
            await callback.answer(
                f"❌ Нужен уровень {req}+\nВаш уровень: {user_level}",
                show_alert=True,
            )
            return

    if criteria.get("channel"):
        channel = criteria["channel"]
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ("left", "kicked", "banned"):
                await callback.answer(
                    f"❌ Подпишитесь на {channel} для участия!",
                    show_alert=True,
                )
                return
        except Exception:
            pass

    raffle["participants"].append(user_id)
    save_raffles(raffles)

    count = len(raffle["participants"])
    try:
        await bot.edit_message_text(
            chat_id=raffle["chat_id"],
            message_id=raffle["message_id"],
            text=build_raffle_text(raffle_id, raffle),
            parse_mode="HTML",
            reply_markup=raffle_join_kb(raffle_id, count),
        )
    except Exception:
        pass

    await callback.answer(f"🎉 Вы участвуете в розыгрыше #{raffle_id}!", show_alert=True)


# ─── Завершение розыгрышей (вызывается планировщиком) ───────────────────────

@router.message(F.text.lower().in_(["📋 все розыгрыши", "все розыгрыши"]))
async def cmd_admin_raffles(message: Message):
    if not is_admin_or_owner(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    raffles = load_raffles()
    if not raffles:
        await message.answer("📋 Розыгрышей нет.")
        return
    now = int(time.time())
    text = "📋 <b>Все розыгрыши:</b>\n\n"
    buttons = []
    for rid, r in sorted(raffles.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        unit = "$" if r["type"] == "money" else " DC"
        amount = r["amount"]
        winners = r["winners_count"]
        count = len(r.get("participants", []))
        status = r["status"]
        if status == "active" and now >= r["end_time"]:
            status_icon = "⏳"
        elif status == "active":
            status_icon = "✅"
        else:
            status_icon = "🏁"
        text += f"{status_icon} <b>#{rid}</b> — {format_amount(amount)}{unit} | 👑{winners} | 👥{count}\n"
        buttons.append([
            InlineKeyboardButton(
                text=f"🔍 #{rid}",
                callback_data=f"radm_info_{rid}",
            )
        ])
    await message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("radm_info_"))
async def raffle_admin_info(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("Нет прав.", show_alert=True)
        return
    rid = callback.data.replace("radm_info_", "")
    raffles = load_raffles()
    if rid not in raffles:
        await callback.answer("Розыгрыш не найден.", show_alert=True)
        return
    r = raffles[rid]
    now = int(time.time())
    unit = "$" if r["type"] == "money" else " DC"
    amount = r["amount"]
    winners = r["winners_count"]
    per_winner = amount // winners
    count = len(r.get("participants", []))
    end_dt = datetime.fromtimestamp(r["end_time"]).strftime("%d.%m.%Y %H:%M")
    status = r["status"]
    if status == "active" and now >= r["end_time"]:
        status_text = "⏳ Ожидает завершения"
    elif status == "active":
        remaining = r["end_time"] - now
        status_text = f"✅ Активен (осталось {format_duration(remaining)})"
    else:
        status_text = "🏁 Завершён"
    criteria = r.get("criteria", {})
    crit_text = ""
    if criteria.get("min_level"):
        crit_text += f"\n   🎚 Мин. уровень: {criteria['min_level']}"
    if criteria.get("channel"):
        crit_text += f"\n   📢 Канал: {criteria['channel']}"
    if not crit_text:
        crit_text = "\n   ✅ Без критериев"
    text = (
        f"━━━━━━━━━━━━━━━\n"
        f"🎰 <b>Розыгрыш #{rid}</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📌 Статус: {status_text}\n"
        f"🏆 Приз: <b>{format_amount(amount)}{unit}</b>\n"
        f"👑 Победителей: <b>{winners}</b> (по <b>{format_amount(per_winner)}{unit}</b>)\n"
        f"⏰ Конец: <b>{end_dt}</b>\n\n"
        f"👥 Участников: <b>{count}</b>\n"
        f"📋 Критерии:{crit_text}\n\n"
        f"━━━━━━━━━━━━━━━"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить розыгрыш", callback_data=f"radm_del_{rid}")],
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="radm_back")],
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("radm_del_"))
async def raffle_admin_delete(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("Нет прав.", show_alert=True)
        return
    rid = callback.data.replace("radm_del_", "")
    raffles = load_raffles()
    if rid not in raffles:
        await callback.answer("Розыгрыш не найден.", show_alert=True)
        return
    r = raffles[rid]
    # Вернуть деньги создателю если розыгрыш был активен
    if r["status"] == "active":
        creator_id = r["creator_id"]
        amount = r["amount"]
        if r["type"] == "money":
            update_balance(creator_id, get_balance(creator_id) + amount)
        else:
            u = get_user(creator_id)
            u["donate_coins"] = u.get("donate_coins", 0) + amount
            save_user_data()
        refund_text = f"\n💰 Сумма <b>{format_amount(amount)}</b> возвращена организатору."
    else:
        refund_text = ""
    del raffles[rid]
    save_raffles(raffles)
    await callback.message.edit_text(
        f"✅ Розыгрыш <b>#{rid}</b> удалён.{refund_text}",
        parse_mode="HTML",
    )
    await callback.answer("Удалено!")


@router.callback_query(F.data == "radm_back")
async def raffle_admin_back(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("Нет прав.", show_alert=True)
        return
    raffles = load_raffles()
    if not raffles:
        await callback.message.edit_text("📋 Розыгрышей нет.")
        await callback.answer()
        return
    now = int(time.time())
    text = "📋 <b>Все розыгрыши:</b>\n\n"
    buttons = []
    for rid, r in sorted(raffles.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        unit = "$" if r["type"] == "money" else " DC"
        amount = r["amount"]
        winners = r["winners_count"]
        count = len(r.get("participants", []))
        status = r["status"]
        if status == "active" and now >= r["end_time"]:
            status_icon = "⏳"
        elif status == "active":
            status_icon = "✅"
        else:
            status_icon = "🏁"
        text += f"{status_icon} <b>#{rid}</b> — {format_amount(amount)}{unit} | 👑{winners} | 👥{count}\n"
        buttons.append([InlineKeyboardButton(text=f"🔍 #{rid}", callback_data=f"radm_info_{rid}")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.message(F.text.lower().in_(["розыгрыши", "🎰 розыгрыши", "giveaway", "giveaways"]))
async def cmd_list_raffles(message: Message):
    user_id = message.from_user.id
    raffles = load_raffles()
    now = int(time.time())

    active = {rid: r for rid, r in raffles.items() if r["status"] == "active" and now < r["end_time"]}

    if not active:
        await message.answer(
            "🎰 Активных розыгрышей нет.\n\n"
            "Следите за новыми — они появятся здесь!",
            parse_mode="HTML",
        )
        return

    text = f"🎰 <b>Активные розыгрыши ({len(active)}):</b>\n\n"
    buttons = []

    for rid, r in active.items():
        unit = "$" if r["type"] == "money" else " DC"
        amount = r["amount"]
        winners = r["winners_count"]
        per_winner = amount // winners
        count = len(r.get("participants", []))
        end_time = r["end_time"]
        remaining = end_time - now
        time_left = format_duration(remaining)

        already_in = user_id in r.get("participants", [])
        join_mark = "✅" if already_in else "🎉"

        crit_lines = ""
        criteria = r.get("criteria", {})
        if criteria.get("min_level"):
            crit_lines += f" · 🎚{criteria['min_level']}ур"
        if criteria.get("channel"):
            crit_lines += f" · 📢{criteria['channel']}"

        prize_text = (
            f"<b>{format_amount(amount)}{unit}</b>"
            if winners == 1
            else f"<b>{format_amount(per_winner)}{unit}</b> × {winners}"
        )

        text += (
            f"━━━━━━━━━━━━━━━\n"
            f"🔑 #{rid}\n"
            f"🏆 Приз: {prize_text}\n"
            f"⏰ Осталось: <b>{time_left}</b>\n"
            f"👥 Участников: <b>{count}</b>{crit_lines}\n"
        )
        buttons.append([
            InlineKeyboardButton(
                text=f"{join_mark} #{rid} — {format_amount(per_winner if winners > 1 else amount)}{unit}",
                callback_data=f"raffle_join_{rid}",
            )
        ])

    text += "━━━━━━━━━━━━━━━"
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


async def process_raffles():
    now = int(time.time())
    raffles = load_raffles()
    changed = False

    for raffle_id, raffle in list(raffles.items()):
        if raffle["status"] != "active":
            continue
        if now < raffle["end_time"]:
            continue

        raffle["status"] = "finished"
        changed = True

        participants = raffle.get("participants", [])
        amount = raffle["amount"]
        winners_count = raffle["winners_count"]
        raffle_type = raffle["type"]
        creator_id = raffle["creator_id"]
        chat_id = raffle.get("chat_id")
        message_id = raffle.get("message_id")
        unit = "$" if raffle_type == "money" else " DC"

        if not participants:
            if raffle_type == "money":
                update_balance(creator_id, get_balance(creator_id) + amount)
            else:
                u = get_user(creator_id)
                u["donate_coins"] = u.get("donate_coins", 0) + amount
                save_user_data()
            result_text = (
                f"🎰 <b>РОЗЫГРЫШ #{raffle_id} завершён</b>\n\n"
                f"😔 Никто не принял участие.\n"
                f"Сумма <b>{format_amount(amount)}{unit}</b> возвращена организатору."
            )
        else:
            actual_winners = min(winners_count, len(participants))
            winners = random.sample(participants, actual_winners)
            per_winner = amount // actual_winners
            remainder = amount - per_winner * actual_winners
            winners_text = ""

            for i, w_id in enumerate(winners):
                win_amount = per_winner + (remainder if i == 0 else 0)
                w_user = get_user(w_id)
                w_name = w_user.get("name", "Без имени") if w_user else str(w_id)

                if raffle_type == "money":
                    update_balance(w_id, get_balance(w_id) + win_amount)
                else:
                    w_user["donate_coins"] = w_user.get("donate_coins", 0) + win_amount
                    save_user_data()

                winners_text += (
                    f"🏆 {clickable_name(w_id, w_name)} — "
                    f"<b>+{format_amount(win_amount)}{unit}</b>\n"
                )
                try:
                    await bot.send_message(
                        w_id,
                        f"🎉 Вы победили в розыгрыше <b>#{raffle_id}</b>!\n"
                        f"Награда: <b>+{format_amount(win_amount)}{unit}</b> уже на счёте!",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

            result_text = (
                f"🎰 <b>РОЗЫГРЫШ #{raffle_id} завершён!</b>\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"👥 Участников: <b>{len(participants)}</b>\n\n"
                f"🏆 <b>Победители:</b>\n{winners_text}"
            )

        if chat_id and message_id:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=result_text,
                    parse_mode="HTML",
                )
            except Exception:
                try:
                    await bot.send_message(chat_id, result_text, parse_mode="HTML")
                except Exception:
                    pass

    if changed:
        save_raffles(raffles)
