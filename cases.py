"""
КЕЙСЫ — система открытия кейсов.
Кейсы: Уникорн, Редкий, Эпик, Лега, Донат
Купить за $, Винты или DC.
Команда: 📦 Кейсы
"""
import random
import time
import json
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_user, get_balance, update_balance, save_user_data, format_amount

router = Router()

# ──────────────────────────────────────────────────────────────────────────────
#  Описание кейсов
# ──────────────────────────────────────────────────────────────────────────────

CASES = {
    "unicorn": {
        "id": "unicorn",
        "name": "🦄 Уникорн",
        "emoji": "🦄",
        "rarity": "Обычный",
        "price_usd": 200_000,
        "price_dc": None,
        "color": "⬜",
    },
    "rare": {
        "id": "rare",
        "name": "🔵 Редкий",
        "emoji": "🔵",
        "rarity": "Редкий",
        "price_usd": 750_000,
        "price_dc": None,
        "color": "🔵",
    },
    "epic": {
        "id": "epic",
        "name": "🟣 Эпик",
        "emoji": "🟣",
        "rarity": "Эпический",
        "price_usd": 3_000_000,
        "price_dc": None,
        "color": "🟣",
    },
    "legendary": {
        "id": "legendary",
        "name": "🟡 Лега",
        "emoji": "🟡",
        "rarity": "Легендарный",
        "price_usd": 10_000_000,
        "price_dc": None,
        "color": "🟡",
    },
    "donate": {
        "id": "donate",
        "name": "💎 Донат",
        "emoji": "💎",
        "rarity": "Донат",
        "price_usd": None,
        "price_dc": 50,
        "color": "💎",
    },
}

# ──────────────────────────────────────────────────────────────────────────────
#  Дропы из кейсов
# ──────────────────────────────────────────────────────────────────────────────

DROPS = {
    "unicorn": [
        {"weight": 55, "type": "money",  "min": 2_000,    "max": 15_000,   "label": "💵 Деньги"},
        {"weight": 20, "type": "money",  "min": 15_001,   "max": 40_000,   "label": "💵 Деньги"},
        {"weight": 12, "type": "car",    "name": "Toyota Camry",    "speed": 200, "cash_value": 150_000,  "label": "🚗 Toyota Camry"},
        {"weight": 8,  "type": "house",  "name": "Квартира",        "rooms": 2,   "cash_value": 60_000,   "label": "🏠 Квартира"},
        {"weight": 5,  "type": "btc",    "min": 0.0005,  "max": 0.003,    "label": "₿ BTC"},
    ],
    "rare": [
        {"weight": 45, "type": "money",  "min": 20_000,   "max": 90_000,   "label": "💵 Деньги"},
        {"weight": 20, "type": "money",  "min": 90_001,   "max": 200_000,  "label": "💵 Деньги"},
        {"weight": 12, "type": "car",    "name": "BMW M5",           "speed": 290, "cash_value": 600_000,  "label": "🚗 BMW M5"},
        {"weight": 8,  "type": "house",  "name": "Коттедж",          "rooms": 4,   "cash_value": 300_000,  "label": "🏠 Коттедж"},
        {"weight": 15, "type": "btc",    "min": 0.003,   "max": 0.015,    "label": "₿ BTC"},
    ],
    "epic": [
        {"weight": 40, "type": "money",  "min": 100_000,  "max": 450_000,  "label": "💵 Деньги"},
        {"weight": 18, "type": "money",  "min": 450_001,  "max": 1_000_000,"label": "💵 Деньги"},
        {"weight": 12, "type": "car",    "name": "Porsche 911 Turbo", "speed": 330, "cash_value": 2_500_000, "label": "🚗 Porsche 911 Turbo"},
        {"weight": 8,  "type": "house",  "name": "Пентхаус",         "rooms": 6,   "cash_value": 1_500_000, "label": "🏠 Пентхаус"},
        {"weight": 19, "type": "btc",    "min": 0.015,   "max": 0.08,     "label": "₿ BTC"},
        {"weight": 3,  "type": "case",   "case_id": "rare",              "label": "🔵 Редкий кейс"},
    ],
    "legendary": [
        {"weight": 30, "type": "money",  "min": 500_000,  "max": 2_000_000,"label": "💵 Деньги"},
        {"weight": 18, "type": "money",  "min": 2_000_001,"max": 5_000_000,"label": "💵 Деньги"},
        {"weight": 12, "type": "car",    "name": "Lamborghini Aventador", "speed": 380, "cash_value": 12_000_000, "label": "🚗 Lamborghini Aventador"},
        {"weight": 8,  "type": "house",  "name": "Вилла на побережье",   "rooms": 8,   "cash_value": 8_000_000,  "label": "🏠 Вилла"},
        {"weight": 25, "type": "btc",    "min": 0.08,    "max": 0.4,      "label": "₿ BTC"},
        {"weight": 4,  "type": "case",   "case_id": "epic",              "label": "🟣 Эпик кейс"},
        {"weight": 3,  "type": "dc",     "min": 2,       "max": 8,        "label": "💎 DC"},
    ],
    "donate": [
        {"weight": 25, "type": "money",  "min": 2_000_000,"max": 8_000_000,"label": "💵 Деньги"},
        {"weight": 15, "type": "money",  "min": 8_000_001,"max": 20_000_000,"label": "💵 Деньги"},
        {"weight": 10, "type": "car",    "name": "Bugatti Chiron",       "speed": 420, "cash_value": 50_000_000, "label": "🚗 Bugatti Chiron"},
        {"weight": 8,  "type": "house",  "name": "Замок",                "rooms": 15,  "cash_value": 35_000_000, "label": "🏠 Замок"},
        {"weight": 30, "type": "btc",    "min": 0.3,     "max": 1.5,      "label": "₿ BTC"},
        {"weight": 5,  "type": "case",   "case_id": "legendary",         "label": "🟡 Лега кейс"},
        {"weight": 7,  "type": "dc",     "min": 5,       "max": 20,       "label": "💎 DC"},
    ],
}


