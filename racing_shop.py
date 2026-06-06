from aiogram import Router, F
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
                           InlineKeyboardButton, BufferedInputFile, InputMediaPhoto)
from utils import get_user, get_balance, update_balance, save_user_data, format_amount

router = Router()

RACING_CARS = [
    {"name": "Mazda MX-5 Cup",                   "price": 80_000,       "dc": 0,    "speed": 240},
    {"name": "Honda Civic Type R TCR",            "price": 200_000,      "dc": 0,    "speed": 260},
    {"name": "Toyota GR Supra GT4",               "price": 400_000,      "dc": 0,    "speed": 270},
    {"name": "Porsche 718 Cayman GT4 Clubsport",  "price": 750_000,      "dc": 0,    "speed": 290},
    {"name": "BMW M4 GT4",                        "price": 1_100_000,    "dc": 0,    "speed": 295},
    {"name": "Lamborghini Huracán Super Trofeo",  "price": 1_800_000,    "dc": 0,    "speed": 320},
    {"name": "Ferrari 488 Challenge",             "price": 2_500_000,    "dc": 0,    "speed": 325},
    {"name": "McLaren 570S GT4",                  "price": 3_500_000,    "dc": 0,    "speed": 315},
    {"name": "Audi R8 LMS GT3",                   "price": 5_000_000,    "dc": 0,    "speed": 330},
    {"name": "Mercedes-AMG GT3",                  "price": 7_500_000,    "dc": 0,    "speed": 335},
    {"name": "Porsche 911 GT3 R",                 "price": 12_000_000,   "dc": 0,    "speed": 340},
    {"name": "Ferrari 296 GT3",                   "price": 18_000_000,   "dc": 0,    "speed": 345},
    {"name": "Lamborghini SC63",                  "price": 28_000_000,   "dc": 0,    "speed": 350},
    {"name": "Mercedes-AMG ONE",                  "price": 45_000_000,   "dc": 0,    "speed": 352},
    {"name": "Bugatti Bolide (track only)",       "price": 70_000_000,   "dc": 0,    "speed": 355},
    {"name": "Red Bull RB17",                     "price": 100_000_000,  "dc": 0,    "speed": 360},
    {"name": "Porsche 919 Hybrid Evo",            "price": 140_000_000,  "dc": 0,    "speed": 366},
    {"name": "McLaren MP4/4 (1988 F1)",           "price": 190_000_000,  "dc": 0,    "speed": 350},
    {"name": "Ferrari F2004 (F1)",                "price": 250_000_000,  "dc": 0,    "speed": 370},
    {"name": "Red Bull RB19 (F1 2023)",           "price": 350_000_000,  "dc": 0,    "speed": 380},
]

SELL_RATIO = 0.6


def _price_str(car: dict) -> str:
    if car["dc"]:
        return f"{car['dc']} DC"
    return f"{format_amount(car['price'])}$"


def rcar_text(idx: int, user_id: int) -> str:
    car = RACING_CARS[idx]
    total = len(RACING_CARS)
    u = get_user(user_id)
    rc = u.get("race_car")
    owned_idx = rc.get("idx") if rc else None
    is_owned = owned_idx == idx
    owned_name = RACING_CARS[owned_idx]["name"] if owned_idx is not None else "Нет"
    slot_line = "🔒 <b>Слот:</b> 1/1 — уже куплено" if is_owned else (
        "🔒 <b>Слот:</b> 1/1 — занят" if owned_idx is not None else "🔓 <b>Слот:</b> 0/1 — свободен"
    )
    dc_mark = " 💎" if car["dc"] else ""
    return (
        f"🕍 <b>Авто {idx + 1}/{total}</b>{dc_mark}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏎 <b>{car['name']}</b>\n\n"
        f"⚡ <b>Скорость:</b> {car['speed']} км/ч\n"
        f"💰 <b>Стоимость:</b> {_price_str(car)}\n\n"
        f"{slot_line}\n"
        f"🏎 Ваше авто: <b>{owned_name}</b>"
    )


