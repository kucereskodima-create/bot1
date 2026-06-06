from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_user, get_balance, update_balance, save_user_data, format_amount

router = Router()

SELL_RATIO = 0.6

SHOP_HOUSES = {
    "abandoned": {
        "name": "🏚 Заброшенный дом",
        "price": 124_000,
        "work_boost": 0,
        "farm_boost": 0,
        "bonus_cd_pct": 3,
        "desc": "⏱ Бонус быстрее на 3%",
    },
    "tent": {
        "name": "🏕 Палатка",
        "price": 476_240,
        "work_boost": 2,
        "farm_boost": 0,
        "bonus_cd_pct": 0,
        "desc": "💼 Работа +2%",
    },
    "treehouse": {
        "name": "🏡 Домик на дереве",
        "price": 896_000,
        "work_boost": 0,
        "farm_boost": 2,
        "bonus_cd_pct": 0,
        "desc": "⛏ Ферма +2%",
    },
    "village": {
        "name": "🏠 Дом в посёлке",
        "price": 1_300_620,
        "work_boost": 0,
        "farm_boost": 0,
        "bonus_cd_pct": 5,
        "desc": "⏱ Бонус быстрее на 5%",
    },
    "city": {
        "name": "🏘 Дом в городе",
        "price": 2_540_000,
        "work_boost": 5,
        "farm_boost": 0,
        "bonus_cd_pct": 0,
        "desc": "💼 Работа +5%",
    },
    "moscow": {
        "name": "🏙 Дом в Москве",
        "price": 7_930_000,
        "work_boost": 0,
        "farm_boost": 5,
        "bonus_cd_pct": 0,
        "desc": "⛏ Ферма +5%",
    },
    "hotel": {
        "name": "🏤 Дом в отеле",
        "price": 11_250_500,
        "work_boost": 8,
        "farm_boost": 0,
        "bonus_cd_pct": 0,
        "desc": "💼 Работа +8%",
    },
    "maldives": {
        "name": "🏖 Дом на Мальдивах",
        "price": 15_000_000,
        "work_boost": 0,
        "farm_boost": 10,
        "bonus_cd_pct": 0,
        "desc": "⛏ Ферма +10%",
    },
    "mountains": {
        "name": "⛰ Дом в горах",
        "price": 35_000_000,
        "work_boost": 5,
        "farm_boost": 5,
        "bonus_cd_pct": 5,
        "desc": "💼 +5% работа · ⛏ +5% ферма · ⏱ -5% кд",
    },
}

HOUSE_KEYS = list(SHOP_HOUSES.keys())


def get_shop_house_boosts(user_id: int) -> dict:
    user = get_user(user_id)
    key = user.get("shop_house")
    if not key or key not in SHOP_HOUSES:
        return {"work_boost": 0, "farm_boost": 0, "bonus_cd_pct": 0}
    h = SHOP_HOUSES[key]
    return {
        "work_boost":   h.get("work_boost", 0),
        "farm_boost":   h.get("farm_boost", 0),
        "bonus_cd_pct": h.get("bonus_cd_pct", 0),
    }


HOUSE_RENT_RATES = [
    ("1 час",   0.020),
    ("5 часов", 0.090),
    ("10 часов",0.160),
]


def house_shop_text(idx: int, owned_key: str | None) -> str:
    key = HOUSE_KEYS[idx]
    h = SHOP_HOUSES[key]
    total = len(HOUSE_KEYS)
    is_owned = owned_key == key
    owned_name = SHOP_HOUSES[owned_key]["name"] if owned_key and owned_key in SHOP_HOUSES else "Нет"
    slot_line = "🔒 <b>Слот:</b> 1/1 — уже куплен" if is_owned else (
        "🔒 <b>Слот:</b> 1/1 — занят" if owned_key else "🔓 <b>Слот:</b> 0/1 — свободен"
    )
    rent_lines = "\n".join(
        f"  🕐 {label} → <b>+{format_amount(int(h['price'] * rate))}$</b>"
        for label, rate in HOUSE_RENT_RATES
    )
    return (
        f"🏠 <b>Дом {idx + 1}/{total}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{h['name']}</b>\n\n"
        f"🎁 <b>Буст:</b> {h['desc']}\n\n"
        f"💰 <b>Стоимость:</b> {format_amount(h['price'])}$\n"
        f"🔴 <b>Продажа:</b> {format_amount(int(h['price'] * SELL_RATIO))}$\n\n"
        f"🔑 <b>Доход от аренды:</b>\n{rent_lines}\n\n"
        f"{slot_line}\n"
        f"🏡 Ваш дом: <b>{owned_name}</b>"
    )


def _menu_kb(owned_key: str | None) -> InlineKeyboardMarkup:
    return get_house_shop_kb(0, owned_key)