def _weighted_choice(drops: list) -> dict:
    total = sum(d["weight"] for d in drops)
    r = random.uniform(0, total)
    cumulative = 0
    for drop in drops:
        cumulative += drop["weight"]
        if r <= cumulative:
            return drop
    return drops[-1]


def open_case(user_id: int, case_id: str) -> dict:
    from farm import get_farm
    if case_id not in DROPS:
        return {"error": "Неизвестный кейс"}

    drop = _weighted_choice(DROPS[case_id])
    user = get_user(user_id)
    assets = user.setdefault("assets", {})
    assets.setdefault("cars", [])
    assets.setdefault("houses", [])
    assets.setdefault("cases", [])
    assets.setdefault("yachts", [])
    assets.setdefault("planes", [])
    assets.setdefault("helicopters", [])
    assets.setdefault("smartphones", [])
    result = {"drop": drop, "case_id": case_id}

    dtype = drop["type"]

    if dtype == "money":
        amount = random.randint(drop["min"], drop["max"])
        update_balance(user_id, get_balance(user_id) + amount)
        result["amount"] = amount
        result["text"] = f"💵 <b>{format_amount(amount)}$</b>"

    elif dtype == "car":
        cash_val = drop.get("cash_value", 0)
        already_owned = any(c.get("name") == drop["name"] for c in assets["cars"])
        if already_owned and cash_val:
            update_balance(user_id, get_balance(user_id) + cash_val)
            save_user_data()
            result["text"] = f"🚗 <b>{drop['name']}</b> уже есть → 💵 <b>{format_amount(cash_val)}$</b>"
            result["duplicate"] = True
            result["amount"] = cash_val
        else:
            car = {"name": drop["name"], "speed": drop["speed"], "source": f"case_{case_id}"}
            assets["cars"].append(car)
            save_user_data()
            result["text"] = f"🚗 <b>{drop['name']}</b>"

    elif dtype == "house":
        cash_val = drop.get("cash_value", 0)
        already_owned = any(h.get("name") == drop["name"] for h in assets["houses"])
        if already_owned and cash_val:
            update_balance(user_id, get_balance(user_id) + cash_val)
            save_user_data()
            result["text"] = f"🏠 <b>{drop['name']}</b> уже есть → 💵 <b>{format_amount(cash_val)}$</b>"
            result["duplicate"] = True
            result["amount"] = cash_val
        else:
            house = {"name": drop["name"], "rooms": drop["rooms"], "source": f"case_{case_id}"}
            assets["houses"].append(house)
            save_user_data()
            result["text"] = f"🏠 <b>{drop['name']}</b>"

    elif dtype == "btc":
        amount = round(random.uniform(drop["min"], drop["max"]), 6)
        farm = get_farm(user_id)
        farm["btc_balance"] = round(farm.get("btc_balance", 0.0) + amount, 6)
        save_user_data()
        result["amount"] = amount
        result["text"] = f"₿ <b>{amount:.6f} BTC</b>"

    elif dtype == "dc":
        amount = random.randint(drop["min"], drop["max"])
        user["donate_coins"] = user.get("donate_coins", 0) + amount
        save_user_data()
        result["amount"] = amount
        result["text"] = f"💎 <b>{amount} DC</b>"

    elif dtype == "case":
        cid = drop["case_id"]
        cname = CASES[cid]["name"]
        assets["cases"].append({"case_id": cid, "name": cname})
        save_user_data()
        result["text"] = f"{CASES[cid]['emoji']} <b>{cname}</b>"

    return result


