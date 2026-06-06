import random
import time
import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

# ─── Cooldowns (seconds) ──────────────────────────────────────────────────────
COOLDOWN_SUCCESS = 60
COOLDOWN_FAIL    = 30

# ─── Jobs catalogue ───────────────────────────────────────────────────────────
JOBS = [
    {
        "id": "chef",
        "name": "Повар",
        "emoji": "👨‍🍳",
        "scene_emoji": "🍳",
        "description": "Горит заказ на кухне!\nНайдите нужный кухонный предмет.",
        "correct": ("🍳", "Сковорода"),
        "wrong":   [("🧴", "Мыло"), ("🪣", "Ведро"), ("🔑", "Ключ")],
        "salary": 400,
        "xp": 15,
        "min_level": 1,
    },
    {
        "id": "engineer",
        "name": "Инженер",
        "emoji": "👨‍🔧",
        "scene_emoji": "🔧",
        "description": "Сломался станок на заводе!\nНайдите инструмент для ремонта.",
        "correct": ("🔧", "Гаечный ключ"),
        "wrong":   [("📏", "Линейка"), ("🧲", "Магнит"), ("📦", "Ящик")],
        "salary": 800,
        "xp": 30,
        "min_level": 3,
    },
    {
        "id": "police",
        "name": "Полицейский",
        "emoji": "👮",
        "scene_emoji": "📻",
        "description": "Поступил срочный вызов!\nНайдите предмет полицейского.",
        "correct": ("📻", "Рация"),
        "wrong":   [("🎸", "Гитара"), ("🧸", "Игрушка"), ("🍕", "Пицца")],
        "salary": 1_200,
        "xp": 40,
        "min_level": 5,
    },
    {
        "id": "programmer",
        "name": "Программист",
        "emoji": "💻",
        "scene_emoji": "💻",
        "description": "В системе критические баги!\nНайдите устройство для срочной работы.",
        "correct": ("💻", "Ноутбук"),
        "wrong":   [("🎮", "Джойстик"), ("📺", "Телевизор"), ("🎯", "Мишень")],
        "salary": 2_000,
        "xp": 55,
        "min_level": 8,
    },
    {
        "id": "firefighter",
        "name": "Пожарный",
        "emoji": "🔥",
        "scene_emoji": "🧯",
        "description": "Пожарная тревога!\nНайдите инструмент для тушения огня.",
        "correct": ("🧯", "Огнетушитель"),
        "wrong":   [("🍶", "Фляга"), ("🎈", "Шар"), ("🪞", "Зеркало")],
        "salary": 3_000,
        "xp": 70,
        "min_level": 12,
    },
    {
        "id": "doctor",
        "name": "Доктор",
        "emoji": "🏥",
        "scene_emoji": "💉",
        "description": "Пациент ждёт экстренной помощи!\nВыберите медицинский инструмент.",
        "correct": ("💉", "Шприц"),
        "wrong":   [("🍎", "Яблоко"), ("🎸", "Гитара"), ("🔫", "Пистолет")],
        "salary": 5_000,
        "xp": 90,
        "min_level": 16,
    },
]

JOBS_BY_ID = {j["id"]: j for j in JOBS}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fmt(n):
    n = int(n)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _remaining(until_ts):
    secs = int(until_ts - time.time())
    return max(0, secs)


def _add_xp(user, xp_amount):
    """Add XP and handle levelling up. Returns (new_level, levelled_up)."""
    user["experience"] = user.get("experience", 0) + xp_amount
    level = user.get("level", 1)
    levelled_up = False
    while user["experience"] >= level * 100:
        user["experience"] -= level * 100
        level += 1
        levelled_up = True
    user["level"] = level
    return level, levelled_up


