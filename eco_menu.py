import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_user, get_balance, update_balance, save_user_data, format_amount

router = Router()

ECO_BUSINESSES = {
    "restaurant": {"name": "🍔 Ресторан",     "price":   50_000, "income_per_hour":    500},
    "store":      {"name": "🏪 Магазин",       "price":  150_000, "income_per_hour":  1_500},
    "pawnshop":   {"name": "🏦 Ломбард",       "price":  400_000, "income_per_hour":  3_000},
    "factory":    {"name": "🏭 Завод",          "price": 1_000_000, "income_per_hour": 7_500},
    "mall":       {"name": "🏙 Торговый центр", "price": 3_000_000, "income_per_hour": 20_000},
}

SELL_RATIO = 0.6


def _get_eco_biz(user: dict) -> dict | None:
    return user.get("eco_biz") or None


def _calc_income(biz: dict) -> int:
    key = biz.get("key")
    if not key or key not in ECO_BUSINESSES:
        return 0
    last = biz.get("last_collect") or int(time.time())
    elapsed = (int(time.time()) - last) / 3600
    return int(elapsed * ECO_BUSINESSES[key]["income_per_hour"])


# ─── keyboards ────────────────────────────────────────────────────────────────

def _main_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 Бизнес",  callback_data="eco_biz_section")],
        [InlineKeyboardButton(text="🚗 Авто",     callback_data="eco_car_section")],
        [InlineKeyboardButton(text="🏠 Дом",      callback_data="eco_house_section")],
    ])