def get_user_cases(user_id: int) -> list:
    user = get_user(user_id)
    return user.get("assets", {}).get("cases", [])


def add_case_to_user(user_id: int, case_id: str):
    user = get_user(user_id)
    case_info = CASES[case_id]
    user.setdefault("assets", {}).setdefault("cases", []).append({
        "case_id": case_id,
        "name": case_info["name"],
    })
    save_user_data()


def remove_case_from_user(user_id: int, case_id: str) -> bool:
    user = get_user(user_id)
    cases = user.get("assets", {}).get("cases", [])
    for i, c in enumerate(cases):
        if c.get("case_id") == case_id:
            cases.pop(i)
            save_user_data()
            return True
    return False


# ──────────────────────────────────────────────────────────────────────────────
#  Клавиатуры
# ──────────────────────────────────────────────────────────────────────────────

def _cases_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Магазин кейсов",   callback_data="cases_shop")],
        [InlineKeyboardButton(text="🎒 Мои кейсы",        callback_data="cases_my")],
        [InlineKeyboardButton(text="🔄 Обновить",         callback_data="cases_main")],
    ])


def _shop_kb() -> InlineKeyboardMarkup:
    rows = []
    for key, case in CASES.items():
        if key == "donate":
            continue
        prices = []
        if case["price_usd"]:
            prices.append(f"{format_amount(case['price_usd'])}$")
        if case["price_dc"]:
            prices.append(f"{case['price_dc']} DC")
        price_str = " / ".join(prices)
        rows.append([InlineKeyboardButton(
            text=f"{case['name']} — {price_str}",
            callback_data=f"cases_view:{key}"
        )])
    rows.append([InlineKeyboardButton(text="💎 Донат кейс", callback_data="donate_cases_menu")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="cases_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _case_buy_kb(case_id: str, case: dict, user_id: int = 0) -> InlineKeyboardMarkup:
    from donate import is_vip
    from admin_roles import is_admin_any
    vip = is_vip(user_id) if user_id else False
    admin = is_admin_any(user_id) if user_id else False
    rows = []
    if case["price_usd"]:
        rows.append([InlineKeyboardButton(
            text=f"💵 Купить ×1 за {format_amount(case['price_usd'])}$",
            callback_data=f"cases_buy:{case_id}:usd:1"
        )])
        if vip:
            rows.append([InlineKeyboardButton(
                text=f"⭐ Купить ×10 за {format_amount(case['price_usd'] * 10)}$ (VIP)",
                callback_data=f"cases_buy:{case_id}:usd:10"
            )])
        if admin:
            rows.append([InlineKeyboardButton(
                text=f"🛡 Купить ×50 (Адм.)",
                callback_data=f"cases_buy:{case_id}:usd:50"
            )])
    if case["price_dc"]:
        rows.append([InlineKeyboardButton(
            text=f"💎 Купить ×1 за {case['price_dc']} DC",
            callback_data=f"cases_buy:{case_id}:dc:1"
        )])
        if vip:
            rows.append([InlineKeyboardButton(
                text=f"⭐ Купить ×10 за {case['price_dc'] * 10} DC (VIP)",
                callback_data=f"cases_buy:{case_id}:dc:10"
            )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="cases_shop")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _my_cases_kb(user_id: int) -> InlineKeyboardMarkup:
    cases = get_user_cases(user_id)
    if not cases:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 В магазин", callback_data="cases_shop")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="cases_main")],
        ])
    counts = {}
    for c in cases:
        cid = c.get("case_id", "unicorn")
        counts[cid] = counts.get(cid, 0) + 1
    rows = []
    for cid, cnt in counts.items():
        cinfo = CASES.get(cid, {})
        cname = cinfo.get("name", cid)
        rows.append([InlineKeyboardButton(
            text=f"{cname} ×{cnt}",
            callback_data=f"cases_open_menu:{cid}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="cases_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _open_menu_kb(case_id: str, count: int, user_id: int = 0) -> InlineKeyboardMarkup:
    from donate import is_vip
    from admin_roles import is_admin_any
    cinfo = CASES.get(case_id, {})
    vip = is_vip(user_id) if user_id else False
    admin = is_admin_any(user_id) if user_id else False
    rows = [
        [InlineKeyboardButton(
            text=f"🎁 Открыть ×1",
            callback_data=f"cases_open:{case_id}:1"
        )],
    ]
    if vip and count >= 10:
        rows.append([InlineKeyboardButton(
            text=f"⭐ Открыть ×10 (VIP)",
            callback_data=f"cases_open:{case_id}:10"
        )])
    elif vip and count > 1:
        rows.append([InlineKeyboardButton(
            text=f"⭐ Открыть все ×{count} (VIP)",
            callback_data=f"cases_open:{case_id}:{count}"
        )])
    if admin and count >= 50:
        rows.append([InlineKeyboardButton(
            text=f"🛡 Открыть ×50 (Адм.)",
            callback_data=f"cases_open:{case_id}:50"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="cases_my")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ──────────────────────────────────────────────────────────────────────────────
#  Текст главной страницы кейсов
# ──────────────────────────────────────────────────────────────────────────────

def _cases_main_text() -> str:
    lines = [
        "📦 <b>КЕЙСЫ BLACKLINE</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        "🎰 Открывай кейсы и выигрывай крупные призы —",
        "деньги, машины, дома и криптовалюту!",
        "",
        "┌─────────────────────────",
        "│ 🦄 <b>Уникорн</b>  <i>Обычный</i>",
        "│    💵 200.000$",
        "│",
        "│ 🔵 <b>Редкий</b>  <i>Редкий</i>",
        "│    💵 750.000$",
        "│",
        "│ 🟣 <b>Эпик</b>  <i>Эпический</i>",
        "│    💵 3.000.000$",
        "│",
        "│ 🟡 <b>Лега</b>  <i>Легендарный</i>",
        "│    💵 10.000.000$",
        "│",
        "└─────────────────────────",
        "",
        "💎 <b>Донат кейс</b> — доступен только в разделе доната.",
        "",
        "<i>Чем выше редкость — тем ценнее награда.</i>",
    ]
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
#  Хендлеры
# ──────────────────────────────────────────────────────────────────────────────

@router.message(F.text.lower().in_(["📦 кейсы", "кейсы", "/кейсы", "/cases"]))
async def cmd_cases(message: Message):
    await message.answer(_cases_main_text(), parse_mode="HTML", reply_markup=_cases_main_kb())


@router.callback_query(F.data == "cases_main")
async def cb_cases_main(callback: CallbackQuery):
    try:
        await callback.message.edit_text(_cases_main_text(), parse_mode="HTML", reply_markup=_cases_main_kb())
    except Exception:
        await callback.message.answer(_cases_main_text(), parse_mode="HTML", reply_markup=_cases_main_kb())
    await callback.answer()


@router.callback_query(F.data == "cases_shop")
async def cb_cases_shop(callback: CallbackQuery):
    text = (
        "🛍 <b>МАГАЗИН КЕЙСОВ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Выбери кейс для покупки:"
    )
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_shop_kb())
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=_shop_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("cases_view:"))
async def cb_case_view(callback: CallbackQuery):
    case_id = callback.data.split(":")[1]
    case = CASES.get(case_id)
    if not case:
        await callback.answer("❌ Кейс не найден.", show_alert=True)
        return

    drops = DROPS.get(case_id, [])
    total_weight = sum(d["weight"] for d in drops)
    drop_lines = []
    for d in drops:
        pct = round(d["weight"] / total_weight * 100, 1)
        drop_lines.append(f"  {d['label']} — <b>{pct}%</b>")

    prices = []
    if case["price_usd"]:
        prices.append(f"💵 {format_amount(case['price_usd'])}$")
    if case["price_dc"]:
        prices.append(f"💎 {case['price_dc']} DC")

    text = (
        f"{case['name']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷 Редкость: <b>{case['rarity']}</b>\n"
        f"💰 Цена: {' / '.join(prices)}\n\n"
        f"📋 <b>Возможные выпадения:</b>\n"
        + "\n".join(drop_lines)
    )
    kb = _case_buy_kb(case_id, case, callback.from_user.id)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("cases_buy:"))
async def cb_case_buy(callback: CallbackQuery):
    parts = callback.data.split(":")
    case_id = parts[1]
    currency = parts[2]
    qty = int(parts[3]) if len(parts) > 3 else 1
    case = CASES.get(case_id)
    if not case:
        await callback.answer("❌ Кейс не найден.", show_alert=True)
        return

    from donate import is_vip
    from admin_roles import is_admin_any
    user_id = callback.from_user.id
    user = get_user(user_id)

    if qty > 1 and not is_vip(user_id) and not is_admin_any(user_id):
        await callback.answer("❌ Покупка пачкой доступна только VIP!", show_alert=True)
        return

    if currency == "usd":
        price = case["price_usd"]
        if price is None:
            await callback.answer("❌ Недоступно.", show_alert=True)
            return
        total_price = price * qty
        balance = get_balance(user_id)
        if balance < total_price:
            await callback.answer(
                f"❌ Недостаточно средств!\nНужно: {format_amount(total_price)}$\nВаш баланс: {format_amount(balance)}$",
                show_alert=True
            )
            return
        update_balance(user_id, balance - total_price)

    elif currency == "dc":
        price = case["price_dc"]
        if price is None:
            await callback.answer("❌ Недоступно.", show_alert=True)
            return
        total_price = price * qty
        dc = user.get("donate_coins", 0)
        if dc < total_price:
            await callback.answer(
                f"❌ Недостаточно DC!\nНужно: {total_price} DC\nВаших DC: {dc} DC",
                show_alert=True
            )
            return
        user["donate_coins"] = dc - total_price
        save_user_data()
    else:
        await callback.answer("❌ Неизвестная валюта.", show_alert=True)
        return

    for _ in range(qty):
        add_case_to_user(user_id, case_id)

    cname = case["name"]
    qty_text = f" ×{qty}" if qty > 1 else ""
    text = (
        f"✅ <b>Куплено: {cname}{qty_text}!</b>\n\n"
        f"Кейс{'ы' if qty > 1 else ''} добавлены в инвентарь.\n"
        f"Открой в разделе «🎒 Мои кейсы»!"
    )
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎒 Мои кейсы", callback_data="cases_my")],
            [InlineKeyboardButton(text="🛍 Ещё купить", callback_data="cases_shop")],
        ]))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎒 Мои кейсы", callback_data="cases_my")],
            [InlineKeyboardButton(text="🛍 Ещё купить", callback_data="cases_shop")],
        ]))
    await callback.answer()


