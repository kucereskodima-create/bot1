from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_user, get_balance, update_balance, save_user_data, format_amount

router = Router()

SELL_RATIO = 0.6

SHOP_CARS = {
    "lada_granta": {
        "name": "🚗 Lada Granta",
        "speed": 170,
        "price": 350_000,
        "desc": "Простой и надёжный отечественный автомобиль",
    },
    "toyota_camry": {
        "name": "🚗 Toyota Camry",
        "speed": 210,
        "price": 2_500_000,
        "desc": "Популярный японский седан бизнес-класса",
    },
    "bmw_3": {
        "name": "🚗 BMW 3 Series",
        "speed": 240,
        "price": 5_000_000,
        "desc": "Спортивный немецкий седан с отличной динамикой",
    },
    "mercedes_c": {
        "name": "🚗 Mercedes-Benz C-Class",
        "speed": 245,
        "price": 7_500_000,
        "desc": "Премиальный немецкий седан со стильным дизайном",
    },
    "audi_a6": {
        "name": "🚗 Audi A6",
        "speed": 250,
        "price": 9_000_000,
        "desc": "Элегантный немецкий седан высокого класса",
    },
    "porsche_cayenne": {
        "name": "🚙 Porsche Cayenne",
        "speed": 265,
        "price": 18_000_000,
        "desc": "Мощный спортивный внедорожник из Германии",
    },
    "bentley_continental": {
        "name": "🚗 Bentley Continental GT",
        "speed": 318,
        "price": 45_000_000,
        "desc": "Роскошный британский гран-туризмо",
    },
    "lamborghini_urus": {
        "name": "🚙 Lamborghini Urus",
        "speed": 305,
        "price": 70_000_000,
        "desc": "Самый быстрый SUV в мире от итальянского бренда",
    },
    "rolls_royce": {
        "name": "🚗 Rolls-Royce Ghost",
        "speed": 250,
        "price": 120_000_000,
        "desc": "Эталон роскоши и статуса на дороге",
    },
    "bugatti_chiron": {
        "name": "🚗 Bugatti Chiron",
        "speed": 420,
        "price": 500_000_000,
        "desc": "Гиперкар — самый быстрый серийный автомобиль в мире",
    },
}

CAR_KEYS = list(SHOP_CARS.keys())


def get_owned_car(user_id: int) -> str | None:
    user = get_user(user_id)
    return user.get("shop_car")


CAR_RENT_RATES = [
    ("1 час",    0.015),
    ("5 часов",  0.070),
    ("10 часов", 0.130),
]


def car_shop_text(idx: int, owned_key: str | None) -> str:
    key = CAR_KEYS[idx]
    c = SHOP_CARS[key]
    total = len(CAR_KEYS)
    is_owned = owned_key == key
    owned_name = SHOP_CARS[owned_key]["name"] if owned_key and owned_key in SHOP_CARS else "Нет"
    if is_owned:
        slot_line = "🔒 <b>Слот:</b> 1/1 — уже куплен"
    elif owned_key:
        slot_line = "🔒 <b>Слот:</b> 1/1 — занят"
    else:
        slot_line = "🔓 <b>Слот:</b> 0/1 — свободен"
    rent_lines = "\n".join(
        f"  🕐 {label} → <b>+{format_amount(int(c['price'] * rate))}$</b>"
        for label, rate in CAR_RENT_RATES
    )
    return (
        f"🚗 <b>Автомобиль {idx + 1}/{total}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{c['name']}</b>\n"
        f"⚡ Скорость: <b>{c['speed']} км/ч</b>\n\n"
        f"📝 {c['desc']}\n\n"
        f"💰 <b>Стоимость:</b> {format_amount(c['price'])}$\n"
        f"🔴 <b>Продажа:</b> {format_amount(int(c['price'] * SELL_RATIO))}$\n\n"
        f"🔑 <b>Доход от аренды:</b>\n{rent_lines}\n\n"
        f"{slot_line}\n"
        f"🚗 Ваше авто: <b>{owned_name}</b>"
    )


