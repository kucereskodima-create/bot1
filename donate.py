import time
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery,
)
from utils import get_user, get_balance, update_balance, save_user_data, format_amount

router = Router()

DC_RATE = 100_000

DC_PACKAGES = [
    {"dc": 10,  "stars": 10,  "label": "10 DC",  "bonus": ""},
    {"dc": 25,  "stars": 25,  "label": "25 DC",  "bonus": ""},
    {"dc": 50,  "stars": 50,  "label": "50 DC",  "bonus": "🔥 +5 DC бонус"},
    {"dc": 100, "stars": 100, "label": "100 DC", "bonus": "🔥 +15 DC бонус"},
    {"dc": 200, "stars": 200, "label": "200 DC", "bonus": "🔥 +40 DC бонус"},
]

DONATE_SELL_RATIO = 0.5

DONATE_BUSINESSES = {
    "casino": {
        "name": "🃏 Казино",
        "dc": 950,
        "virty_price": 2_500_000_000,
        "income_per_hour": 750_000,
        "desc": "Элитное казино с пассивным доходом 750.000$/час. Накапливается без авто-сбора.",
        "sell_price": 750_000_000,
    },
}

DONATE_HOUSES = {
    "whitehouse": {
        "name": "🏛 Белый Дом",
        "dc": 450,
        "virty_price": 800_000_000,
        "farm_boost": 25,
        "desc": "+25% к ферме",
        "sell_price": 250_000_000,
    },
}

DONATE_CARS = {
    "hypercar": {
        "name": "🏎 Formula 1 Hypercar",
        "dc": 1000,
        "virty_price": 1_500_000_000,
        "speed": 420,
        "desc": "Эксклюзивный суперкар Formula 1. Скорость 420 км/ч.",
        "sell_price": 450_000_000,
    },
}

VIP_PRICE_DC = 250
VIP_BONUS_COOLDOWN    = 43200
NONVIP_BONUS_COOLDOWN = 86400
VIP_BONUS_AMOUNT    = 1500
NONVIP_BONUS_AMOUNT = 1000


def get_donate_main_kb(has_vip: bool = False):
    vip_text = "⭐ Мой VIP" if has_vip else "⭐ VIP статус"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить DC (Telegram Stars)", callback_data="donate_buy_dc")],
        [
            InlineKeyboardButton(text=vip_text,             callback_data="donate_vip"),
            InlineKeyboardButton(text="🏢 Бизнес",          callback_data="donate_biz_menu"),
        ],
        [
            InlineKeyboardButton(text="🏠 Дома",            callback_data="donate_houses_menu"),
            InlineKeyboardButton(text="🚗 Авто",            callback_data="donate_cars_menu"),
        ],
        [InlineKeyboardButton(text="📦 Кейсы за DC",        callback_data="donate_cases_menu")],
        [InlineKeyboardButton(text="💵 Магазин за вирты",   callback_data="donate_virty_menu")],
        [InlineKeyboardButton(text="📦 Мои покупки",        callback_data="donate_my_items")],
    ])


