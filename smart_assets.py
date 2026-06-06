from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_user, format_amount


def build_house_response(user_id: int):
    from house_shop import SHOP_HOUSES, SELL_RATIO, HOUSE_KEYS, house_shop_text, get_house_shop_kb
    from donate import get_donate_user_data, DONATE_HOUSES
    import time as _time

    user = get_user(user_id)
    owned_key = user.get("shop_house")
    d = get_donate_user_data(user)
    don_key = d.get("house")

    has_shop = bool(owned_key and owned_key in SHOP_HOUSES)
    has_don = bool(don_key and don_key in DONATE_HOUSES)

    if not has_shop and not has_don:
        return None

    # ── Донат-дом: только инфо, без кнопки продажи здесь ──
    if has_don and not has_shop:
        don_house = DONATE_HOUSES[don_key]
        sell_p = don_house.get("sell_price", 0)
        text = (
            f"🏡 <b>Моё жильё</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💎 <b>{don_house['name']}</b>\n"
            f"✨ Эффект: {don_house['desc']}\n"
            f"🔴 Цена продажи: {format_amount(sell_p)}$"
        )
        rental = user.get("house_rental", {})
        if rental.get("active"):
            left = max(0, int(rental["expire_at"] - _time.time()))
            h, m = divmod(left // 60, 60)
            rent_btn = InlineKeyboardButton(
                text=f"🔑 Аренда активна ({h}ч {m}мин)",
                callback_data="myhouse_rent_menu"
            )
        else:
            rent_btn = InlineKeyboardButton(text="🔑 Сдать в аренду", callback_data="myhouse_rent_menu")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🔴 Продать за {format_amount(sell_p)}$", callback_data=f"donate_house_sell_{don_key}")],
            [rent_btn],
            [InlineKeyboardButton(text="🏠 Магазин домов", callback_data="myhouse_to_shop")],
        ])
        return text, kb

    # ── Магазинный дом: навигация + продать + аренда ──
    idx = HOUSE_KEYS.index(owned_key)
    text = house_shop_text(idx, owned_key)
    kb = get_house_shop_kb(idx, owned_key, show_rent=True)
    return text, kb


def build_house_shop_response(user_id: int):
    from house_shop import house_shop_text, get_house_shop_kb
    user = get_user(user_id)
    owned_key = user.get("shop_house")
    return house_shop_text(0, owned_key), get_house_shop_kb(0, owned_key)


def build_car_response(user_id: int):
    from racing_shop import RACING_CARS, SELL_RATIO, _price_str
    from donate import get_donate_user_data, DONATE_CARS

    user = get_user(user_id)
    owned = user.get("race_car")
    d = get_donate_user_data(user)
    don_key = d.get("car")

    has_race = owned is not None
    has_don = bool(don_key and don_key in DONATE_CARS)

    if not has_race and not has_don:
        return None

    text = "🏎 <b>Моё авто</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    kb_rows = []

    if has_don:
        don_car = DONATE_CARS[don_key]
        sell_p = don_car.get("sell_price", 0)
        speed_str = f" · ⚡ {don_car['speed']} км/ч" if don_car.get("speed") else ""
        text += (
            f"💎 <b>{don_car['name']}</b>{speed_str}\n"
            f"📝 {don_car.get('desc', 'Эксклюзивное донат-авто')}\n"
            f"🔴 Цена продажи: {format_amount(sell_p)}$\n\n"
        )
        kb_rows.append([InlineKeyboardButton(
            text=f"🔴 Продать {don_car['name']} за {format_amount(sell_p)}$",
            callback_data=f"donate_car_sell_{don_key}"
        )])

    if has_race:
        idx = owned.get("idx", 0)
        car = RACING_CARS[idx]
        sell_price = int(car["price"] * SELL_RATIO) if not car.get("dc") else 0
        text += (
            f"🏎 <b>{car['name']}</b>\n"
            f"⚡ Скорость: {car['speed']} км/ч\n"
            f"💰 {_price_str(car)}\n"
        )
        if sell_price:
            text += f"🔴 Цена продажи: {format_amount(sell_price)}$\n\n"
            kb_rows.append([InlineKeyboardButton(
                text=f"🔴 Продать {car['name']} за {format_amount(sell_price)}$",
                callback_data="mycar_sell_confirm"
            )])
        else:
            text += "\n"

    kb_rows.append([InlineKeyboardButton(text="🕍 Магазин авто", callback_data="rcar_view:0")])
    return text.rstrip(), InlineKeyboardMarkup(inline_keyboard=kb_rows)


def build_shop_car_response(user_id: int):
    from auto_shop import SHOP_CARS, SELL_RATIO, CAR_KEYS, car_shop_text, get_car_shop_kb
    import time as _t

    user = get_user(user_id)
    owned_key = user.get("shop_car")

    if not owned_key or owned_key not in SHOP_CARS:
        return None

    idx = CAR_KEYS.index(owned_key)
    text = car_shop_text(idx, owned_key)
    rental = user.get("car_rental", {})
    if rental.get("active"):
        left = max(0, int(rental["expire_at"] - _t.time()))
        h, m = divmod(left // 60, 60)
        rent_btn = InlineKeyboardButton(
            text=f"🔑 Аренда активна ({h}ч {m}мин)",
            callback_data="mycar_rent_menu"
        )
    else:
        rent_btn = InlineKeyboardButton(text="🔑 Сдать в аренду", callback_data="mycar_rent_menu")
    kb = get_car_shop_kb(idx, owned_key, show_rent=True)
    return text, kb


def build_shop_car_shop_response(user_id: int):
    from auto_shop import car_shop_text, get_car_shop_kb
    user = get_user(user_id)
    owned_key = user.get("shop_car")
    return car_shop_text(0, owned_key), get_car_shop_kb(0, owned_key)


def build_donate_biz_card(user_id: int):
    from donate import get_donate_user_data, DONATE_BUSINESSES, accumulate_biz_income

    user = get_user(user_id)
    d = get_donate_user_data(user)
    don_biz_key = d.get("business")

    if not don_biz_key or don_biz_key not in DONATE_BUSINESSES:
        return None

    don_biz = DONATE_BUSINESSES[don_biz_key]
    income = accumulate_biz_income(user_id)
    sell_p = don_biz.get("sell_price", 0)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💰 Собрать {format_amount(income)}$" if income > 0 else "💤 Доход накапливается...",
            callback_data=f"donate_biz_collect_{don_biz_key}"
        )],
        [InlineKeyboardButton(
            text=f"🔴 Продать за {format_amount(sell_p)}$",
            callback_data=f"donate_biz_sell_{don_biz_key}"
        )],
    ])
    text = (
        f"💎 <b>Донат-бизнес</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{don_biz['name']}</b>\n"
        f"📝 {don_biz.get('desc', '')}\n\n"
        f"📈 Прибыль в час: {format_amount(don_biz['income_per_hour'])}$\n"
        f"💰 Накоплено: <b>{format_amount(income)}$</b>\n"
        f"🔴 Цена продажи: {format_amount(sell_p)}$"
    )
    return text, kb
