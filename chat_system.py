"""
Система казны и топа чата.
3% от проигрышей в рулетку пополняют казну группы.
Команды: чат, топ чаты
"""

import json
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_user, format_amount

router = Router()

CHATS_FILE = os.path.join(os.path.dirname(__file__), "chats.json")
TREASURY_PERCENT = 3
CHAT_LEVELS = [
    1,
    10,
    15,
    20,
    35,
]
CHAT_LEVEL_BONUSES = {
    1: 1.0,
    2: 1.1,
    3: 1.2,
    4: 1.3,
    5: 1.5,
}


# ──────────────────────────────────────────────────────────────────────────────
#  Хранилище
# ──────────────────────────────────────────────────────────────────────────────

def _load_chats() -> dict:
    if os.path.exists(CHATS_FILE):
        try:
            with open(CHATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_chats(data: dict):
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────────────────────────────────────
#  API функции (используются снаружи)
# ──────────────────────────────────────────────────────────────────────────────

def add_to_treasury(chat_id, amount: int) -> int:
    contrib = max(1, int(amount * TREASURY_PERCENT / 100))
    chats = _load_chats()
    cid = str(chat_id)
    if cid not in chats:
        chats[cid] = {"treasury": 0, "top": {}}
    chats[cid]["treasury"] = chats[cid].get("treasury", 0) + contrib
    _save_chats(chats)
    return contrib


def get_treasury(chat_id) -> int:
    chats = _load_chats()
    return chats.get(str(chat_id), {}).get("treasury", 0)


def collect_treasury(chat_id) -> int:
    chats = _load_chats()
    cid = str(chat_id)
    amount = chats.get(cid, {}).get("treasury", 0)
    if cid in chats:
        chats[cid]["treasury"] = 0
    _save_chats(chats)
    return amount


def update_chat_stats(chat_id, user_id, spent: int = 0, won: int = 0):
    chats = _load_chats()
    cid = str(chat_id)
    uid = str(user_id)
    if cid not in chats:
        chats[cid] = {"treasury": 0, "top": {}}
    chats[cid].setdefault("top", {})
    if uid not in chats[cid]["top"]:
        chats[cid]["top"][uid] = {"spent": 0, "won": 0, "games": 0}
    chats[cid]["top"][uid]["spent"] = chats[cid]["top"][uid].get("spent", 0) + spent
    chats[cid]["top"][uid]["won"] = chats[cid]["top"][uid].get("won", 0) + won
    chats[cid]["top"][uid]["games"] = chats[cid]["top"][uid].get("games", 0) + 1
    _save_chats(chats)


def get_chat_level(member_count: int) -> int:
    count = max(1, int(member_count or 1))
    level = 1
    for index, threshold in enumerate(CHAT_LEVELS):
        if count >= threshold:
            level = index + 1
    return min(level, len(CHAT_LEVELS))


# ──────────────────────────────────────────────────────────────────────────────
#  Клавиатура
# ──────────────────────────────────────────────────────────────────────────────

def _chat_kb(has_treasury: bool) -> InlineKeyboardMarkup:
    rows = []
    if has_treasury:
        rows.append([InlineKeyboardButton(text="💰 Собрать казну", callback_data="chat_collect")])
    rows.append([InlineKeyboardButton(text="🏆 Топ чата", callback_data="chat_top")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ──────────────────────────────────────────────────────────────────────────────
#  Команда «чат»
# ──────────────────────────────────────────────────────────────────────────────

@router.message(F.text.lower().in_(["чат", "/чат", "chat", "/chat"]))
async def cmd_chat(message: Message):
    if message.chat.type == "private":
        await message.answer("📊 Статистика чата доступна только в групповых чатах!")
        return

    chat_id = message.chat.id
    chats = _load_chats()
    chat = chats.get(str(chat_id), {})
    treasury = chat.get("treasury", 0)
    top = chat.get("top", {})
    total_games = sum(v.get("games", 0) for v in top.values())
    total_spent = sum(v.get("spent", 0) for v in top.values())
    players = len(top)
    chat_level = get_chat_level(players)
    next_threshold = CHAT_LEVELS[chat_level] if chat_level < len(CHAT_LEVELS) else CHAT_LEVELS[-1]
    bonus = CHAT_LEVEL_BONUSES.get(chat_level, 1.0)

    fill = min(10, int(treasury / max(total_spent, 1) * 10)) if total_spent else 0
    bar = "█" * fill + "░" * (10 - fill)

    text = (
        f"🏙 <b>СТАТИСТИКА ЧАТА</b>\n"
        f"{'━' * 22}\n\n"
        f"🏦 <b>Казна чата</b>\n"
        f"┌─────────────────────\n"
        f"│ 💰 <b>{format_amount(treasury)}$</b>\n"
        f"│ [{bar}]\n"
        f"│ <i>{TREASURY_PERCENT}% от каждого проигрыша в рулетку</i>\n"
        f"└─────────────────────\n\n"
        f"⭐ <b>Лвл чата: {chat_level} / 5</b>\n"
        f"👥 До след. лвл: <b>{players} / {next_threshold}</b>\n"
        f"✨ Бонус: <b>+{bonus:.1f}%</b>\n\n"
        f"📈 <b>Активность</b>\n"
        f"┌─────────────────────\n"
        f"│ 👥 Игроков: <b>{players}</b>\n"
        f"│ 🎰 Всего игр: <b>{total_games}</b>\n"
        f"│ 💸 Оборот: <b>{format_amount(total_spent)}$</b>\n"
        f"└─────────────────────\n\n"
        f"<i>Администраторы чата могут собрать казну кнопкой ниже</i>"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=_chat_kb(treasury > 0))


# ──────────────────────────────────────────────────────────────────────────────
#  Callback: Собрать казну
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "chat_collect")
async def cb_collect(callback: CallbackQuery):
    if callback.message.chat.type == "private":
        await callback.answer("Только в группах!", show_alert=True)
        return

    from config import bot
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id

    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status not in ("administrator", "creator"):
            await callback.answer("⛔ Только администраторы чата могут собирать казну!", show_alert=True)
            return
    except Exception:
        await callback.answer("❌ Не удалось проверить права.", show_alert=True)
        return

    from utils import get_balance, update_balance, save_user_data
    amount = collect_treasury(chat_id)
    if amount <= 0:
        await callback.answer("🏦 Казна пуста — нечего собирать.", show_alert=True)
        return

    update_balance(user_id, get_balance(user_id) + amount)
    save_user_data()

    user = get_user(user_id)
    name = user.get("name", "Администратор")

    try:
        await callback.message.edit_text(
            f"💰 <b>КАЗНА СОБРАНА</b>\n"
            f"{'━' * 22}\n\n"
            f"👤 Собрал: <b>{name}</b>\n"
            f"💵 Получено: <b>{format_amount(amount)}$</b>\n\n"
            f"<i>Казна начнёт пополняться снова\nс новыми проигрышами в рулетку</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏆 Топ чата", callback_data="chat_top")]
            ])
        )
    except Exception:
        await callback.answer(f"✅ {name} собрал {format_amount(amount)}$!", show_alert=True)

    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