def rcar_kb(idx: int, user_id: int) -> InlineKeyboardMarkup:
    total = len(RACING_CARS)
    u = get_user(user_id)
    rc = u.get("race_car")
    owned_idx = rc.get("idx") if rc else None
    is_owned = owned_idx == idx
    car = RACING_CARS[idx]

    nav_row = []
    if idx > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"rcar_view:{idx - 1}"))
    if is_owned:
        nav_row.append(InlineKeyboardButton(text="🔒 Уже куплено", callback_data="rcar_slot_full"))
    elif car["dc"] > 0:
        nav_row.append(InlineKeyboardButton(text=f"💎 Купить за {car['dc']} DC", callback_data=f"rcar_buy_{idx}"))
    else:
        nav_row.append(InlineKeyboardButton(text="✅ Купить", callback_data=f"rcar_buy_{idx}"))
    if idx < total - 1:
        nav_row.append(InlineKeyboardButton(text="Далее ▶️", callback_data=f"rcar_view:{idx + 1}"))

    rows = [nav_row]
    if owned_idx is not None:
        owned_car = RACING_CARS[owned_idx]
        if not owned_car["dc"]:
            sell_price = int(owned_car["price"] * SELL_RATIO)
            rows.append([InlineKeyboardButton(
                text=f"🔴 Продать {owned_car['name']} за {format_amount(sell_price)}$",
                callback_data="rcar_sell"
            )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _page_text(page: int, user_id: int = None) -> str:
    return rcar_text(0, user_id) if user_id else rcar_text(0, 0)


def _page_kb(page: int, user_id: int) -> InlineKeyboardMarkup:
    return rcar_kb(0, user_id)


def _car_photo(idx: int, user_id: int) -> BufferedInputFile | None:
    try:
        from image_gen import gen_car_card
        car = RACING_CARS[idx]
        u = get_user(user_id)
        rc = u.get("race_car")
        owned_idx = rc.get("idx") if rc else None
        owned_name = RACING_CARS[owned_idx]["name"] if owned_idx is not None else "Нет"
        d = {
            "name":       car["name"],
            "speed":      car["speed"],
            "price_str":  _price_str(car),
            "idx":        idx,
            "total":      len(RACING_CARS),
            "is_dc":      bool(car["dc"]),
            "is_owned":   owned_idx == idx,
            "owned_name": owned_name,
        }
        buf = gen_car_card(d)
        return BufferedInputFile(buf.read(), filename="car.png")
    except Exception:
        return None


@router.message(F.text.lower().in_(["🕍 гонки", "гонки", "гоночный магазин", "гоночные машины", "race shop", "🏎 гонки"]))
async def cmd_racing_shop(message: Message):
    user_id = message.from_user.id
    photo = _car_photo(0, user_id)
    if photo:
        await message.answer_photo(photo=photo, caption=rcar_text(0, user_id),
                                   reply_markup=rcar_kb(0, user_id), parse_mode="HTML")
    else:
        await message.answer(rcar_text(0, user_id), reply_markup=rcar_kb(0, user_id), parse_mode="HTML")


@router.message(F.text.lower().in_(["авто", "🏎 авто", "моё авто", "мое авто", "мой авто", "моё гоночное авто", "моя машина", "🏎 моё авто"]))
async def cmd_my_car_smart(message: Message):
    from smart_assets import build_car_response
    user_id = message.from_user.id
    result = build_car_response(user_id)
    if result:
        text, kb = result
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(rcar_text(0, user_id), reply_markup=rcar_kb(0, user_id), parse_mode="HTML")


async def _edit_car_msg(callback: CallbackQuery, idx: int):
    user_id = callback.from_user.id
    text = rcar_text(idx, user_id)
    kb   = rcar_kb(idx, user_id)
    photo = _car_photo(idx, user_id)
    if photo:
        try:
            media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
            await callback.message.edit_media(media=media, reply_markup=kb)
            await callback.answer()
            return
        except Exception:
            pass
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("rcar_view:"))
async def cb_rcar_view(callback: CallbackQuery):
    idx = int(callback.data.split(":")[1])
    await _edit_car_msg(callback, idx)


@router.callback_query(F.data == "rcar_slot_full")
async def cb_rcar_slot_full(callback: CallbackQuery):
    await callback.answer("🔒 Это авто уже ваше!", show_alert=True)


@router.callback_query(F.data.startswith("rcar_page_"))
async def cb_rcar_page_compat(callback: CallbackQuery):
    await _edit_car_msg(callback, 0)


@router.callback_query(F.data.startswith("rcar_buy_"))
async def cb_rcar_buy(callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.replace("rcar_buy_", ""))
    car = RACING_CARS[idx]
    user = get_user(user_id)
    owned = user.get("race_car")

    if owned and owned.get("idx") == idx:
        await callback.answer("🔒 Слот занят (1/1) — это авто уже ваше!", show_alert=True)
        return

    if car["dc"] > 0:
        dc_bal = user.get("donate_coins", 0)
        if dc_bal < car["dc"]:
            await callback.answer(
                f"❌ Недостаточно DC!\nНужно: {car['dc']} DC\nУ вас: {dc_bal} DC\n\nКупить DC можно в донат магазине.",
                show_alert=True
            )
            return
        replace_text = ""
        if owned:
            old = RACING_CARS[owned["idx"]]
            replace_text = f"\n\n⚠️ Ваш «{old['name']}» будет заменён!"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Купить за {car['dc']} DC", callback_data=f"rcar_confirm_{idx}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rcar_view:{idx}")],
        ])
        await callback.message.edit_text(
            f"🏎 <b>{car['name']}</b>\n\n"
            f"⚡ Скорость: {car['speed']} км/ч\n"
            f"💎 Цена: {car['dc']} DC (эксклюзив){replace_text}\n\n"
            f"💎 Ваш DC баланс: {dc_bal} DC",
            reply_markup=kb, parse_mode="HTML"
        )
    else:
        balance = get_balance(user_id)
        if balance < car["price"]:
            await callback.answer(
                f"❌ Недостаточно средств!\nНужно: {format_amount(car['price'])}$\nУ вас: {format_amount(balance)}$",
                show_alert=True
            )
            return
        replace_text = ""
        if owned:
            old = RACING_CARS[owned["idx"]]
            replace_text = f"\n\n⚠️ Ваш «{old['name']}» будет заменён!"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Купить за {format_amount(car['price'])}$", callback_data=f"rcar_confirm_{idx}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"rcar_view:{idx}")],
        ])
        await callback.message.edit_text(
            f"🏎 <b>{car['name']}</b>\n\n"
            f"⚡ Скорость: {car['speed']} км/ч\n"
            f"💳 Цена: {format_amount(car['price'])}${replace_text}\n\n"
            f"💰 Ваш баланс: {format_amount(balance)}$",
            reply_markup=kb, parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("rcar_confirm_"))