def get_dc_packages_kb():
    rows = []
    for i, pkg in enumerate(DC_PACKAGES):
        bonus = f" ({pkg['bonus']})" if pkg["bonus"] else ""
        rows.append([InlineKeyboardButton(
            text=f"💎 {pkg['label']} — {pkg['stars']} ⭐{bonus}",
            callback_data=f"donate_dc_{i}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_biz_menu_kb(owned_biz: str | None = None):
    rows = []
    for key, biz in DONATE_BUSINESSES.items():
        rows.append([InlineKeyboardButton(
            text=f"{biz['name']} — {biz['dc']} DC | {format_amount(biz['income_per_hour'])}$/ч",
            callback_data=f"donate_biz_buy_{key}"
        )])
    if owned_biz and owned_biz in DONATE_BUSINESSES:
        sell_p = DONATE_BUSINESSES[owned_biz]["sell_price"]
        rows.append([InlineKeyboardButton(
            text=f"🔴 Продать {DONATE_BUSINESSES[owned_biz]['name']} за {format_amount(sell_p)}$",
            callback_data=f"donate_biz_sell_{owned_biz}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_houses_menu_kb(owned_house: str | None = None):
    rows = []
    for key, house in DONATE_HOUSES.items():
        rows.append([InlineKeyboardButton(
            text=f"{house['name']} — {house['dc']} DC | {house['desc']}",
            callback_data=f"donate_house_buy_{key}"
        )])
    if owned_house and owned_house in DONATE_HOUSES:
        sell_p = DONATE_HOUSES[owned_house]["sell_price"]
        rows.append([InlineKeyboardButton(
            text=f"🔴 Продать {DONATE_HOUSES[owned_house]['name']} за {format_amount(sell_p)}$",
            callback_data=f"donate_house_sell_{owned_house}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_cars_menu_kb(owned_car: str | None = None):
    rows = []
    for key, car in DONATE_CARS.items():
        rows.append([InlineKeyboardButton(
            text=f"{car['name']} — {car['dc']} DC",
            callback_data=f"donate_car_buy_{key}"
        )])
    if owned_car and owned_car in DONATE_CARS:
        sell_p = DONATE_CARS[owned_car]["sell_price"]
        rows.append([InlineKeyboardButton(
            text=f"🔴 Продать {DONATE_CARS[owned_car]['name']} за {format_amount(sell_p)}$",
            callback_data=f"donate_car_sell_{owned_car}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_main")]
    ])


def get_donate_user_data(user):
    if "donate" not in user:
        user["donate"] = {
            "vip": False,
            "business": None,
            "biz_last_collect": None,
            "house": None,
            "car": None,
        }
        save_user_data()
    return user["donate"]


def accumulate_biz_income(user_id: int) -> int:
    user = get_user(user_id)
    d = get_donate_user_data(user)
    biz_key = d.get("business")
    if not biz_key or biz_key not in DONATE_BUSINESSES:
        if biz_key and biz_key not in DONATE_BUSINESSES:
            d["business"] = "casino"
            save_user_data()
            biz_key = "casino"
        else:
            return 0
    now = int(time.time())
    last = d.get("biz_last_collect") or now
    elapsed_hours = (now - last) / 3600
    income_per_hour = DONATE_BUSINESSES[biz_key]["income_per_hour"]
    multiplier = 1.10 if d.get("vip") else 1.0
    income = int(elapsed_hours * income_per_hour * multiplier)
    return income


def collect_biz_income(user_id: int) -> int:
    user = get_user(user_id)
    d = get_donate_user_data(user)
    biz_key = d.get("business")
    if not biz_key or biz_key not in DONATE_BUSINESSES:
        if biz_key and biz_key not in DONATE_BUSINESSES:
            d["business"] = "casino"
            save_user_data()
            biz_key = "casino"
        else:
            return 0
    now = int(time.time())
    last = d.get("biz_last_collect") or now
    elapsed_hours = (now - last) / 3600
    income_per_hour = DONATE_BUSINESSES[biz_key]["income_per_hour"]
    multiplier = 1.10 if d.get("vip") else 1.0
    income = int(elapsed_hours * income_per_hour * multiplier)
    if income > 0:
        update_balance(user_id, get_balance(user_id) + income)
        d["biz_last_collect"] = now
        save_user_data()
    return income


def get_farm_boost_pct(user_id: int) -> float:
    user = get_user(user_id)
    d = get_donate_user_data(user)
    house_key = d.get("house")
    if not house_key or house_key not in DONATE_HOUSES:
        return 0.0
    return float(DONATE_HOUSES[house_key].get("farm_boost", 0))


def get_work_boost_pct(user_id: int) -> float:
    user = get_user(user_id)
    d = get_donate_user_data(user)
    house_key = d.get("house")
    if not house_key or house_key not in DONATE_HOUSES:
        return 0.0
    return float(DONATE_HOUSES[house_key].get("work_boost", 0))


def get_bonus_boost_pct(user_id: int) -> float:
    user = get_user(user_id)
    d = get_donate_user_data(user)
    house_key = d.get("house")
    if not house_key or house_key not in DONATE_HOUSES:
        return 0.0
    return float(DONATE_HOUSES[house_key].get("bonus_boost", 0))


def is_vip(user_id: int) -> bool:
    user = get_user(user_id)
    d = get_donate_user_data(user)
    return bool(d.get("vip", False))


def vip_clan_hourly_rating():
    """Начисляет +10 рейтинга клану за каждого VIP-участника раз в час."""
    import json, os
    from utils import user_data
    CLANS_FILE = os.path.join(os.path.dirname(__file__), "clans.json")
    if not os.path.exists(CLANS_FILE):
        return
    try:
        with open(CLANS_FILE, "r", encoding="utf-8") as f:
            clans_data = json.load(f)
    except Exception:
        return
    changed = False
    for uid_str, udata in user_data.items():
        d = udata.get("donate", {})
        if not d.get("vip"):
            continue
        clan_id = udata.get("clan_id")
        if not clan_id or clan_id not in clans_data:
            continue
        clans_data[clan_id]["rating"] = clans_data[clan_id].get("rating", 0) + 10
        changed = True
    if changed:
        with open(CLANS_FILE, "w", encoding="utf-8") as f:
            json.dump(clans_data, f, ensure_ascii=False, indent=2)


def auto_collect_all_businesses():
    """Доход накапливается — авто-сбор отключён, игрок собирает вручную."""
    pass


VIP_BOOSTS_TEXT = (
    "⭐ <b>VIP СТАТУС</b> — 250 DC\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "🏆 <b>Привилегии VIP:</b>\n\n"
    "1) 🎈 Уникальная отметка ⭐ в профиле\n"
    "2) 💸 Лимит перевода до <b>10.000.000$</b>\n"
    "3) 🎁 Бонус каждые <b>12 часов</b> (+500$ к сумме)\n"
    "4) 🛠 Зарплата на работе <b>×1.50</b>\n"
    "5) 👥 Награда за рефералов <b>+50%</b>\n"
    "6) 🏖 Прибыль бизнеса <b>+10%</b>\n"
    "7) 🎉 Доступ к проведению розыгрышей\n"
    "8) 👒 Клан получает <b>+10 рейтинга</b> каждый час"
)

VIP_MY_TEXT = (
    "⭐ <b>ВАШ VIP СТАТУС АКТИВЕН</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "✅ Все привилегии активны:\n\n"
    "1) 🎈 Отметка ⭐ в профиле — <b>активна</b>\n"
    "2) 💸 Лимит перевода <b>10.000.000$</b> — <b>активен</b>\n"
    "3) 🎁 Бонус каждые 12 часов — <b>активен</b>\n"
    "4) 🛠 Зарплата ×1.50 — <b>активна</b>\n"
    "5) 👥 Рефералы +50% — <b>активно</b>\n"
    "6) 🏖 Бизнес +10% — <b>активно</b>\n"
    "7) 🎉 Розыгрыши — <b>доступны</b>\n"
    "8) 👒 Клан +10 рейтинга/ч — <b>активно</b>"
)


def donate_menu_text():
    return (
        "💎 <b>ДОНАТ МАГАЗИН</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💰 <b>Курс:</b> 1 DC = 1 ⭐ Star = 100.000$\n\n"
        "Здесь ты можешь купить эксклюзивные предметы\n"
        "за Donate Coins (DC), которые покупаются\n"
        "через <b>Telegram Stars ⭐</b>\n\n"
        "📦 <b>Категории:</b>\n"
        "• 💎 Пополнить DC баланс\n"
        "• 🧧 VIP статус — 8 уникальных привилегий\n"
        "• 🏢 Бизнес — автоматический доход\n"
        "• 🏠 Дом — буст к ферме\n"
        "• 🚗 Авто — эксклюзивный суперкар\n"
        "• 📦 Кейсы — донат кейсы с топовыми дропами"
    )


@router.message(F.text.lower().in_(["💎 донат", "донат", "donate", "донат магазин"]))
async def cmd_donate(message: Message):
    user = get_user(message.from_user.id)
    d    = get_donate_user_data(user)
    dc   = user.get("donate_coins", 0)
    text = donate_menu_text() + f"\n\n💎 <b>Ваш DC баланс:</b> {dc} DC"
    await message.answer(text, reply_markup=get_donate_main_kb(has_vip=bool(d.get("vip"))), parse_mode="HTML")


@router.callback_query(F.data == "donate_main")
async def cb_donate_main(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    d    = get_donate_user_data(user)
    dc   = user.get("donate_coins", 0)
    text = donate_menu_text() + f"\n\n💎 <b>Ваш DC баланс:</b> {dc} DC"
    await callback.message.edit_text(text, reply_markup=get_donate_main_kb(has_vip=bool(d.get("vip"))), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "donate_buy_dc")
async def cb_donate_buy_dc(callback: CallbackQuery):
    text = (
        "💎 <b>КУПИТЬ DONATE COINS (DC)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Оплата через <b>Telegram Stars ⭐</b>\n"
        "1 DC = 100.000$ игровых денег\n\n"
        "Выберите пакет:"
    )
    await callback.message.edit_text(text, reply_markup=get_dc_packages_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("donate_dc_"))
async def cb_donate_dc_buy(callback: CallbackQuery):
    idx = int(callback.data.replace("donate_dc_", ""))
    if idx < 0 or idx >= len(DC_PACKAGES):
        await callback.answer("Пакет не найден.", show_alert=True)
        return
    pkg = DC_PACKAGES[idx]
    bonus_text = f"\n🎁 Бонус: {pkg['bonus']}" if pkg["bonus"] else ""
    from config import bot
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"💎 {pkg['label']}",
        description=f"Покупка {pkg['dc']} Donate Coins для игры.{bonus_text}",
        payload=f"dc_pkg_{idx}",
        currency="XTR",
        prices=[LabeledPrice(label=f"{pkg['label']}", amount=pkg["stars"])],
    )
    await callback.answer()


@router.callback_query(F.data == "donate_vip")
async def cb_donate_vip(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    d = get_donate_user_data(user)
    dc = user.get("donate_coins", 0)

    if d.get("vip"):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_main")],
        ])
        await callback.message.edit_text(
            VIP_MY_TEXT,
            reply_markup=kb, parse_mode="HTML"
        )
        await callback.answer()
        return

    text = (
        f"{VIP_BOOSTS_TEXT}\n\n"
        f"💎 <b>Цена: {VIP_PRICE_DC} DC</b>\n"
        f"💎 Ваш баланс: {dc} DC"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Купить VIP за {VIP_PRICE_DC} DC", callback_data="donate_vip_confirm")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_main")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "donate_vip_confirm")
async def cb_donate_vip_confirm(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    d = get_donate_user_data(user)

    if d.get("vip"):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_main")],
        ])
        await callback.message.edit_text(VIP_MY_TEXT, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        return

    dc = user.get("donate_coins", 0)
    if dc < VIP_PRICE_DC:
        await callback.answer(
            f"❌ Недостаточно DC!\nНужно: {VIP_PRICE_DC} DC\nУ вас: {dc} DC",
            show_alert=True
        )
        return

    user["donate_coins"] = dc - VIP_PRICE_DC
    d["vip"] = True
    save_user_data()
    await callback.message.edit_text(
        "⭐ <b>VIP СТАТУС АКТИВИРОВАН!</b>\n\n"
        "Поздравляем! Теперь у вас есть значок ⭐ VIP\n"
        "и все привилегии премиум игрока.\n\n"
        f"{VIP_MY_TEXT}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Мои покупки", callback_data="donate_my_items")],
            [InlineKeyboardButton(text="⬅️ В меню",      callback_data="donate_main")],
        ]),
        parse_mode="HTML"
    )
    await callback.answer("⭐ VIP активирован!")


@router.callback_query(F.data == "donate_biz_menu")
async def cb_donate_biz_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    d = get_donate_user_data(user)
    dc = user.get("donate_coins", 0)
    current = d.get("business")
    current_name = DONATE_BUSINESSES[current]["name"] if current else "Нет"

    text = (
        "🏢 <b>ДОНАТ БИЗНЕСЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Бизнесы приносят автоматический доход каждый час.\n"
        "Можно иметь только <b>1 бизнес</b> одновременно.\n\n"
        f"💎 Ваш DC: {dc} DC\n"
        f"🏢 Текущий бизнес: {current_name}\n\n"
        "<b>Доступные бизнесы:</b>"
    )
    await callback.message.edit_text(text, reply_markup=get_biz_menu_kb(current), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("donate_biz_buy_"))
async def cb_donate_biz_buy(callback: CallbackQuery):
    user_id = callback.from_user.id
    key = callback.data.replace("donate_biz_buy_", "")
    if key not in DONATE_BUSINESSES:
        await callback.answer("Бизнес не найден.", show_alert=True)
        return

    user = get_user(user_id)
    d = get_donate_user_data(user)
    biz = DONATE_BUSINESSES[key]
    dc = user.get("donate_coins", 0)
    current = d.get("business")

    if current == key:
        income = accumulate_biz_income(user_id)
        sell_p = biz.get("sell_price", 0)
        biz_rows = [[InlineKeyboardButton(text=f"💰 Собрать {format_amount(income)}$", callback_data=f"donate_biz_collect_{key}")]]
        biz_rows.append([InlineKeyboardButton(text=f"🔴 Продать за {format_amount(sell_p)}$", callback_data=f"donate_biz_sell_{key}")])
        biz_rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_biz_menu")])
        await callback.message.edit_text(
            f"🏢 <b>{biz['name']}</b>\n\n"
            f"📝 {biz.get('desc', '')}\n\n"
            f"✅ Этот бизнес уже у вас!\n"
            f"💵 Доход: {format_amount(biz['income_per_hour'])}$/час\n"
            f"💰 Накопилось: <b>{format_amount(income)}$</b>\n"
            f"🔴 Цена продажи: <b>{format_amount(sell_p)}$</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=biz_rows), parse_mode="HTML"
        )
        await callback.answer()
        return

    if dc < biz["dc"]:
        await callback.answer(
            f"❌ Недостаточно DC!\nНужно: {biz['dc']} DC\nУ вас: {dc} DC",
            show_alert=True
        )
        return

    replace_text = ""
    if current and current in DONATE_BUSINESSES:
        replace_text = f"\n⚠️ Ваш бизнес «{DONATE_BUSINESSES[current]['name']}» будет заменён!"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Купить за {biz['dc']} DC", callback_data=f"donate_biz_confirm_{key}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_biz_menu")],
    ])
    await callback.message.edit_text(
        f"{biz['name']}\n\n"
        f"💵 Доход: {format_amount(biz['income_per_hour'])}$/час\n"
        f"💎 Цена: {biz['dc']} DC{replace_text}\n"
        f"💎 Ваш баланс: {dc} DC",
        reply_markup=kb, parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("donate_biz_confirm_"))