def get_house_shop_kb(idx: int, owned_key: str | None, show_rent: bool = False) -> InlineKeyboardMarkup:
    total = len(HOUSE_KEYS)
    key = HOUSE_KEYS[idx]
    is_owned = owned_key == key

    nav_row = []
    if idx > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"hshop_view:{idx - 1}"))
    if is_owned:
        nav_row.append(InlineKeyboardButton(text="🔒 Уже куплен", callback_data="hshop_slot_full"))
    else:
        nav_row.append(InlineKeyboardButton(text="✅ Купить", callback_data=f"hshop_buy_{key}"))
    if idx < total - 1:
        nav_row.append(InlineKeyboardButton(text="Далее ▶️", callback_data=f"hshop_view:{idx + 1}"))
    else:
        nav_row.append(InlineKeyboardButton(text="Далее ▶️", callback_data="hshop_donate_view"))

    rows = [nav_row]
    if owned_key and owned_key in SHOP_HOUSES:
        sell_price = int(SHOP_HOUSES[owned_key]["price"] * SELL_RATIO)
        rows.append([InlineKeyboardButton(
            text=f"🔴 Продать {SHOP_HOUSES[owned_key]['name']} за {format_amount(sell_price)}$",
            callback_data=f"hshop_sell_{owned_key}"
        )])
        if show_rent:
            rows.append([InlineKeyboardButton(
                text="🔑 Сдать в аренду",
                callback_data="myhouse_rent_menu"
            )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _donate_house_card_text(user_id: int) -> str:
    from donate import DONATE_HOUSES, get_donate_user_data
    user = get_user(user_id)
    d = get_donate_user_data(user)
    total = len(HOUSE_KEYS)
    house_key = d.get("house")
    house = DONATE_HOUSES.get("whitehouse", {})
    owned = bool(house_key)
    virty = house.get("virty_price", 0)
    sell_p = house.get("sell_price", 0)
    status = "✅ У вас есть" if owned else "🔓 Не куплен"
    return (
        f"🏠 <b>Дом {total + 1}/{total + 1}</b>  💎 <i>ДОНАТ</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{house.get('name', '')}</b>\n\n"
        f"🎁 <b>Буст:</b> {house.get('desc', '')}\n\n"
        f"💎 <b>Цена:</b> {house.get('dc', 0)} DC\n"
        f"💰 <b>За вирты:</b> {format_amount(virty)}$\n"
        f"🔴 <b>Продажа:</b> {format_amount(sell_p)}$\n\n"
        f"{status}"
    )


def _donate_house_card_kb(user_id: int) -> InlineKeyboardMarkup:
    from donate import DONATE_HOUSES, get_donate_user_data
    user = get_user(user_id)
    d = get_donate_user_data(user)
    house_key = d.get("house")
    house = DONATE_HOUSES.get("whitehouse", {})
    total = len(HOUSE_KEYS)
    rows = [[InlineKeyboardButton(text="◀️ Назад", callback_data=f"hshop_view:{total - 1}")]]
    if house_key:
        sell_p = house.get("sell_price", 0)
        rows.append([InlineKeyboardButton(text=f"🔴 Продать за {format_amount(sell_p)}$", callback_data=f"donate_house_sell_{house_key}")])
    else:
        dc = house.get("dc", 0)
        virty = house.get("virty_price", 0)
        rows.append([InlineKeyboardButton(text=f"💎 Купить за {dc} DC", callback_data="donate_houses_menu")])
        rows.append([InlineKeyboardButton(text=f"💵 Купить за {format_amount(virty)}$", callback_data="virty_house_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "hshop_donate_view")
async def cb_hshop_donate_view(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text(
        _donate_house_card_text(user_id),
        parse_mode="HTML",
        reply_markup=_donate_house_card_kb(user_id)
    )
    await callback.answer()


@router.message(F.text.lower().in_(["🏠 магазин домов", "магазин домов", "дома", "/дома"]))
async def cmd_house_shop(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    owned_key = user.get("shop_house")
    await message.answer(
        house_shop_text(0, owned_key),
        parse_mode="HTML",
        reply_markup=get_house_shop_kb(0, owned_key)
    )


@router.message(F.text.lower().in_(["дом", "🏡 дом", "мой дом", "моё жильё", "мое жилье", "🏡 мой дом"]))
async def cmd_house_smart(message: Message):
    from smart_assets import build_house_response, build_house_shop_response
    user_id = message.from_user.id
    result = build_house_response(user_id)
    if result:
        text, kb = result
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        text, kb = build_house_shop_response(user_id)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("hshop_view:"))
async def cb_hshop_view(callback: CallbackQuery):
    idx = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    user = get_user(user_id)
    owned_key = user.get("shop_house")
    await callback.message.edit_text(
        house_shop_text(idx, owned_key),
        parse_mode="HTML",
        reply_markup=get_house_shop_kb(idx, owned_key)
    )
    await callback.answer()


@router.callback_query(F.data == "hshop_slot_full")
async def cb_hshop_slot_full(callback: CallbackQuery):
    await callback.answer("🔒 Этот дом уже ваш!", show_alert=True)


@router.callback_query(F.data.startswith("hshop_buy_"))
async def cb_hshop_buy(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    key = callback.data.replace("hshop_buy_", "")
    if key not in SHOP_HOUSES:
        await callback.answer("❌ Дом не найден.", show_alert=True)
        return
    house = SHOP_HOUSES[key]
    owned = user.get("shop_house")
    idx = HOUSE_KEYS.index(key)
    if owned == key:
        await callback.answer("🔒 Слот занят (1/1) — этот дом уже ваш!", show_alert=True)
        return
    balance = get_balance(user_id)
    if balance < house["price"]:
        await callback.answer(
            f"❌ Недостаточно средств!\nНужно: {format_amount(house['price'])}$\nУ вас: {format_amount(balance)}$",
            show_alert=True
        )
        return
    refund = 0
    old_text = ""
    if owned and owned in SHOP_HOUSES:
        refund = int(SHOP_HOUSES[owned]["price"] * SELL_RATIO)
        old_text = f"\n🔄 Старый дом продан за <b>{format_amount(refund)}$</b>"
    total_cost = house["price"] - refund
    update_balance(user_id, balance - total_cost)
    user["shop_house"] = key
    save_user_data()
    await callback.message.edit_text(
        f"✅ Вы купили <b>{house['name']}</b>!\n"
        f"💳 Стоимость: <b>{format_amount(house['price'])}$</b>{old_text}\n"
        f"🎁 Буст: <b>{house['desc']}</b>\n\n"
        f"🏡 Текущий дом: <b>{house['name']}</b>",
        parse_mode="HTML",
        reply_markup=get_house_shop_kb(idx, key)
    )
    await callback.answer(f"✅ {house['name']} куплен!")


@router.callback_query(F.data == "myhouse_to_shop")
async def cb_myhouse_to_shop(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    owned_key = user.get("shop_house")
    await callback.message.edit_text(
        house_shop_text(0, owned_key),
        parse_mode="HTML",
        reply_markup=get_house_shop_kb(0, owned_key)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("hshop_sell_"))
async def cb_hshop_sell(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    key = callback.data.replace("hshop_sell_", "")
    if key not in SHOP_HOUSES or user.get("shop_house") != key:
        await callback.answer("❌ Этот дом вам не принадлежит.", show_alert=True)
        return
    sell_price = int(SHOP_HOUSES[key]["price"] * SELL_RATIO)
    update_balance(user_id, get_balance(user_id) + sell_price)
    user["shop_house"] = None
    save_user_data()
    await callback.message.edit_text(
        f"🔴 Вы продали <b>{SHOP_HOUSES[key]['name']}</b> за <b>{format_amount(sell_price)}$</b>.\n"
        "🏡 Ваш дом: <b>Нет</b>",
        parse_mode="HTML",
        reply_markup=get_house_shop_kb(0, None)
    )
    await callback.answer(f"Продано за {format_amount(sell_price)}$")


# ──────────────────────────────────────────────────────────────────────────────
#  АРЕНДА ДОМА
# ──────────────────────────────────────────────────────────────────────────────
HOUSE_RENT_OPTIONS = {
    "1h":  {"hours": 1,  "label": "1 час",  "rate": 0.020},
    "5h":  {"hours": 5,  "label": "5 часов", "rate": 0.090},
    "10h": {"hours": 10, "label": "10 часов","rate": 0.160},
}


def _get_rentable_house(user_id: int):
    """Возвращает (name, price) если у игрока есть дом (шоп или донат)."""
    from utils import get_user as _gu
    from donate import get_donate_user_data, DONATE_HOUSES
    user = _gu(user_id)
    don = get_donate_user_data(user)
    don_house = don.get("house")
    if don_house and don_house in DONATE_HOUSES:
        h = DONATE_HOUSES[don_house]
        return h["name"], h["sell_price"]
    shop_key = user.get("shop_house")
    if shop_key and shop_key in SHOP_HOUSES:
        h = SHOP_HOUSES[shop_key]
        return h["name"], h["price"]
    return None, None


def _rent_house_kb(user_id: int) -> InlineKeyboardMarkup:
    _, price = _get_rentable_house(user_id)
    if not price:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Назад", callback_data="myhouse_to_shop")
        ]])
    rows = []
    for key, opt in HOUSE_RENT_OPTIONS.items():
        income = int(price * opt["rate"])
        rows.append([InlineKeyboardButton(
            text=f"🕐 {opt['label']} → +{format_amount(income)}$",
            callback_data=f"hrent_start:{key}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="myhouse_to_shop")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text.lower().in_(["аренда дома", "🏠 аренда", "сдать дом", "/аренда_дома"]))
async def cmd_house_rent(message: Message):
    user_id = message.from_user.id
    name, price = _get_rentable_house(user_id)
    if not price:
        await message.answer("❌ У вас нет дома для аренды.")
        return
    from utils import get_user as _gu
    user = _gu(user_id)
    rental = user.get("house_rental", {})
    if rental.get("active"):
        import time as _t
        left = max(0, int(rental["expire_at"] - _t.time()))
        h, m = divmod(left // 60, 60)
        await message.answer(
            f"🏠 <b>Аренда активна!</b>\n\n"
            f"Дом: <b>{name}</b>\n"
            f"💰 Доход: <b>{format_amount(rental['income'])}$</b>\n"
            f"⏳ Осталось: <b>{h}ч {m}мин</b>",
            parse_mode="HTML"
        )
        return
    text = (
        f"🏠 <b>Сдать дом в аренду</b>\n\n"
        f"Дом: <b>{name}</b>\n"
        f"💵 Стоимость: <b>{format_amount(price)}$</b>\n\n"
        f"Выберите срок аренды:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=_rent_house_kb(user_id))


@router.callback_query(F.data == "myhouse_rent_menu")
async def cb_myhouse_rent_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    from utils import get_user as _gu
    import time as _t
    user = _gu(user_id)
    name, price = _get_rentable_house(user_id)
    if not price:
        await callback.answer("❌ У вас нет дома для аренды.", show_alert=True)
        return
    rental = user.get("house_rental", {})
    if rental.get("active"):
        left = max(0, int(rental["expire_at"] - _t.time()))
        h, m = divmod(left // 60, 60)
        await callback.message.edit_text(
            f"🏠 <b>Аренда активна!</b>\n\n"
            f"Дом: <b>{name}</b>\n"
            f"💰 Доход: <b>{format_amount(rental['income'])}$</b>\n"
            f"⏳ Осталось: <b>{h}ч {m}мин</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="myhouse_to_shop")
            ]])
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        f"🏠 <b>Сдать дом в аренду</b>\n\n"
        f"Дом: <b>{name}</b>\n"
        f"💵 Стоимость: <b>{format_amount(price)}$</b>\n\n"
        f"Выберите срок аренды:",
        parse_mode="HTML",
        reply_markup=_rent_house_kb(user_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("hrent_start:"))
async def cb_hrent_start(callback: CallbackQuery):
    import time as _t
    from utils import get_user as _gu, save_user_data as _sav
    user_id = callback.from_user.id
    opt_key = callback.data.split(":")[1]
    if opt_key not in HOUSE_RENT_OPTIONS:
        await callback.answer("❌ Неверный вариант.", show_alert=True)
        return
    user = _gu(user_id)
    if user.get("house_rental", {}).get("active"):
        await callback.answer("❌ Аренда уже активна!", show_alert=True)
        return
    name, price = _get_rentable_house(user_id)
    if not price:
        await callback.answer("❌ Нет дома для аренды.", show_alert=True)
        return
    opt = HOUSE_RENT_OPTIONS[opt_key]
    income = int(price * opt["rate"])
    expire_at = int(_t.time()) + opt["hours"] * 3600
    user["house_rental"] = {
        "active": True,
        "hours": opt["hours"],
        "income": income,
        "expire_at": expire_at,
    }
    _sav()
    await callback.message.edit_text(
        f"✅ <b>Дом сдан в аренду на {opt['label']}!</b>\n\n"
        f"🏠 {name}\n"
        f"💰 Получите: <b>{format_amount(income)}$</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🏠 Меню", callback_data="myhouse_to_shop")
        ]])
    )
    await callback.answer("✅ Аренда началась!")


async def check_house_rentals(bot):
    """Вызывается планировщиком — начисляет истёкшие аренды домов."""
    import time as _t
    from utils import user_data, save_user_data as _sav
    now = _t.time()
    changed = False
    for uid_str, user in user_data.items():
        rental = user.get("house_rental", {})
        if not rental.get("active"):
            continue
        if now >= rental.get("expire_at", 0):
            income = rental.get("income", 0)
            user["balance"] = round(user.get("balance", 0) + income)
            user["house_rental"] = {"active": False}
            changed = True
            try:
                await bot.send_message(
                    int(uid_str),
                    f"🏠 <b>Аренда дома завершена!</b>\n\n"
                    f"💰 Начислено: <b>{format_amount(income)}$</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    if changed:
        _sav()