@router.callback_query(F.data == "cases_my")
async def cb_my_cases(callback: CallbackQuery):
    user_id = callback.from_user.id
    cases = get_user_cases(user_id)
    if cases:
        text = f"🎒 <b>МОИ КЕЙСЫ</b>\n━━━━━━━━━━━━━━━━━━━━\n\nВсего кейсов: <b>{len(cases)}</b>\n\nВыбери кейс для открытия:"
    else:
        text = "🎒 <b>МОИ КЕЙСЫ</b>\n━━━━━━━━━━━━━━━━━━━━\n\nУ тебя нет кейсов. Купи их в магазине!"
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_my_cases_kb(user_id))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=_my_cases_kb(user_id))
    await callback.answer()


@router.callback_query(F.data.startswith("cases_open_menu:"))
async def cb_open_menu(callback: CallbackQuery):
    case_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    cases = get_user_cases(user_id)
    count = sum(1 for c in cases if c.get("case_id") == case_id)
    if count == 0:
        await callback.answer("❌ У тебя нет этого кейса.", show_alert=True)
        return
    cinfo = CASES.get(case_id, {})
    drops = DROPS.get(case_id, [])
    total_w = sum(d["weight"] for d in drops)
    drop_lines = []
    for d in drops:
        pct = round(d["weight"] / total_w * 100, 1)
        drop_lines.append(f"  {d['label']} — {pct}%")

    text = (
        f"{cinfo.get('name', case_id)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎒 У тебя: <b>{count} шт.</b>\n\n"
        f"📋 <b>Возможные выпадения:</b>\n"
        + "\n".join(drop_lines)
    )
    kb = _open_menu_kb(case_id, count, user_id)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("cases_open:"))