def _biz_shop_kb(owned_key: str | None) -> InlineKeyboardMarkup:
    rows = []
    for key, b in ECO_BUSINESSES.items():
        mark = "✅ " if key == owned_key else ""
        rows.append([InlineKeyboardButton(
            text=f"{mark}{b['name']} — {format_amount(b['price'])}$ | {format_amount(b['income_per_hour'])}$/ч",
            callback_data=f"eco_biz_buy_{key}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="eco_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _biz_owned_kb(biz: dict) -> InlineKeyboardMarkup:
    key = biz["key"]
    sell_price = int(ECO_BUSINESSES[key]["price"] * SELL_RATIO)
    income = _calc_income(biz)
    rows = []
    if income > 0:
        rows.append([InlineKeyboardButton(
            text=f"💰 Собрать {format_amount(income)}$",
            callback_data="eco_biz_collect"
        )])
    rows.append([InlineKeyboardButton(
        text=f"🔴 Продать за {format_amount(sell_price)}$",
        callback_data=f"eco_biz_sell_{key}"
    )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="eco_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _car_kb(has_car: bool) -> InlineKeyboardMarkup:
    rows = []
    if not has_car:
        rows.append([InlineKeyboardButton(text="🕍 Открыть магазин гонок", callback_data="eco_open_racing")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="eco_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _house_kb(has_house: bool) -> InlineKeyboardMarkup:
    rows = []
    if not has_house:
        rows.append([InlineKeyboardButton(text="🏠 Открыть магазин домов", callback_data="eco_open_houses")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="eco_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _eco_summary_text(user_id: int) -> str:
    user = get_user(user_id)
    name = user.get("name", "Без имени")

    biz = _get_eco_biz(user)
    if biz and biz.get("key") in ECO_BUSINESSES:
        b = ECO_BUSINESSES[biz["key"]]
        income = _calc_income(biz)
        biz_line = f"{b['name']}\n   └ {format_amount(b['income_per_hour'])}$/ч · накоплено: {format_amount(income)}$"
    else:
        biz_line = "❌ Нет — нажмите чтобы купить"

    from racing_shop import RACING_CARS
    race = user.get("race_car")
    if race:
        idx = race.get("idx", 0)
        rc = RACING_CARS[idx] if idx < len(RACING_CARS) else None
        car_line = f"{rc['name']} ⚡{rc['speed']} км/ч" if rc else race.get("name", "—")
    else:
        car_line = "❌ Нет — нажмите чтобы купить"

    from house_shop import SHOP_HOUSES
    sh_key = user.get("shop_house")
    if sh_key and sh_key in SHOP_HOUSES:
        h = SHOP_HOUSES[sh_key]
        house_line = f"{h['name']}\n   └ {h['desc']}"
    else:
        house_line = "❌ Нет — нажмите чтобы купить"

    return (
        f"💹 <b>ЭКОНОМИКА</b> — {name}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🏢 <b>Бизнес:</b>\n   {biz_line}\n\n"
        f"🚗 <b>Авто:</b>\n   {car_line}\n\n"
        f"🏠 <b>Дом:</b>\n   {house_line}"
    )


# ─── handlers ─────────────────────────────────────────────────────────────────

@router.message(F.text.lower().in_(["💹 экономика", "экономика", "эко", "/эко", "/экономика"]))
async def cmd_eco(message: Message):
    user_id = message.from_user.id
    await message.answer(
        _eco_summary_text(user_id),
        parse_mode="HTML",
        reply_markup=_main_kb(user_id)
    )


@router.callback_query(F.data == "eco_main")
async def cb_eco_main(callback: CallbackQuery):
    await callback.message.edit_text(
        _eco_summary_text(callback.from_user.id),
        parse_mode="HTML",
        reply_markup=_main_kb(callback.from_user.id)
    )
    await callback.answer()


# ─── Бизнес ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "eco_biz_section")
async def cb_eco_biz(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    biz = _get_eco_biz(user)
    if biz and biz.get("key") in ECO_BUSINESSES:
        b = ECO_BUSINESSES[biz["key"]]
        income = _calc_income(biz)
        sell_price = int(b["price"] * SELL_RATIO)
        text = (
            f"🏢 <b>{b['name']}</b>\n"
            "━━━━━━━━━━━━━━\n"
            f"💵 Доход: {format_amount(b['income_per_hour'])}$/ч\n"
            f"💰 Накоплено: <b>{format_amount(income)}$</b>\n"
            f"💸 Стоимость продажи: {format_amount(sell_price)}$"
        )
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_biz_owned_kb(biz))
    else:
        text = (
            "🏢 <b>Купить бизнес</b>\n"
            "━━━━━━━━━━━━━━\n"
            "Бизнес приносит доход каждый час.\n"
            "Можно владеть только <b>1 бизнесом</b>.\n\n"
            "<b>Доступные бизнесы:</b>"
        )
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_biz_shop_kb(None))
    await callback.answer()


@router.callback_query(F.data.startswith("eco_biz_buy_"))
async def cb_eco_biz_buy(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    key = callback.data.replace("eco_biz_buy_", "")
    if key not in ECO_BUSINESSES:
        await callback.answer("❌ Бизнес не найден.", show_alert=True)
        return
    biz = _get_eco_biz(user)
    if biz and biz.get("key") in ECO_BUSINESSES:
        await callback.answer("❌ У вас уже есть бизнес! Сначала продайте его.", show_alert=True)
        return
    b = ECO_BUSINESSES[key]
    balance = get_balance(user_id)
    if balance < b["price"]:
        await callback.answer(
            f"❌ Недостаточно средств!\nНужно: {format_amount(b['price'])}$\nУ вас: {format_amount(balance)}$",
            show_alert=True
        )
        return
    update_balance(user_id, balance - b["price"])
    user["eco_biz"] = {"key": key, "last_collect": int(time.time())}
    save_user_data()
    await callback.message.edit_text(
        f"✅ Вы купили <b>{b['name']}</b>!\n"
        f"💵 Доход: {format_amount(b['income_per_hour'])}$/ч\n\n"
        f"Возвращайтесь чтобы собрать доход!",
        parse_mode="HTML",
        reply_markup=_biz_owned_kb(user["eco_biz"])
    )
    await callback.answer(f"✅ {b['name']} куплен!")


@router.callback_query(F.data == "eco_biz_collect")
async def cb_eco_biz_collect(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    biz = _get_eco_biz(user)
    if not biz or biz.get("key") not in ECO_BUSINESSES:
        await callback.answer("❌ У вас нет бизнеса.", show_alert=True)
        return
    income = _calc_income(biz)
    if income <= 0:
        await callback.answer("⏳ Доход ещё не накопился. Приходите позже!", show_alert=True)
        return
    update_balance(user_id, get_balance(user_id) + income)
    biz["last_collect"] = int(time.time())
    save_user_data()
    b = ECO_BUSINESSES[biz["key"]]
    await callback.answer(f"💰 Собрано {format_amount(income)}$!", show_alert=True)
    await callback.message.edit_text(
        f"🏢 <b>{b['name']}</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"💵 Доход: {format_amount(b['income_per_hour'])}$/ч\n"
        f"💰 Накоплено: <b>0$</b>\n"
        f"💸 Стоимость продажи: {format_amount(int(b['price'] * SELL_RATIO))}$",
        parse_mode="HTML",
        reply_markup=_biz_owned_kb(biz)
    )


@router.callback_query(F.data.startswith("eco_biz_sell_"))
async def cb_eco_biz_sell(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    key = callback.data.replace("eco_biz_sell_", "")
    biz = _get_eco_biz(user)
    if not biz or biz.get("key") != key:
        await callback.answer("❌ Этот бизнес вам не принадлежит.", show_alert=True)
        return
    income = _calc_income(biz)
    sell_price = int(ECO_BUSINESSES[key]["price"] * SELL_RATIO)
    total = sell_price + income
    update_balance(user_id, get_balance(user_id) + total)
    user["eco_biz"] = None
    save_user_data()
    await callback.message.edit_text(
        f"🔴 Бизнес продан!\n"
        f"💸 За продажу: {format_amount(sell_price)}$\n"
        f"💰 Накопленный доход: {format_amount(income)}$\n"
        f"✅ Итого получено: <b>{format_amount(total)}$</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏢 Купить новый", callback_data="eco_biz_section")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="eco_main")],
        ])
    )
    await callback.answer(f"Продано за {format_amount(total)}$")


# ─── Авто ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "eco_car_section")
async def cb_eco_car(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    from racing_shop import RACING_CARS
    race = user.get("race_car")
    if race:
        idx = race.get("idx", 0)
        rc = RACING_CARS[idx] if idx < len(RACING_CARS) else None
        name = rc["name"] if rc else race.get("name", "—")
        speed = rc["speed"] if rc else race.get("speed", "—")
        text = (
            f"🚗 <b>Ваше авто:</b>\n"
            "━━━━━━━━━━━━━━\n"
            f"🏎 <b>{name}</b>\n"
            f"⚡ Скорость: {speed} км/ч"
        )
    else:
        text = (
            "🚗 <b>Авто</b>\n"
            "━━━━━━━━━━━━━━\n"
            "У вас нет гоночного авто.\n"
            "Откройте магазин гонок чтобы купить!"
        )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_car_kb(race is not None))
    await callback.answer()


@router.callback_query(F.data == "eco_open_racing")
async def cb_eco_open_racing(callback: CallbackQuery):
    from racing_shop import _page_text, _page_kb
    await callback.message.edit_text(
        _page_text(0),
        parse_mode="HTML",
        reply_markup=_page_kb(0, callback.from_user.id)
    )
    await callback.answer()


# ─── Дом ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "eco_house_section")
async def cb_eco_house(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    from house_shop import SHOP_HOUSES
    sh_key = user.get("shop_house")
    if sh_key and sh_key in SHOP_HOUSES:
        h = SHOP_HOUSES[sh_key]
        sell_price = int(h["price"] * 0.6)
        text = (
            f"🏠 <b>Ваш дом:</b>\n"
            "━━━━━━━━━━━━━━\n"
            f"<b>{h['name']}</b>\n"
            f"🎁 Буст: {h['desc']}\n"
            f"💸 Продажа: {format_amount(sell_price)}$"
        )
    else:
        text = (
            "🏠 <b>Дом</b>\n"
            "━━━━━━━━━━━━━━\n"
            "У вас нет дома.\n"
            "Откройте магазин домов чтобы купить!"
        )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_house_kb(sh_key is not None))
    await callback.answer()


@router.callback_query(F.data == "eco_open_houses")
async def cb_eco_open_houses(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    from house_shop import SHOP_HOUSES, _menu_kb
    owned_key = user.get("shop_house")
    owned_name = SHOP_HOUSES[owned_key]["name"] if owned_key and owned_key in SHOP_HOUSES else "Нет"
    await callback.message.edit_text(
        "🏠 <b>МАГАЗИН ДОМОВ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Каждый дом даёт постоянный буст.\n"
        "Можно владеть только <b>1 домом</b>.\n\n"
        f"🏡 Ваш дом: <b>{owned_name}</b>",
        parse_mode="HTML",
        reply_markup=_menu_kb(owned_key)
    )
    await callback.answer()