#  Callback + команда: Топ чаты
# ──────────────────────────────────────────────────────────────────────────────

async def _show_top(chat_id: int, send_target):
    chats = _load_chats()
    chat = chats.get(str(chat_id), {})
    top = chat.get("top", {})
    treasury = chat.get("treasury", 0)

    if not top:
        text = (
            f"🏆 <b>ТОП ЧАТА</b>\n"
            f"{'━' * 22}\n\n"
            f"😴 Пока никто не играл в рулетку.\n"
            f"Начните — и попадёте в топ!"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏙 Статистика чата", callback_data="chat_stats")]
        ])
        if isinstance(send_target, CallbackQuery):
            try:
                await send_target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
            except Exception:
                await send_target.message.answer(text, parse_mode="HTML", reply_markup=kb)
            await send_target.answer()
        else:
            await send_target.answer(text, parse_mode="HTML", reply_markup=kb)
        return

    sorted_top = sorted(top.items(), key=lambda x: x[1].get("spent", 0), reverse=True)[:10]
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    lines = [
        f"🏆 <b>ТОП ЧАТА — Рулетка</b>",
        f"{'━' * 22}",
        "",
    ]

    for i, (uid, stats) in enumerate(sorted_top):
        try:
            user = get_user(int(uid))
            name = user.get("name", "Без имени")
        except Exception:
            name = f"Игрок {uid}"
        spent = stats.get("spent", 0)
        games = stats.get("games", 0)
        won = stats.get("won", 0)
        ratio = f"{int(won / spent * 100)}%" if spent > 0 else "0%"
        lines.append(
            f"{medals[i]} <b>{name}</b>\n"
            f"   💸 <b>{format_amount(spent)}$</b> ставок  ·  🎰 {games} игр  ·  📈 возврат {ratio}"
        )

    lines += [
        "",
        f"{'─' * 22}",
        f"🏦 Казна: <b>{format_amount(treasury)}$</b>",
    ]

    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏙 Статистика чата", callback_data="chat_stats")]
    ])

    if isinstance(send_target, CallbackQuery):
        try:
            await send_target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await send_target.message.answer(text, parse_mode="HTML", reply_markup=kb)
        await send_target.answer()
    else:
        await send_target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.text.lower().in_(["топ чаты", "топ чата", "/топчата", "/топчаты"]))