async def cb_open_case(callback: CallbackQuery):
    parts = callback.data.split(":")
    case_id = parts[1]
    qty = int(parts[2]) if len(parts) > 2 else 1
    user_id = callback.from_user.id

    from donate import is_vip
    from admin_roles import is_admin_any
    if qty > 1 and not is_vip(user_id) and not is_admin_any(user_id):
        await callback.answer("❌ Открытие пачкой доступно только VIP!", show_alert=True)
        return

    RARITY_ANIM = {
        "unicorn":   "🦄✨",
        "rare":      "🔵💫",
        "epic":      "🟣⚡",
        "legendary": "🟡🔥",
        "donate":    "💎🌟",
    }
    anim = RARITY_ANIM.get(case_id, "✨")
    cinfo = CASES.get(case_id, {})

    if qty == 1:
        if not remove_case_from_user(user_id, case_id):
            await callback.answer("❌ У тебя нет этого кейса.", show_alert=True)
            return
        result = open_case(user_id, case_id)
        drop_text = result.get("text", "Что-то выпало")
        text = (
            f"{anim} <b>КЕЙС ОТКРЫТ!</b> {anim}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Ты открыл: <b>{cinfo.get('name', case_id)}</b>\n\n"
            f"🎁 Выпало:\n{drop_text}"
        )
        answer_text = f"Выпало: {result.get('drop', {}).get('label', '?')}"
    else:
        opened = 0
        drops_summary = {}
        for _ in range(qty):
            if not remove_case_from_user(user_id, case_id):
                break
            result = open_case(user_id, case_id)
            lbl = result.get("drop", {}).get("label", "?")
            drops_summary[lbl] = drops_summary.get(lbl, 0) + 1
            opened += 1
        if opened == 0:
            await callback.answer("❌ У тебя нет этого кейса.", show_alert=True)
            return
        lines = "\n".join(f"  {lbl} ×{cnt}" for lbl, cnt in drops_summary.items())
        text = (
            f"{anim} <b>ОТКРЫТО {opened} КЕЙСОВ!</b> {anim}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Кейс: <b>{cinfo.get('name', case_id)}</b>\n\n"
            f"🎁 Что выпало:\n{lines}"
        )
        answer_text = f"✅ Открыто {opened} кейсов!"

    cases_left = sum(1 for c in get_user_cases(user_id) if c.get("case_id") == case_id)
    kb_rows = []
    if cases_left > 0:
        kb_rows.append([InlineKeyboardButton(
            text=f"🎁 Открыть ещё (осталось {cases_left})",
            callback_data=f"cases_open:{case_id}:1"
        )])
    kb_rows.append([InlineKeyboardButton(text="🎒 Мои кейсы", callback_data="cases_my")])
    kb_rows.append([InlineKeyboardButton(text="🛍 Купить ещё", callback_data="cases_shop")])

    try:
        await callback.message.edit_text(text, parse_mode="HTML",
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML",
                                      reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await callback.answer(answer_text)