async def cb_donate_biz_confirm(callback: CallbackQuery):
    user_id = callback.from_user.id
    key = callback.data.replace("donate_biz_confirm_", "")
    if key not in DONATE_BUSINESSES:
        await callback.answer("Ошибка.", show_alert=True)
        return

    user = get_user(user_id)
    d = get_donate_user_data(user)
    biz = DONATE_BUSINESSES[key]
    dc = user.get("donate_coins", 0)

    if dc < biz["dc"]:
        await callback.answer("❌ Недостаточно DC!", show_alert=True)
        return

    user["donate_coins"] = dc - biz["dc"]
    old_biz = d.get("business")
    d["business"] = key
    d["biz_last_collect"] = int(time.time())
    save_user_data()

    extra = ""
    if old_biz and old_biz in DONATE_BUSINESSES:
        extra = f"\nПрежний бизнес «{DONATE_BUSINESSES[old_biz]['name']}» продан."

    await callback.message.edit_text(
        f"✅ <b>Бизнес куплен!</b>\n\n"
        f"{biz['name']}\n"
        f"💵 Доход: {format_amount(biz['income_per_hour'])}$/час\n"
        f"Доход начисляется автоматически каждый час.{extra}",
        reply_markup=get_back_kb(), parse_mode="HTML"
    )
    await callback.answer("✅ Бизнес активирован!")