def get_car_shop_kb(idx: int, owned_key: str | None, show_rent: bool = False) -> InlineKeyboardMarkup:
    total = len(CAR_KEYS)
    key = CAR_KEYS[idx]
    is_owned = owned_key == key

    nav_row = []
    if idx > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"cshop_view:{idx - 1}"))
    if is_owned:
        nav_row.append(InlineKeyboardButton(text="🔒 Уже куплен", callback_data="cshop_slot_full"))
    else:
        nav_row.append(InlineKeyboardButton(text="✅ Купить", callback_data=f"cshop_buy_{key}"))
    if idx < total - 1:
        nav_row.append(InlineKeyboardButton(text="Далее ▶️", callback_data=f"cshop_view:{idx + 1}"))
    else:
        nav_row.append(InlineKeyboardButton(text="Далее ▶️", callback_data="cshop_donate_view"))

    rows = [nav_row]
    if owned_key and owned_key in SHOP_CARS:
        sell_price = int(SHOP_CARS[owned_key]["price"] * SELL_RATIO)
        rows.append([InlineKeyboardButton(
            text=f"🔴 Продать {SHOP_CARS[owned_key]['name']} за {format_amount(sell_price)}$",
            callback_data=f"cshop_sell_{owned_key}"
        )])
        if show_rent:
            rows.append([InlineKeyboardButton(
                text="🔑 Сдать в аренду",
                callback_data="mycar_rent_menu"
            )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _donate_car_card_text(user_id: int) -> str:
    from donate import DONATE_CARS, get_donate_user_data
    user = get_user(user_id)
    d = get_donate_user_data(user)
    total = len(CAR_KEYS)
    car_key = d.get("car")
    car = DONATE_CARS.get("hypercar", {})
    owned = bool(car_key)
    virty = car.get("virty_price", 0)
    sell_p = car.get("sell_price", 0)
    speed_line = f"⚡ Скорость: <b>{car.get('speed', 0)} км/ч</b>\n\n" if car.get("speed") else ""
    status = "✅ У вас есть" if owned else "🔓 Не куплено"
    return (
        f"🚗 <b>Автомобиль {total + 1}/{total + 1}</b>  💎 <i>ДОНАТ</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{car.get('name', '')}</b>\n"
        f"{speed_line}"
        f"📝 {car.get('desc', '')}\n\n"
        f"💎 <b>Цена:</b> {car.get('dc', 0)} DC\n"
        f"💰 <b>За вирты:</b> {format_amount(virty)}$\n"
        f"🔴 <b>Продажа:</b> {format_amount(sell_p)}$\n\n"
        f"{status}"
    )


def _donate_car_card_kb(user_id: int) -> InlineKeyboardMarkup:
    from donate import DONATE_CARS, get_donate_user_data
    user = get_user(user_id)
    d = get_donate_user_data(user)
    car_key = d.get("car")
    car = DONATE_CARS.get("hypercar", {})
    total = len(CAR_KEYS)
    rows = [[InlineKeyboardButton(text="◀️ Назад", callback_data=f"cshop_view:{total - 1}")]]
    if car_key:
        sell_p = car.get("sell_price", 0)
        rows.append([InlineKeyboardButton(text=f"🔴 Продать за {format_amount(sell_p)}$", callback_data=f"donate_car_sell_{car_key}")])
    else:
        dc = car.get("dc", 0)
        virty = car.get("virty_price", 0)
        rows.append([InlineKeyboardButton(text=f"💎 Купить за {dc} DC", callback_data="donate_cars_menu")])
        rows.append([InlineKeyboardButton(text=f"💵 Купить за {format_amount(virty)}$", callback_data="virty_car_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "cshop_donate_view")
async def cb_cshop_donate_view(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text(
        _donate_car_card_text(user_id),
        parse_mode="HTML",
        reply_markup=_donate_car_card_kb(user_id)
    )
    await callback.answer()


@router.message(F.text.lower().in_(["🚗 магазин авто", "магазин авто", "автосалон", "/автосалон", "купить авто", "/купить авто"]))
async def cmd_car_shop(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    owned_key = user.get("shop_car")
    await message.answer(
        car_shop_text(0, owned_key),
        parse_mode="HTML",
        reply_markup=get_car_shop_kb(0, owned_key)
    )


@router.callback_query(F.data.startswith("cshop_view:"))
async def cb_cshop_view(callback: CallbackQuery):
    idx = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    user = get_user(user_id)
    owned_key = user.get("shop_car")
    await callback.message.edit_text(
        car_shop_text(idx, owned_key),
        parse_mode="HTML",
        reply_markup=get_car_shop_kb(idx, owned_key)
    )
    await callback.answer()


@router.callback_query(F.data == "cshop_slot_full")
async def cb_cshop_slot_full(callback: CallbackQuery):
    await callback.answer("🔒 Этот автомобиль уже ваш!", show_alert=True)


@router.callback_query(F.data.startswith("cshop_buy_"))
async def cb_cshop_buy(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    key = callback.data.replace("cshop_buy_", "")
    if key not in SHOP_CARS:
        await callback.answer("❌ Автомобиль не найден.", show_alert=True)
        return
    car = SHOP_CARS[key]
    owned = user.get("shop_car")
    idx = CAR_KEYS.index(key)
    if owned == key:
        await callback.answer("🔒 Слот занят (1/1) — этот автомобиль уже ваш!", show_alert=True)
        return
    balance = get_balance(user_id)
    if balance < car["price"]:
        await callback.answer(
            f"❌ Недостаточно средств!\nНужно: {format_amount(car['price'])}$\nУ вас: {format_amount(balance)}$",
            show_alert=True
        )
        return
    refund = 0
    old_text = ""
    if owned and owned in SHOP_CARS:
        refund = int(SHOP_CARS[owned]["price"] * SELL_RATIO)
        old_text = f"\n🔄 Старое авто продано за <b>{format_amount(refund)}$</b>"
    total_cost = car["price"] - refund
    update_balance(user_id, balance - total_cost)
    user["shop_car"] = key
    save_user_data()
    await callback.message.edit_text(
        f"✅ Вы купили <b>{car['name']}</b>!\n"
        f"💳 Стоимость: <b>{format_amount(car['price'])}$</b>{old_text}\n"
        f"⚡ Скорость: <b>{car['speed']} км/ч</b>\n\n"
        f"🚗 Ваше авто: <b>{car['name']}</b>",
        parse_mode="HTML",
        reply_markup=get_car_shop_kb(idx, key)
    )
    await callback.answer(f"✅ {car['name']} куплен!")


@router.callback_query(F.data.startswith("cshop_sell_"))
async def cb_cshop_sell(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    key = callback.data.replace("cshop_sell_", "")
    if key not in SHOP_CARS or user.get("shop_car") != key:
        await callback.answer("❌ Этот автомобиль вам не принадлежит.", show_alert=True)
        return
    sell_price = int(SHOP_CARS[key]["price"] * SELL_RATIO)
    update_balance(user_id, get_balance(user_id) + sell_price)
    user["shop_car"] = None
    save_user_data()
    await callback.message.edit_text(
        f"🔴 Вы продали <b>{SHOP_CARS[key]['name']}</b> за <b>{format_amount(sell_price)}$</b>.\n"
        "🚗 Ваше авто: <b>Нет</b>",
        parse_mode="HTML",
        reply_markup=get_car_shop_kb(0, None)
    )
    await callback.answer(f"Продано за {format_amount(sell_price)}$")


# ──────────────────────────────────────────────────────────────────────────────
#  АРЕНДА АВТО
# ──────────────────────────────────────────────────────────────────────────────
CAR_RENT_OPTIONS = {
    "1h":  {"hours": 1,  "label": "1 час",   "rate": 0.015},
    "5h":  {"hours": 5,  "label": "5 часов",  "rate": 0.070},
    "10h": {"hours": 10, "label": "10 часов", "rate": 0.130},
}


def _get_rentable_car(user_id: int):
    """Возвращает (name, price) если у игрока есть авто (шоп или донат)."""
    from utils import get_user as _gu
    from donate import get_donate_user_data, DONATE_CARS
    user = _gu(user_id)
    don = get_donate_user_data(user)
    don_car = don.get("car")
    if don_car and don_car in DONATE_CARS:
        c = DONATE_CARS[don_car]
        return c["name"], c["sell_price"]
    shop_key = user.get("shop_car")
    if shop_key and shop_key in SHOP_CARS:
        c = SHOP_CARS[shop_key]
        return c["name"], c["price"]
    return None, None


def _rent_car_kb(user_id: int) -> InlineKeyboardMarkup:
    _, price = _get_rentable_car(user_id)
    if not price:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Назад", callback_data="mycars_to_shop")
        ]])
    rows = []
    for key, opt in CAR_RENT_OPTIONS.items():
        income = int(price * opt["rate"])
        rows.append([InlineKeyboardButton(
            text=f"🕐 {opt['label']} → +{format_amount(income)}$",
            callback_data=f"crent_start:{key}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="mycars_to_shop")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text.lower().in_(["аренда авто", "🚗 аренда", "сдать авто", "/аренда_авто"]))
async def cmd_car_rent(message: Message):
    user_id = message.from_user.id
    name, price = _get_rentable_car(user_id)
    if not price:
        await message.answer("❌ У вас нет автомобиля для аренды.")
        return
    from utils import get_user as _gu
    user = _gu(user_id)
    rental = user.get("car_rental", {})
    if rental.get("active"):
        import time as _t
        left = max(0, int(rental["expire_at"] - _t.time()))
        h, m = divmod(left // 60, 60)
        await message.answer(
            f"🚗 <b>Аренда активна!</b>\n\n"
            f"Авто: <b>{name}</b>\n"
            f"💰 Доход: <b>{format_amount(rental['income'])}$</b>\n"
            f"⏳ Осталось: <b>{h}ч {m}мин</b>",
            parse_mode="HTML"
        )
        return
    text = (
        f"🚗 <b>Сдать авто в аренду</b>\n\n"
        f"Авто: <b>{name}</b>\n"
        f"💵 Стоимость: <b>{format_amount(price)}$</b>\n\n"
        f"Выберите срок аренды:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=_rent_car_kb(user_id))


@router.callback_query(F.data.startswith("crent_start:"))
async def cb_crent_start(callback: CallbackQuery):
    import time as _t
    from utils import get_user as _gu, save_user_data as _sav
    user_id = callback.from_user.id
    opt_key = callback.data.split(":")[1]
    if opt_key not in CAR_RENT_OPTIONS:
        await callback.answer("❌ Неверный вариант.", show_alert=True)
        return
    user = _gu(user_id)
    if user.get("car_rental", {}).get("active"):
        await callback.answer("❌ Аренда уже активна!", show_alert=True)
        return
    name, price = _get_rentable_car(user_id)
    if not price:
        await callback.answer("❌ Нет авто для аренды.", show_alert=True)
        return
    opt = CAR_RENT_OPTIONS[opt_key]
    income = int(price * opt["rate"])
    expire_at = int(_t.time()) + opt["hours"] * 3600
    user["car_rental"] = {
        "active": True,
        "hours": opt["hours"],
        "income": income,
        "expire_at": expire_at,
    }
    _sav()
    await callback.message.edit_text(
        f"✅ <b>Авто сдано в аренду на {opt['label']}!</b>\n\n"
        f"🚗 {name}\n"
        f"💰 Получите: <b>{format_amount(income)}$</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🚗 Меню", callback_data="mycars_to_shop")
        ]])
    )
    await callback.answer("✅ Аренда началась!")


@router.callback_query(F.data == "mycars_to_shop")
async def cb_mycars_to_shop(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    owned_key = user.get("shop_car")
    await callback.message.edit_text(
        car_shop_text(0, owned_key),
        parse_mode="HTML",
        reply_markup=get_car_shop_kb(0, owned_key, show_rent=bool(owned_key))
    )
    await callback.answer()


@router.callback_query(F.data == "mycar_rent_menu")
async def cb_mycar_rent_menu(callback: CallbackQuery):
    import time as _t
    user_id = callback.from_user.id
    user = get_user(user_id)
    name, price = _get_rentable_car(user_id)
    if not price:
        await callback.answer("❌ У вас нет авто для аренды.", show_alert=True)
        return
    rental = user.get("car_rental", {})
    if rental.get("active"):
        left = max(0, int(rental["expire_at"] - _t.time()))
        h, m = divmod(left // 60, 60)
        await callback.message.edit_text(
            f"🚗 <b>Аренда активна!</b>\n\n"
            f"Авто: <b>{name}</b>\n"
            f"💰 Доход: <b>{format_amount(rental['income'])}$</b>\n"
            f"⏳ Осталось: <b>{h}ч {m}мин</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="mycars_to_shop")
            ]])
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        f"🚗 <b>Сдать авто в аренду</b>\n\n"
        f"Авто: <b>{name}</b>\n"
        f"💵 Стоимость: <b>{format_amount(price)}$</b>\n\n"
        f"Выберите срок аренды:",
        parse_mode="HTML",
        reply_markup=_rent_car_kb(user_id)
    )
    await callback.answer()


async def check_car_rentals(bot):
    """Вызывается планировщиком — начисляет истёкшие аренды авто."""
    import time as _t
    from utils import user_data, save_user_data as _sav
    now = _t.time()
    changed = False
    for uid_str, user in user_data.items():
        rental = user.get("car_rental", {})
        if not rental.get("active"):
            continue
        if now >= rental.get("expire_at", 0):
            income = rental.get("income", 0)
            user["balance"] = round(user.get("balance", 0) + income)
            user["car_rental"] = {"active": False}
            changed = True
            try:
                await bot.send_message(
                    int(uid_str),
                    f"🚗 <b>Аренда авто завершена!</b>\n\n"
                    f"💰 Начислено: <b>{format_amount(income)}$</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    if changed:
        _sav()