def _jobs_menu_kb(user_level: int = 1):
    buttons = []
    for job in JOBS:
        mlvl = job["min_level"]
        if user_level >= mlvl:
            label = f"{job['emoji']} {job['name']}  —  {_fmt(job['salary'])}$  /  +{job['xp']} XP"
            cb    = f"job_start:{job['id']}"
        else:
            label = f"🔒 {job['name']}  —  откроется с уровня {mlvl}"
            cb    = f"job_locked:{job['id']}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _shift_kb(job_id, correct_key, token):
    job = JOBS_BY_ID[job_id]
    options = [(job["correct"][0], job["correct"][1], "1")]
    for em, label in job["wrong"]:
        options.append((em, label, "0"))
    random.shuffle(options)
    buttons = []
    row = []
    for em, label, is_correct in options:
        row.append(InlineKeyboardButton(
            text=f"{em} {label}",
            callback_data=f"job_ans:{job_id}:{is_correct}:{token}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _shift_text(job):
    line = "━━━━━━━━━━━━━━━━━━━━"
    return (
        f"{line}\n"
        f"  {job['emoji']}  <b>{job['name'].upper()}</b>  —  СМЕНА\n"
        f"{line}\n\n"
        f"        {job['scene_emoji']}\n\n"
        f"{line}\n\n"
        f"{job['description']}\n\n"
        f"⏰ <b>Выберите правильный предмет:</b>"
    )


# ─── Main work menu ───────────────────────────────────────────────────────────

@router.message(F.text.lower().in_(["💼 работа", "работа", "работы", "job", "джоб", "/работа", "/job"]))
async def cmd_work(message: Message):
    from utils import get_user
    user = get_user(message.from_user.id)
    cooldown_until = user.get("job_cooldown", 0)
    remaining = _remaining(cooldown_until)

    if remaining > 0:
        await message.answer(
            f"⏳ До следующей смены: <b>{remaining} сек.</b>\n"
            f"Отдыхайте, вы заслужили!",
            parse_mode="HTML"
        )
        return

    user_level = user.get("level", 1)
    line = "━━━━━━━━━━━━━━━━━━━━"
    await message.answer(
        f"{line}\n"
        f"  💼  <b>ВЫБОР ПРОФЕССИИ</b>\n"
        f"{line}\n\n"
        f"🎖 Ваш уровень: <b>{user_level}</b>\n"
        "Выберите работу для следующей смены:\n",
        parse_mode="HTML",
        reply_markup=_jobs_menu_kb(user_level)
    )


# ─── Start shift ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("job_start:"))
async def cb_job_start(callback: CallbackQuery):
    from utils import get_user, save_user_data
    user_id = callback.from_user.id
    job_id = callback.data.split(":")[1]
    job = JOBS_BY_ID.get(job_id)
    if not job:
        await callback.answer("❌ Работа не найдена.", show_alert=True)
        return

    user = get_user(user_id)

    # Проверка уровня
    user_level = user.get("level", 1)
    if user_level < job.get("min_level", 1):
        await callback.answer(
            f"🔒 Профессия откроется с уровня {job['min_level']}. "
            f"Ваш уровень: {user_level}.",
            show_alert=True
        )
        return

    cooldown_until = user.get("job_cooldown", 0)
    remaining = _remaining(cooldown_until)
    if remaining > 0:
        await callback.answer(f"⏳ Подождите ещё {remaining} сек.", show_alert=True)
        return

    token = uuid.uuid4().hex[:10]
    user["job_token"] = token
    user["job_current"] = job_id
    save_user_data()

    await callback.message.edit_text(
        _shift_text(job),
        parse_mode="HTML",
        reply_markup=_shift_kb(job_id, job["correct"][0], token)
    )
    await callback.answer()


# ─── Answer ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("job_ans:"))
async def cb_job_answer(callback: CallbackQuery):
    from utils import get_user, get_balance, update_balance, save_user_data
    user_id = callback.from_user.id
    parts = callback.data.split(":")
    job_id   = parts[1]
    correct  = parts[2] == "1"
    token    = parts[3]

    user = get_user(user_id)

    if user.get("job_token") != token:
        await callback.answer("❌ Смена уже завершена.", show_alert=True)
        return

    job = JOBS_BY_ID.get(job_id)
    if not job:
        await callback.answer("❌ Ошибка.", show_alert=True)
        return

    # Invalidate token so they can't click twice
    user["job_token"] = None
    line = "━━━━━━━━━━━━━━━━━━━━"

    if correct:
        salary = job["salary"]
        xp = job["xp"]
        try:
            from donate import is_vip
            if is_vip(user_id):
                salary = int(salary * 1.5)
        except Exception:
            pass
        try:
            from house_shop import get_shop_house_boosts
            _wb = get_shop_house_boosts(user_id).get("work_boost", 0)
            if _wb:
                salary = int(salary * (1 + _wb / 100))
        except Exception:
            pass
        new_balance = get_balance(user_id) + salary
        update_balance(user_id, new_balance)
        new_level, levelled_up = _add_xp(user, xp)
        user["job_cooldown"] = time.time() + COOLDOWN_SUCCESS
        user["current_work"] = job_id
        save_user_data()
        level_text = f"\n🆙 <b>Новый уровень: {new_level}!</b>" if levelled_up else ""
        result_text = (
            f"{line}\n"
            f"  ✅  СМЕНА ЗАВЕРШЕНА\n"
            f"{line}\n\n"
            f"{job['emoji']} <b>{job['name']}</b> — отличная работа!\n"
            f"Вы справились с заданием.\n\n"
            f"💰 Заработок: <b>+{_fmt(salary)}$</b>\n"
            f"⭐ Опыт: <b>+{xp} XP</b>{level_text}\n\n"
            f"⏳ КД на следующую смену: <b>{COOLDOWN_SUCCESS} сек.</b>\n"
            f"{line}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Список профессий", callback_data="job_menu")]
        ])
    else:
        user["job_cooldown"] = time.time() + COOLDOWN_FAIL
        save_user_data()

        result_text = (
            f"{line}\n"
            f"  ❌  СМЕНА ПРОВАЛЕНА\n"
            f"{line}\n\n"
            f"{job['emoji']} <b>{job['name']}</b> — промах!\n"
            f"Вы выбрали неверный предмет.\n\n"
            f"💰 Заработок: <b>0$</b>\n"
            f"⭐ Опыт: <b>0 XP</b>\n\n"
            f"⏳ КД на следующую смену: <b>{COOLDOWN_FAIL} сек.</b>\n"
            f"{line}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Список профессий", callback_data="job_menu")]
        ])

    await callback.message.edit_text(result_text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


# ─── Back to job menu ────────────────────────────────────────────────────────

@router.callback_query(F.data == "job_menu")
async def cb_job_menu(callback: CallbackQuery):
    from utils import get_user
    user = get_user(callback.from_user.id)
    cooldown_until = user.get("job_cooldown", 0)
    remaining = _remaining(cooldown_until)

    line = "━━━━━━━━━━━━━━━━━━━━"
    if remaining > 0:
        await callback.message.edit_text(
            f"{line}\n"
            f"  ⏳  ПЕРЕРЫВ\n"
            f"{line}\n\n"
            f"До следующей смены: <b>{remaining} сек.</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="job_menu")]
            ])
        )
    else:
        user_level = user.get("level", 1)
        await callback.message.edit_text(
            f"{line}\n"
            f"  💼  <b>ВЫБОР ПРОФЕССИИ</b>\n"
            f"{line}\n\n"
            f"🎖 Ваш уровень: <b>{user_level}</b>\n"
            "Выберите работу для следующей смены:\n",
            parse_mode="HTML",
            reply_markup=_jobs_menu_kb(user_level)
        )
    await callback.answer()


# ─── Locked job tap ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("job_locked:"))
async def cb_job_locked(callback: CallbackQuery):
    from utils import get_user
    job_id = callback.data.split(":")[1]
    job = JOBS_BY_ID.get(job_id)
    if not job:
        await callback.answer("❌ Работа не найдена.", show_alert=True)
        return
    user = get_user(callback.from_user.id)
    user_level = user.get("level", 1)
    need = job["min_level"]
    await callback.answer(
        f"🔒 {job['emoji']} {job['name']} заблокирована.\n"
        f"Требуется уровень {need}. Ваш: {user_level}.",
        show_alert=True
    )