@router.callback_query(F.data.startswith("donate_biz_collect_"))
async def cb_donate_biz_collect(callback: CallbackQuery):
    user_id = callback.from_user.id
    key = callback.data.replace("donate_biz_collect_", "")
    user = get_user(user_id)
    d = get_donate_user_data(user)

    if d.get("business") != key:
        await callback.answer("Этот бизнес не ваш.", show_alert=True)
        return

    income = collect_biz_income(user_id)
    if income <= 0:
        await callback.answer("Ещё не накопился доход. Приходите позже!", show_alert=True)
        return

    biz = DONATE_BUSINESSES[key]
    await callback.message.edit_text(
        f"💰 <b>Доход собран!</b>\n\n"
        f"{biz['name']}\n"
        f"Вы получили: <b>+{format_amount(income)}$</b>",
        reply_markup=get_back_kb(), parse_mode="HTML"
    )
    await callback.answer(f"💰 +{format_amount(income)}$!")


@router.callback_query(F.data == "donate_houses_menu")
async def cb_donate_houses_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    d = get_donate_user_data(user)
    dc = user.get("donate_coins", 0)
    current = d.get("house")
    current_name = DONATE_HOUSES[current]["name"] if current else "Нет"

    text = (
        "🏠 <b>ДОНАТ ДОМА</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Каждый дом даёт постоянный буст к игре.\n"
        "Можно иметь только <b>1 дом</b> одновременно.\n\n"
        f"💎 Ваш DC: {dc} DC\n"
        f"🏠 Текущий дом: {current_name}\n\n"
        "<b>Доступные дома:</b>"
    )
    await callback.message.edit_text(text, reply_markup=get_houses_menu_kb(current), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("donate_house_buy_"))
async def cb_donate_house_buy(callback: CallbackQuery):
    user_id = callback.from_user.id
    key = callback.data.replace("donate_house_buy_", "")
    if key not in DONATE_HOUSES:
        await callback.answer("Дом не найден.", show_alert=True)
        return

    user = get_user(user_id)
    d = get_donate_user_data(user)
    house = DONATE_HOUSES[key]
    dc = user.get("donate_coins", 0)
    current = d.get("house")

    if current == key:
        sell_p = house.get("sell_price", 0)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🔴 Продать за {format_amount(sell_p)}$", callback_data=f"donate_house_sell_{key}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_houses_menu")],
        ])
        await callback.message.edit_text(
            f"🏠 <b>{house['name']}</b>\n\n"
            f"✅ Этот дом уже у вас!\n"
            f"✨ Эффект: {house['desc']}\n"
            f"🔴 Цена продажи: <b>{format_amount(sell_p)}$</b>",
            reply_markup=kb, parse_mode="HTML"
        )
        await callback.answer()
        return

    if dc < house["dc"]:
        await callback.answer(
            f"❌ Недостаточно DC!\nНужно: {house['dc']} DC\nУ вас: {dc} DC",
            show_alert=True
        )
        return

    replace_text = ""
    if current and current in DONATE_HOUSES:
        replace_text = f"\n⚠️ Ваш дом «{DONATE_HOUSES[current]['name']}» будет заменён!"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Купить за {house['dc']} DC", callback_data=f"donate_house_confirm_{key}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_houses_menu")],
    ])
    await callback.message.edit_text(
        f"{house['name']}\n\n"
        f"✨ Эффект: {house['desc']}\n"
        f"💎 Цена: {house['dc']} DC{replace_text}\n"
        f"💎 Ваш баланс: {dc} DC",
        reply_markup=kb, parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("donate_house_confirm_"))
async def cb_donate_house_confirm(callback: CallbackQuery):
    user_id = callback.from_user.id
    key = callback.data.replace("donate_house_confirm_", "")
    if key not in DONATE_HOUSES:
        await callback.answer("Ошибка.", show_alert=True)
        return

    user = get_user(user_id)
    d = get_donate_user_data(user)
    house = DONATE_HOUSES[key]
    dc = user.get("donate_coins", 0)

    if dc < house["dc"]:
        await callback.answer("❌ Недостаточно DC!", show_alert=True)
        return

    user["donate_coins"] = dc - house["dc"]
    old_house = d.get("house")
    d["house"] = key
    save_user_data()

    extra = ""
    if old_house and old_house in DONATE_HOUSES:
        extra = f"\nПрежний дом «{DONATE_HOUSES[old_house]['name']}» продан."

    await callback.message.edit_text(
        f"✅ <b>Дом куплен!</b>\n\n"
        f"{house['name']}\n"
        f"✨ Эффект: <b>{house['desc']}</b>\n"
        f"Буст активирован немедленно!{extra}",
        reply_markup=get_back_kb(), parse_mode="HTML"
    )
    await callback.answer("✅ Дом куплен!")


@router.callback_query(F.data == "donate_cars_menu")
async def cb_donate_cars_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    d = get_donate_user_data(user)
    dc = user.get("donate_coins", 0)
    current = d.get("car")
    current_name = DONATE_CARS[current]["name"] if current else "Нет"

    text = (
        "🚗 <b>ДОНАТ АВТО</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Эксклюзивные суперкары, недоступные в обычном магазине.\n\n"
        f"💎 Ваш DC: {dc} DC\n"
        f"🚗 Текущее авто: {current_name}\n\n"
        "<b>Доступные авто:</b>"
    )
    await callback.message.edit_text(text, reply_markup=get_cars_menu_kb(current), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("donate_car_buy_"))