async def cmd_chat_top(message: Message):
    if message.chat.type == "private":
        await message.answer("🏆 Топ чата доступен только в групповых чатах!")
        return
    await _show_top(message.chat.id, message)


@router.callback_query(F.data == "chat_top")
async def cb_chat_top(callback: CallbackQuery):
    if callback.message.chat.type == "private":
        await callback.answer("Только в группах!", show_alert=True)
        return
    await _show_top(callback.message.chat.id, callback)


@router.callback_query(F.data == "chat_stats")
async def cb_chat_stats(callback: CallbackQuery):
    if callback.message.chat.type == "private":
        await callback.answer("Только в группах!", show_alert=True)
        return

    chat_id = callback.message.chat.id
    chats = _load_chats()
    chat = chats.get(str(chat_id), {})
    treasury = chat.get("treasury", 0)
    top = chat.get("top", {})
    total_games = sum(v.get("games", 0) for v in top.values())
    total_spent = sum(v.get("spent", 0) for v in top.values())
    players = len(top)
    chat_level = get_chat_level(players)
    next_threshold = CHAT_LEVELS[chat_level] if chat_level < len(CHAT_LEVELS) else CHAT_LEVELS[-1]
    bonus = CHAT_LEVEL_BONUSES.get(chat_level, 1.0)

    fill = min(10, int(treasury / max(total_spent, 1) * 10)) if total_spent else 0
    bar = "█" * fill + "░" * (10 - fill)

    text = (
        f"🏙 <b>СТАТИСТИКА ЧАТА</b>\n"
        f"{'━' * 22}\n\n"
        f"🏦 <b>Казна чата</b>\n"
        f"┌─────────────────────\n"
        f"│ 💰 <b>{format_amount(treasury)}$</b>\n"
        f"│ [{bar}]\n"
        f"│ <i>{TREASURY_PERCENT}% от каждого проигрыша в рулетку</i>\n"
        f"└─────────────────────\n\n"
        f"⭐ <b>Лвл чата: {chat_level} / 5</b>\n"
        f"👥 До след. лвл: <b>{players} / {next_threshold}</b>\n"
        f"✨ Бонус: <b>+{bonus:.1f}%</b>\n\n"
        f"📈 <b>Активность</b>\n"
        f"┌─────────────────────\n"
        f"│ 👥 Игроков: <b>{players}</b>\n"
        f"│ 🎰 Всего игр: <b>{total_games}</b>\n"
        f"│ 💸 Оборот: <b>{format_amount(total_spent)}$</b>\n"
        f"└─────────────────────\n\n"
        f"<i>Администраторы чата могут собрать казну кнопкой ниже</i>"
    )

    try:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=_chat_kb(treasury > 0)
        )
    except Exception:
        await callback.message.answer(
            text, parse_mode="HTML", reply_markup=_chat_kb(treasury > 0)
        )
    await callback.answer()