async def cb_rcar_confirm(callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.replace("rcar_confirm_", ""))
    car = RACING_CARS[idx]
    user = get_user(user_id)

    if car["dc"] > 0:
        dc_bal = user.get("donate_coins", 0)
        if dc_bal < car["dc"]:
            await callback.answer("❌ Недостаточно DC!", show_alert=True)
            return
        user["donate_coins"] = dc_bal - car["dc"]
    else:
        balance = get_balance(user_id)
        if balance < car["price"]:
            await callback.answer("❌ Недостаточно средств!", show_alert=True)
            return
        update_balance(user_id, balance - car["price"])

    user["race_car"] = {"idx": idx, "name": car["name"], "speed": car["speed"]}
    save_user_data()

    await callback.message.edit_text(
        f"✅ <b>Покупка совершена!</b>\n\n"
        f"🏎 <b>{car['name']}</b>\n"
        f"⚡ Скорость: <b>{car['speed']} км/ч</b>\n\n"
        f"Ваш гоночный болид готов к трассе!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В магазин", callback_data=f"rcar_view:{idx}")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer("🏎 Куплено!")


@router.callback_query(F.data == "rcar_sell")
async def cb_rcar_sell(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    owned = user.get("race_car")
    if not owned:
        await callback.answer("У вас нет гоночного авто.", show_alert=True)
        return
    idx = owned.get("idx", 0)
    car = RACING_CARS[idx]
    if car["dc"] > 0:
        await callback.answer("💎 Донат-авто нельзя продать!", show_alert=True)
        return
    sell_price = int(car["price"] * SELL_RATIO)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Продать за {format_amount(sell_price)}$", callback_data="rcar_sell_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"rcar_view:{idx}")],
    ])
    await callback.message.edit_text(
        f"💰 Продать <b>{car['name']}</b>?\n\n"
        f"⚡ Скорость: {car['speed']} км/ч\n"
        f"💳 Вы получите: <b>{format_amount(sell_price)}$</b> (60% от цены)",
        reply_markup=kb, parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "rcar_sell_confirm")
async def cb_rcar_sell_confirm(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    owned = user.get("race_car")
    if not owned:
        await callback.answer("Нет авто для продажи.", show_alert=True)
        return
    idx = owned.get("idx", 0)
    car = RACING_CARS[idx]
    if car["dc"] > 0:
        await callback.answer("💎 Донат-авто нельзя продать!", show_alert=True)
        return
    sell_price = int(car["price"] * SELL_RATIO)
    update_balance(user_id, get_balance(user_id) + sell_price)
    user["race_car"] = None
    save_user_data()
    await callback.message.edit_text(
        f"✅ <b>Продано!</b>\n\n"
        f"🏎 {car['name']} продан за <b>{format_amount(sell_price)}$</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🕍 В магазин", callback_data="rcar_view:0")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer(f"+{format_amount(sell_price)}$!")


@router.callback_query(F.data == "mycar_sell_confirm")
async def cb_mycar_sell_confirm(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    owned = user.get("race_car")
    if not owned:
        await callback.answer("У вас нет авто для продажи.", show_alert=True)
        return
    idx = owned.get("idx", 0)
    car = RACING_CARS[idx]
    if car["dc"] > 0:
        await callback.answer("💎 Донат-авто нельзя продать!", show_alert=True)
        return
    sell_price = int(car["price"] * SELL_RATIO)
    update_balance(user_id, get_balance(user_id) + sell_price)
    user["race_car"] = None
    save_user_data()
    await callback.message.edit_text(
        f"🔴 <b>{car['name']}</b> продан!\n\n"
        f"💰 Получено: <b>{format_amount(sell_price)}$</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🕍 В магазин", callback_data="rcar_view:0")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer(f"+{format_amount(sell_price)}$!")


def get_race_car_text(user_id: int) -> str:
    user = get_user(user_id)
    owned = user.get("race_car")
    if not owned:
        return "Нет"
    idx = owned.get("idx", 0)
    car = RACING_CARS[idx]
    dc_mark = " 💎" if car["dc"] else ""
    return f"{car['name']}{dc_mark} ({car['speed']} км/ч)"