async def cb_donate_car_buy(callback: CallbackQuery):
    user_id = callback.from_user.id
    key = callback.data.replace("donate_car_buy_", "")
    if key not in DONATE_CARS:
        await callback.answer("Авто не найдено.", show_alert=True)
        return

    user = get_user(user_id)
    d = get_donate_user_data(user)
    car = DONATE_CARS[key]
    dc = user.get("donate_coins", 0)
    current = d.get("car")

    if current == key:
        sell_p = car.get("sell_price", 0)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🔴 Продать за {format_amount(sell_p)}$", callback_data=f"donate_car_sell_{key}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_cars_menu")],
        ])
        speed_line = f"\n⚡ Скорость: {car['speed']} км/ч" if car.get("speed") else ""
        await callback.message.edit_text(
            f"🚗 <b>{car['name']}</b>{speed_line}\n\n"
            f"📝 {car.get('desc', '')}\n\n"
            f"✅ Это авто уже у вас!\n"
            f"🔴 Цена продажи: <b>{format_amount(sell_p)}$</b>",
            reply_markup=kb, parse_mode="HTML"
        )
        await callback.answer()
        return

    if dc < car["dc"]:
        await callback.answer(
            f"❌ Недостаточно DC!\nНужно: {car['dc']} DC\nУ вас: {dc} DC",
            show_alert=True
        )
        return

    replace_text = ""
    if current and current in DONATE_CARS:
        replace_text = f"\n⚠️ Ваше авто «{DONATE_CARS[current]['name']}» будет заменено!"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Купить за {car['dc']} DC", callback_data=f"donate_car_confirm_{key}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_cars_menu")],
    ])
    speed_line = f"\n⚡ Скорость: {car['speed']} км/ч" if car.get("speed") else ""
    await callback.message.edit_text(
        f"{car['name']}{speed_line}\n\n"
        f"💎 Цена: {car['dc']} DC{replace_text}\n"
        f"💎 Ваш баланс: {dc} DC",
        reply_markup=kb, parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("donate_car_confirm_"))
async def cb_donate_car_confirm(callback: CallbackQuery):
    user_id = callback.from_user.id
    key = callback.data.replace("donate_car_confirm_", "")
    if key not in DONATE_CARS:
        await callback.answer("Ошибка.", show_alert=True)
        return

    user = get_user(user_id)
    d = get_donate_user_data(user)
    car = DONATE_CARS[key]
    dc = user.get("donate_coins", 0)

    if dc < car["dc"]:
        await callback.answer("❌ Недостаточно DC!", show_alert=True)
        return

    user["donate_coins"] = dc - car["dc"]
    old_car = d.get("car")
    d["car"] = key
    save_user_data()

    extra = ""
    if old_car and old_car in DONATE_CARS:
        extra = f"\nПрежнее авто «{DONATE_CARS[old_car]['name']}» продано."

    await callback.message.edit_text(
        f"✅ <b>Авто куплено!</b>\n\n"
        f"{car['name']}\n"
        f"Эксклюзив теперь ваш!{extra}",
        reply_markup=get_back_kb(), parse_mode="HTML"
    )
    await callback.answer("✅ Авто куплено!")


@router.callback_query(F.data.startswith("donate_biz_sell_"))
async def cb_donate_biz_sell(callback: CallbackQuery):
    user_id = callback.from_user.id
    key = callback.data.replace("donate_biz_sell_", "")
    user = get_user(user_id)
    d = get_donate_user_data(user)

    if d.get("business") != key or key not in DONATE_BUSINESSES:
        await callback.answer("❌ Этот бизнес вам не принадлежит.", show_alert=True)
        return

    biz = DONATE_BUSINESSES[key]
    income = collect_biz_income(user_id)
    sell_p = biz.get("sell_price", 0)

    update_balance(user_id, get_balance(user_id) + sell_p)
    d["business"] = None
    d["biz_last_collect"] = None
    save_user_data()

    extra = f"\n💵 + накопленная прибыль: <b>{format_amount(income)}$</b>" if income > 0 else ""
    await callback.message.edit_text(
        f"🔴 <b>{biz['name']} продан!</b>\n\n"
        f"💰 Получено: <b>{format_amount(sell_p)}$</b>{extra}\n\n"
        f"🏢 Бизнес: <b>Нет</b>",
        reply_markup=get_back_kb(), parse_mode="HTML"
    )
    await callback.answer(f"🔴 Продано за {format_amount(sell_p)}$!")


@router.callback_query(F.data.startswith("donate_house_sell_"))
async def cb_donate_house_sell(callback: CallbackQuery):
    user_id = callback.from_user.id
    key = callback.data.replace("donate_house_sell_", "")
    user = get_user(user_id)
    d = get_donate_user_data(user)

    if d.get("house") != key or key not in DONATE_HOUSES:
        await callback.answer("❌ Этот дом вам не принадлежит.", show_alert=True)
        return

    house = DONATE_HOUSES[key]
    sell_p = house.get("sell_price", 0)

    update_balance(user_id, get_balance(user_id) + sell_p)
    d["house"] = None
    save_user_data()

    await callback.message.edit_text(
        f"🔴 <b>{house['name']} продан!</b>\n\n"
        f"💰 Получено: <b>{format_amount(sell_p)}$</b>\n\n"
        f"🏠 Дом: <b>Нет</b>",
        reply_markup=get_back_kb(), parse_mode="HTML"
    )
    await callback.answer(f"🔴 Продано за {format_amount(sell_p)}$!")


@router.callback_query(F.data.startswith("donate_car_sell_"))
async def cb_donate_car_sell(callback: CallbackQuery):
    user_id = callback.from_user.id
    key = callback.data.replace("donate_car_sell_", "")
    user = get_user(user_id)
    d = get_donate_user_data(user)

    if d.get("car") != key or key not in DONATE_CARS:
        await callback.answer("❌ Это авто вам не принадлежит.", show_alert=True)
        return

    car = DONATE_CARS[key]
    sell_p = car.get("sell_price", 0)

    update_balance(user_id, get_balance(user_id) + sell_p)
    d["car"] = None
    save_user_data()

    await callback.message.edit_text(
        f"🔴 <b>{car['name']} продан!</b>\n\n"
        f"💰 Получено: <b>{format_amount(sell_p)}$</b>\n\n"
        f"🚗 Авто: <b>Нет</b>",
        reply_markup=get_back_kb(), parse_mode="HTML"
    )
    await callback.answer(f"🔴 Продано за {format_amount(sell_p)}$!")


@router.callback_query(F.data == "donate_cases_menu")
async def cb_donate_cases_menu(callback: CallbackQuery):
    from cases import CASES
    user_id = callback.from_user.id
    user = get_user(user_id)
    dc = user.get("donate_coins", 0)

    donate_cases = {k: v for k, v in CASES.items() if v.get("price_dc") is not None}
    rows = []
    for cid, cinfo in donate_cases.items():
        rows.append([InlineKeyboardButton(
            text=f"{cinfo['name']} — {cinfo['price_dc']} DC",
            callback_data=f"donate_case_buy:{cid}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_main")])

    text = (
        "📦 <b>КЕЙСЫ ЗА DC</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 Ваш DC баланс: <b>{dc} DC</b>\n\n"
        "Донат кейсы содержат самые редкие награды:\n"
        "деньги до 20.000.000$, BTC до 1.5, Bugatti,\n"
        "Замок, Винты и DC!\n\n"
        "Выберите кейс:"
    )
    try:
        await callback.message.edit_text(text, parse_mode="HTML",
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML",
                                      reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("donate_case_buy:"))
async def cb_donate_case_buy(callback: CallbackQuery):
    from cases import CASES, add_case_to_user
    case_id = callback.data.split(":")[1]
    case = CASES.get(case_id)
    if not case or case.get("price_dc") is None:
        await callback.answer("❌ Кейс не найден.", show_alert=True)
        return

    user_id = callback.from_user.id
    user = get_user(user_id)
    dc = user.get("donate_coins", 0)
    price = case["price_dc"]

    if dc < price:
        await callback.answer(
            f"❌ Недостаточно DC!\nНужно: {price} DC\nВаших DC: {dc} DC",
            show_alert=True
        )
        return

    user["donate_coins"] = dc - price
    save_user_data()
    add_case_to_user(user_id, case_id)

    text = (
        f"✅ <b>Кейс куплен!</b>\n\n"
        f"{case['name']} добавлен в инвентарь.\n"
        f"💎 Остаток DC: <b>{user['donate_coins']} DC</b>\n\n"
        f"Открой кейс в разделе «📦 Кейсы»!"
    )
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Открыть кейсы", callback_data="cases_main")],
            [InlineKeyboardButton(text="⬅️ Назад в донат", callback_data="donate_main")],
        ]))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Открыть кейсы", callback_data="cases_main")],
            [InlineKeyboardButton(text="⬅️ Назад в донат", callback_data="donate_main")],
        ]))
    await callback.answer()


@router.callback_query(F.data == "donate_my_items")
async def cb_donate_my_items(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    d = get_donate_user_data(user)
    dc = user.get("donate_coins", 0)

    biz_key = d.get("business")
    biz_name = DONATE_BUSINESSES[biz_key]["name"] if biz_key else "Нет"
    biz_income = accumulate_biz_income(user_id) if biz_key else 0
    biz_rate = DONATE_BUSINESSES[biz_key]["income_per_hour"] if biz_key else 0
    biz_sell_p = DONATE_BUSINESSES[biz_key].get("sell_price", 0) if biz_key else 0

    house_key = d.get("house")
    house_name = DONATE_HOUSES[house_key]["name"] if house_key else "Нет"
    house_desc = DONATE_HOUSES[house_key]["desc"] if house_key else ""
    house_sell_p = DONATE_HOUSES[house_key].get("sell_price", 0) if house_key else 0

    car_key = d.get("car")
    car_name = DONATE_CARS[car_key]["name"] if car_key else "Нет"
    car_sell_p = DONATE_CARS[car_key].get("sell_price", 0) if car_key else 0

    vip_str = "⭐ VIP" if d.get("vip") else "Нет"

    rows = []
    if biz_key and biz_income > 0:
        rows.append([InlineKeyboardButton(
            text=f"💰 Собрать {format_amount(biz_income)}$",
            callback_data=f"donate_biz_collect_{biz_key}"
        )])
    if biz_key:
        rows.append([InlineKeyboardButton(
            text=f"🔴 Продать бизнес за {format_amount(biz_sell_p)}$",
            callback_data=f"donate_biz_sell_{biz_key}"
        )])
    if house_key:
        rows.append([InlineKeyboardButton(
            text=f"🔴 Продать дом за {format_amount(house_sell_p)}$",
            callback_data=f"donate_house_sell_{house_key}"
        )])
    if car_key:
        rows.append([InlineKeyboardButton(
            text=f"🔴 Продать авто за {format_amount(car_sell_p)}$",
            callback_data=f"donate_car_sell_{car_key}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_main")])

    text = (
        "📦 <b>МОИ ДОНАТ ПОКУПКИ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 DC баланс: <b>{dc} DC</b>\n\n"
        f"⭐ VIP: <b>{vip_str}</b>\n"
        f"🏢 Бизнес: <b>{biz_name}</b>"
    )
    if biz_key:
        text += f"\n   └ Доход: {format_amount(biz_rate)}$/ч | Накоплено: {format_amount(biz_income)}$"
        text += f"\n   └ Цена продажи: {format_amount(biz_sell_p)}$"
    text += f"\n🏠 Дом: <b>{house_name}</b>"
    if house_desc:
        text += f"\n   └ Эффект: {house_desc}"
        text += f"\n   └ Цена продажи: {format_amount(house_sell_p)}$"
    text += f"\n🚗 Авто: <b>{car_name}</b>"
    if car_key:
        text += f"\n   └ Цена продажи: {format_amount(car_sell_p)}$"

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML"
    )
    await callback.answer()


# ─── Магазин за вирты (игровые деньги $) ─────────────────────────────────────

def _virty_menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🏢 Бизнес за вирты",  callback_data="virty_biz_menu")],
        [InlineKeyboardButton(text="🏠 Дома за вирты",    callback_data="virty_house_menu")],
        [InlineKeyboardButton(text="🚗 Авто за вирты",    callback_data="virty_car_menu")],
        [InlineKeyboardButton(text="⬅️ Назад",             callback_data="donate_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "donate_virty_menu")
async def cb_donate_virty_menu(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    bal  = get_balance(callback.from_user.id)
    text = (
        "💵 <b>МАГАЗИН ЗА ВИРТЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Здесь ты можешь купить донат-имущество\n"
        "за обычные игровые деньги (виртуальные $).\n\n"
        f"💰 <b>Ваш баланс:</b> {format_amount(bal)}$\n\n"
        "📦 <b>Категории:</b>\n"
        "• 🏢 Бизнес — пассивный доход\n"
        "• 🏠 Дом — буст к ферме\n"
        "• 🚗 Авто — эксклюзивный суперкар"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_virty_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "virty_biz_menu")
async def cb_virty_biz_menu(callback: CallbackQuery):
    user   = get_user(callback.from_user.id)
    d      = get_donate_user_data(user)
    bal    = get_balance(callback.from_user.id)
    current = d.get("business")
    rows = []
    for key, biz in DONATE_BUSINESSES.items():
        price = biz.get("virty_price", 0)
        owned = "✅ " if current == key else ""
        rows.append([InlineKeyboardButton(
            text=f"{owned}{biz['name']} — {format_amount(price)}$",
            callback_data=f"virty_biz_buy:{key}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_virty_menu")])
    text = (
        "🏢 <b>БИЗНЕСЫ ЗА ВИРТЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Бизнесы приносят автоматический доход каждый час.\n"
        f"💰 Ваш баланс: <b>{format_amount(bal)}$</b>\n\n"
        "<b>Доступные бизнесы:</b>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("virty_biz_buy:"))
async def cb_virty_biz_buy(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    if key not in DONATE_BUSINESSES:
        await callback.answer("❌ Бизнес не найден.", show_alert=True); return
    user   = get_user(callback.from_user.id)
    d      = get_donate_user_data(user)
    biz    = DONATE_BUSINESSES[key]
    price  = biz.get("virty_price", 0)
    bal    = get_balance(callback.from_user.id)
    current = d.get("business")
    if current == key:
        income = accumulate_biz_income(callback.from_user.id)
        rows = [
            [InlineKeyboardButton(text=f"💰 Собрать {format_amount(income)}$", callback_data=f"donate_biz_collect_{key}")],
            [InlineKeyboardButton(text=f"🔴 Продать за {format_amount(biz.get('sell_price',0))}$", callback_data=f"donate_biz_sell_{key}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="virty_biz_menu")],
        ]
        await callback.message.edit_text(
            f"🏢 <b>{biz['name']}</b>\n\n✅ Этот бизнес уже у вас!\n"
            f"💵 Доход: {format_amount(biz['income_per_hour'])}$/час\n"
            f"💰 Накоплено: <b>{format_amount(income)}$</b>",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        await callback.answer(); return
    if bal < price:
        await callback.answer(f"❌ Недостаточно денег!\nНужно: {format_amount(price)}$\nУ вас: {format_amount(bal)}$", show_alert=True); return
    replace_text = f"\n⚠️ Ваш бизнес «{DONATE_BUSINESSES[current]['name']}» будет заменён!" if current and current in DONATE_BUSINESSES else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Купить за {format_amount(price)}$", callback_data=f"virty_biz_confirm:{key}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="virty_biz_menu")],
    ])
    await callback.message.edit_text(
        f"🏢 <b>{biz['name']}</b>\n\n{biz.get('desc','')}\n"
        f"💵 Доход: {format_amount(biz['income_per_hour'])}$/час\n"
        f"💰 Цена: <b>{format_amount(price)}$</b>{replace_text}\n"
        f"💰 Ваш баланс: {format_amount(bal)}$",
        parse_mode="HTML", reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data.startswith("virty_biz_confirm:"))
async def cb_virty_biz_confirm(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    if key not in DONATE_BUSINESSES:
        await callback.answer("❌", show_alert=True); return
    user   = get_user(callback.from_user.id)
    d      = get_donate_user_data(user)
    biz    = DONATE_BUSINESSES[key]
    price  = biz.get("virty_price", 0)
    bal    = get_balance(callback.from_user.id)
    if bal < price:
        await callback.answer("❌ Недостаточно денег!", show_alert=True); return
    update_balance(callback.from_user.id, bal - price)
    old_biz = d.get("business")
    d["business"] = key
    d["biz_last_collect"] = int(time.time())
    save_user_data()
    extra = f"\nПрежний бизнес «{DONATE_BUSINESSES[old_biz]['name']}» продан." if old_biz and old_biz in DONATE_BUSINESSES else ""
    await callback.message.edit_text(
        f"✅ <b>Бизнес куплен за вирты!</b>\n\n{biz['name']}\n"
        f"💵 Доход: {format_amount(biz['income_per_hour'])}$/час\nДоход начисляется каждый час.{extra}",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В магазин", callback_data="donate_virty_menu")],
        ])
    )
    await callback.answer("✅ Куплено!")


@router.callback_query(F.data == "virty_house_menu")
async def cb_virty_house_menu(callback: CallbackQuery):
    user   = get_user(callback.from_user.id)
    d      = get_donate_user_data(user)
    bal    = get_balance(callback.from_user.id)
    current = d.get("house")
    rows = []
    for key, house in DONATE_HOUSES.items():
        price = house.get("virty_price", 0)
        owned = "✅ " if current == key else ""
        rows.append([InlineKeyboardButton(
            text=f"{owned}{house['name']} — {format_amount(price)}$",
            callback_data=f"virty_house_buy:{key}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_virty_menu")])
    text = (
        "🏠 <b>ДОМА ЗА ВИРТЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Каждый дом даёт постоянный буст к игре.\n"
        f"💰 Ваш баланс: <b>{format_amount(bal)}$</b>\n\n"
        "<b>Доступные дома:</b>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("virty_house_buy:"))
async def cb_virty_house_buy(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    if key not in DONATE_HOUSES:
        await callback.answer("❌ Дом не найден.", show_alert=True); return
    user   = get_user(callback.from_user.id)
    d      = get_donate_user_data(user)
    house  = DONATE_HOUSES[key]
    price  = house.get("virty_price", 0)
    bal    = get_balance(callback.from_user.id)
    current = d.get("house")
    if current == key:
        rows = [
            [InlineKeyboardButton(text=f"🔴 Продать за {format_amount(house.get('sell_price',0))}$", callback_data=f"donate_house_sell_{key}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="virty_house_menu")],
        ]
        await callback.message.edit_text(
            f"🏠 <b>{house['name']}</b>\n\n✅ Этот дом уже у вас!\n✨ Эффект: {house['desc']}",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        await callback.answer(); return
    if bal < price:
        await callback.answer(f"❌ Недостаточно денег!\nНужно: {format_amount(price)}$\nУ вас: {format_amount(bal)}$", show_alert=True); return
    replace_text = f"\n⚠️ Ваш дом «{DONATE_HOUSES[current]['name']}» будет заменён!" if current and current in DONATE_HOUSES else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Купить за {format_amount(price)}$", callback_data=f"virty_house_confirm:{key}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="virty_house_menu")],
    ])
    await callback.message.edit_text(
        f"🏠 <b>{house['name']}</b>\n\n✨ Эффект: {house['desc']}\n"
        f"💰 Цена: <b>{format_amount(price)}$</b>{replace_text}\n"
        f"💰 Ваш баланс: {format_amount(bal)}$",
        parse_mode="HTML", reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data.startswith("virty_house_confirm:"))
async def cb_virty_house_confirm(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    if key not in DONATE_HOUSES:
        await callback.answer("❌", show_alert=True); return
    user   = get_user(callback.from_user.id)
    d      = get_donate_user_data(user)
    house  = DONATE_HOUSES[key]
    price  = house.get("virty_price", 0)
    bal    = get_balance(callback.from_user.id)
    if bal < price:
        await callback.answer("❌ Недостаточно денег!", show_alert=True); return
    update_balance(callback.from_user.id, bal - price)
    old_house = d.get("house")
    d["house"] = key
    save_user_data()
    extra = f"\nПрежний дом «{DONATE_HOUSES[old_house]['name']}» продан." if old_house and old_house in DONATE_HOUSES else ""
    await callback.message.edit_text(
        f"✅ <b>Дом куплен за вирты!</b>\n\n{house['name']}\n✨ Эффект: <b>{house['desc']}</b>\nБуст активирован немедленно!{extra}",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В магазин", callback_data="donate_virty_menu")],
        ])
    )
    await callback.answer("✅ Куплено!")


@router.callback_query(F.data == "virty_car_menu")
async def cb_virty_car_menu(callback: CallbackQuery):
    user   = get_user(callback.from_user.id)
    d      = get_donate_user_data(user)
    bal    = get_balance(callback.from_user.id)
    current = d.get("car")
    rows = []
    for key, car in DONATE_CARS.items():
        price = car.get("virty_price", 0)
        owned = "✅ " if current == key else ""
        rows.append([InlineKeyboardButton(
            text=f"{owned}{car['name']} — {format_amount(price)}$",
            callback_data=f"virty_car_buy:{key}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="donate_virty_menu")])
    text = (
        "🚗 <b>АВТО ЗА ВИРТЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Эксклюзивные суперкары за игровые деньги.\n"
        f"💰 Ваш баланс: <b>{format_amount(bal)}$</b>\n\n"
        "<b>Доступные авто:</b>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("virty_car_buy:"))
async def cb_virty_car_buy(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    if key not in DONATE_CARS:
        await callback.answer("❌ Авто не найдено.", show_alert=True); return
    user   = get_user(callback.from_user.id)
    d      = get_donate_user_data(user)
    car    = DONATE_CARS[key]
    price  = car.get("virty_price", 0)
    bal    = get_balance(callback.from_user.id)
    current = d.get("car")
    if current == key:
        rows = [
            [InlineKeyboardButton(text=f"🔴 Продать за {format_amount(car.get('sell_price',0))}$", callback_data=f"donate_car_sell_{key}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="virty_car_menu")],
        ]
        speed_line = f"\n⚡ Скорость: {car['speed']} км/ч" if car.get("speed") else ""
        await callback.message.edit_text(
            f"🚗 <b>{car['name']}</b>{speed_line}\n\n✅ Это авто уже у вас!\n📝 {car.get('desc','')}",
            parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        await callback.answer(); return
    if bal < price:
        await callback.answer(f"❌ Недостаточно денег!\nНужно: {format_amount(price)}$\nУ вас: {format_amount(bal)}$", show_alert=True); return
    replace_text = f"\n⚠️ Ваше авто «{DONATE_CARS[current]['name']}» будет заменено!" if current and current in DONATE_CARS else ""
    speed_line = f"\n⚡ Скорость: {car['speed']} км/ч" if car.get("speed") else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Купить за {format_amount(price)}$", callback_data=f"virty_car_confirm:{key}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="virty_car_menu")],
    ])
    await callback.message.edit_text(
        f"🚗 <b>{car['name']}</b>{speed_line}\n\n📝 {car.get('desc','')}\n"
        f"💰 Цена: <b>{format_amount(price)}$</b>{replace_text}\n"
        f"💰 Ваш баланс: {format_amount(bal)}$",
        parse_mode="HTML", reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data.startswith("virty_car_confirm:"))
async def cb_virty_car_confirm(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    if key not in DONATE_CARS:
        await callback.answer("❌", show_alert=True); return
    user   = get_user(callback.from_user.id)
    d      = get_donate_user_data(user)
    car    = DONATE_CARS[key]
    price  = car.get("virty_price", 0)
    bal    = get_balance(callback.from_user.id)
    if bal < price:
        await callback.answer("❌ Недостаточно денег!", show_alert=True); return
    update_balance(callback.from_user.id, bal - price)
    old_car = d.get("car")
    d["car"] = key
    save_user_data()
    extra = f"\nПрежнее авто «{DONATE_CARS[old_car]['name']}» продано." if old_car and old_car in DONATE_CARS else ""
    await callback.message.edit_text(
        f"✅ <b>Авто куплено за вирты!</b>\n\n{car['name']}\nЭксклюзив теперь ваш!{extra}",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В магазин", callback_data="donate_virty_menu")],
        ])
    )
    await callback.answer("✅ Куплено!")


async def handle_pre_checkout(pre_checkout: PreCheckoutQuery):
    await pre_checkout.answer(ok=True)


async def handle_successful_payment(message: Message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload

    if payload.startswith("dc_pkg_"):
        idx = int(payload.replace("dc_pkg_", ""))
        if 0 <= idx < len(DC_PACKAGES):
            pkg = DC_PACKAGES[idx]
            dc_amount = pkg["dc"]
            if pkg["bonus"]:
                bonus_match = [c for c in pkg["bonus"] if c.isdigit() or c == "+"]
                try:
                    bonus_dc = int("".join(c for c in pkg["bonus"].split("+")[-1] if c.isdigit()))
                    dc_amount += bonus_dc
                except Exception:
                    pass
            user = get_user(user_id)
            user["donate_coins"] = user.get("donate_coins", 0) + dc_amount
            save_user_data()
            await message.answer(
                f"✅ <b>Оплата прошла успешно!</b>\n\n"
                f"💎 Вы получили: <b>{dc_amount} DC</b>\n"
                f"💎 Ваш DC баланс: <b>{user['donate_coins']} DC</b>\n\n"
                f"1 DC = 100.000$ игровых денег",
                parse_mode="HTML",
                reply_markup=get_donate_main_kb()
            )
