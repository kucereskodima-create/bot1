import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_user, get_balance, update_balance, save_user_data, format_amount

router = Router()

SELL_RATIO = 0.6

BIZ_LEVELS = {
    1: {"name": "Старт",       "multiplier": 1.0,  "cost_ratio": 0.0},
    2: {"name": "Базовый",     "multiplier": 1.3,  "cost_ratio": 0.3},
    3: {"name": "Развитый",    "multiplier": 1.7,  "cost_ratio": 0.8},
    4: {"name": "Продвинутый", "multiplier": 2.2,  "cost_ratio": 1.5},
    5: {"name": "Элитный",     "multiplier": 3.0,  "cost_ratio": 3.0},
    6: {"name": "Премиум",     "multiplier": 4.0,  "cost_ratio": 6.0},
    7: {"name": "Легенда",     "multiplier": 5.5,  "cost_ratio": 12.0},
}
MAX_BIZ_LEVEL = 7


def get_biz_level(user: dict, biz_idx: int) -> int:
    return user.get("biz_levels", {}).get(str(biz_idx), 1)


def get_biz_upgrade_cost(biz_price: int, target_level: int) -> int:
    ratio = BIZ_LEVELS[target_level]["cost_ratio"]
    return int(biz_price * ratio)

BUSINESSES = [
    {
        "name": "🥤 Ларёк",
        "desc": "Небольшой торговый ларёк в оживлённом месте. Минимальные вложения, стабильный поток покупателей — идеальный старт для начинающего предпринимателя.",
        "price": 350_000,
        "income_per_hour": 4_500,
    },
    {
        "name": "☕ Кофейня",
        "desc": "Стильная кофейня в деловом квартале города. Авторские напитки, уютная атмосфера и очередь из постоянных гостей каждое утро.",
        "price": 900_000,
        "income_per_hour": 9_500,
    },
    {
        "name": "🍔 Бургерная",
        "desc": "Популярная бургерная с фирменным меню и живой музыкой по вечерам. Молодёжная аудитория и высокий средний чек обеспечивают уверенный доход.",
        "price": 1_800_000,
        "income_per_hour": 18_000,
    },
    {
        "name": "⛽ АЗС",
        "desc": "Современная автозаправочная станция на оживлённой трассе. Круглосуточный трафик, магазин при станции и автомойка — три источника прибыли в одном.",
        "price": 4_000_000,
        "income_per_hour": 35_000,
    },
    {
        "name": "🚕 Таксопарк",
        "desc": "Собственный таксопарк с флотом современных автомобилей. Подключение к ведущим агрегаторам и диспетчерская служба работают за вас 24/7.",
        "price": 8_000_000,
        "income_per_hour": 65_000,
    },
    {
        "name": "🛠 СТО",
        "desc": "Профессиональная станция технического обслуживания с полным спектром услуг. Дорогостоящие ремонты, плановое ТО и детейлинг — живая очередь клиентов каждый день.",
        "price": 15_000_000,
        "income_per_hour": 110_000,
    },
    {
        "name": "🏪 Магазин 24/7",
        "desc": "Сеть круглосуточных магазинов в спальных районах. Высокая проходимость, широкий ассортимент и полная автоматизация кассового учёта делают этот бизнес золотой жилой.",
        "price": 30_000_000,
        "income_per_hour": 180_000,
    },
    {
        "name": "🎲 Игровой Клуб",
        "desc": "Элитный развлекательный клуб с премиальными игровыми зонами, баром и vip-кабинетами. Закрытое членство и высокий средний чек превращают каждый вечер в рекорд выручки.",
        "price": 60_000_000,
        "income_per_hour": 300_000,
    },
    {
        "name": "🏨 Отель",
        "desc": "Пятизвёздочный бутик-отель в историческом центре. Люксовые номера, ресторан высокой кухни и спа-комплекс привлекают состоятельных гостей со всего мира.",
        "price": 100_000_000,
        "income_per_hour": 450_000,
    },
    {
        "name": "✈️ Аэропорт",
        "desc": "Международный аэропорт с терминалами бизнес-авиации, duty-free зонами и грузовыми терминалами. Тысячи рейсов в месяц генерируют доходы, недоступные обычному бизнесу.",
        "price": 150_000_000,
        "income_per_hour": 600_000,
    },
]


# ──────────────────────────────────────────────
#  МАГАЗИН БИЗНЕСОВ (просмотр/покупка)
# ──────────────────────────────────────────────

def get_biz_shop_kb(idx: int, owned: list) -> InlineKeyboardMarkup:
    total = len(BUSINESSES)
    is_owned = idx in owned
    nav_row = []
    if idx > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"biz_shop_view:{idx - 1}"))
    if is_owned:
        nav_row.append(InlineKeyboardButton(text="🔒 Слот занят (1/1)", callback_data="biz_slot_full"))
    else:
        nav_row.append(InlineKeyboardButton(text="✅ Купить", callback_data=f"biz_shop_buy:{idx}"))
    if idx < total - 1:
        nav_row.append(InlineKeyboardButton(text="Далее ▶️", callback_data=f"biz_shop_view:{idx + 1}"))
    else:
        nav_row.append(InlineKeyboardButton(text="Далее ▶️", callback_data="biz_donate_view"))
    menu_row = [InlineKeyboardButton(text="🏠 Меню", callback_data="biz_shop_close")]
    return InlineKeyboardMarkup(inline_keyboard=[nav_row, menu_row])


def biz_shop_text(idx: int, owned: list) -> str:
    biz = BUSINESSES[idx]
    total = len(BUSINESSES)
    is_owned = idx in owned
    slot_line = "🔒 <b>Слот:</b> 1/1 — уже куплен" if is_owned else "🔓 <b>Слот:</b> 0/1 — доступен"
    return (
        f"🏢 <b>Бизнес {idx + 1}/{total}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{biz['name']}</b>\n\n"
        f"📝 {biz['desc']}\n\n"
        f"💰 <b>Стоимость:</b> {format_amount(biz['price'])}$\n"
        f"📈 <b>Прибыль в час:</b> {format_amount(biz['income_per_hour'])}$\n\n"
        f"{slot_line}"
    )


@router.message(F.text.lower().in_(["🏢 бизнес", "бизнес", "биз", "🏢 биз", "бизнесы", "/бизнес"]))
async def cmd_biz_smart(message: Message):
    from smart_assets import build_donate_biz_card
    user_id = message.from_user.id
    user = get_user(user_id)
    owned = user.get("businesses", [])
    if owned:
        await message.answer(my_biz_text(user, 0), reply_markup=my_biz_kb(user, 0), parse_mode="HTML")
        don_card = build_donate_biz_card(user_id)
        if don_card:
            text, kb = don_card
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        don_card = build_donate_biz_card(user_id)
        if don_card:
            text, kb = don_card
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.answer(biz_shop_text(0, owned), reply_markup=get_biz_shop_kb(0, owned), parse_mode="HTML")


@router.message(F.text.lower().in_(["🏢 купить бизнес", "купить бизнес", "магазин бизнесов"]))
async def cmd_biz_shop_only(message: Message):
    user = get_user(message.from_user.id)
    owned = user.get("businesses", [])
    await message.answer(biz_shop_text(0, owned), reply_markup=get_biz_shop_kb(0, owned), parse_mode="HTML")


@router.callback_query(F.data.startswith("biz_shop_view:"))
async def cb_biz_shop_view(callback: CallbackQuery):
    idx = int(callback.data.split(":")[1])
    user = get_user(callback.from_user.id)
    owned = user.get("businesses", [])
    await callback.message.edit_text(biz_shop_text(idx, owned), reply_markup=get_biz_shop_kb(idx, owned), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "biz_slot_full")
async def cb_biz_slot_full(callback: CallbackQuery):
    await callback.answer("🔒 Слот занят! Продайте бизнес в разделе «Мои бизнесы».", show_alert=True)


@router.callback_query(F.data.startswith("biz_shop_buy:"))
async def cb_biz_shop_buy(callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split(":")[1])
    biz = BUSINESSES[idx]

    user = get_user(user_id)
    balance = get_balance(user_id)

    owned = user.get("businesses", [])
    if idx in owned:
        await callback.answer("⚠️ Вы уже владеете этим бизнесом!", show_alert=True)
        return

    if balance < biz["price"]:
        await callback.answer(
            f"❌ Недостаточно средств!\nНужно: {format_amount(biz['price'])}$\nУ вас: {format_amount(balance)}$",
            show_alert=True
        )
        return

    update_balance(user_id, balance - biz["price"])
    owned.append(idx)
    user["businesses"] = owned

    if "biz_last_collect" not in user:
        user["biz_last_collect"] = {}
    user["biz_last_collect"][str(idx)] = int(time.time())

    save_user_data()

    await callback.answer(f"✅ {biz['name']} куплен!", show_alert=True)
    await callback.message.edit_text(
        f"✅ <b>Куплено: {biz['name']}</b>\n\n"
        f"📈 Прибыль: <b>{format_amount(biz['income_per_hour'])}$/ч</b>\n"
        f"💰 Баланс: <b>{format_amount(get_balance(user_id))}$</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏢 К бизнесам", callback_data=f"biz_shop_view:{idx}")],
            [InlineKeyboardButton(text="📦 Мои бизнесы", callback_data="mybiz_view:0")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="biz_shop_close")],
        ]),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "biz_shop_close")
async def cb_biz_shop_close(callback: CallbackQuery):
    from keyboards import menu_kb
    from utils import safe_reply_kb
    await callback.message.delete()
    await callback.message.answer("Главное меню:", reply_markup=safe_reply_kb(callback.message, menu_kb))
    await callback.answer()


# ──────────────────────────────────────────────
#  ДОНАТ-БИЗНЕС в магазине (последняя карточка)
# ──────────────────────────────────────────────

def _donate_biz_card_text(user_id: int) -> str:
    from donate import DONATE_BUSINESSES, get_donate_user_data, accumulate_biz_income
    user = get_user(user_id)
    d = get_donate_user_data(user)
    total = len(BUSINESSES)
    biz_key = d.get("business")
    biz = DONATE_BUSINESSES.get("casino", {})
    owned = bool(biz_key)
    income = accumulate_biz_income(user_id) if owned else 0
    virty = biz.get("virty_price", 0)
    sell_p = biz.get("sell_price", 0)
    status = "✅ У вас есть" if owned else "🔓 Не куплен"
    text = (
        f"🏢 <b>Бизнес {total + 1}/{total + 1}</b>  💎 <i>ДОНАТ</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{biz['name']}</b>\n\n"
        f"📝 {biz.get('desc', '')}\n\n"
        f"📈 <b>Прибыль в час:</b> {format_amount(biz.get('income_per_hour', 0))}$\n"
    )
    if owned:
        text += f"💵 <b>Накоплено:</b> {format_amount(income)}$\n"
    text += (
        f"💎 <b>Цена:</b> {biz.get('dc', 0)} DC\n"
        f"💰 <b>За вирты:</b> {format_amount(virty)}$\n"
        f"🔴 <b>Продажа:</b> {format_amount(sell_p)}$\n\n"
        f"{status}"
    )
    return text


def _donate_biz_card_kb(user_id: int) -> InlineKeyboardMarkup:
    from donate import DONATE_BUSINESSES, get_donate_user_data, accumulate_biz_income
    user = get_user(user_id)
    d = get_donate_user_data(user)
    biz_key = d.get("business")
    biz = DONATE_BUSINESSES.get("casino", {})
    total = len(BUSINESSES)
    rows = []
    nav_row = [InlineKeyboardButton(text="◀️ Назад", callback_data=f"biz_shop_view:{total - 1}")]
    rows.append(nav_row)
    if biz_key:
        income = accumulate_biz_income(user_id)
        if income > 0:
            rows.append([InlineKeyboardButton(text=f"💵 Собрать {format_amount(income)}$", callback_data=f"donate_biz_collect_{biz_key}")])
        sell_p = biz.get("sell_price", 0)
        rows.append([InlineKeyboardButton(text=f"🔴 Продать за {format_amount(sell_p)}$", callback_data=f"donate_biz_sell_{biz_key}")])
    else:
        virty = biz.get("virty_price", 0)
        dc = biz.get("dc", 0)
        rows.append([InlineKeyboardButton(text=f"💎 Купить за {dc} DC", callback_data="donate_biz_menu")])
        rows.append([InlineKeyboardButton(text=f"💵 Купить за {format_amount(virty)}$", callback_data="virty_biz_menu")])
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="biz_shop_close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "biz_donate_view")
async def cb_biz_donate_view(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text(
        _donate_biz_card_text(user_id),
        parse_mode="HTML",
        reply_markup=_donate_biz_card_kb(user_id)
    )
    await callback.answer()


# ──────────────────────────────────────────────
#  МОИ БИЗНЕСЫ (просмотр/сбор/продажа)
# ──────────────────────────────────────────────

def _calc_income(user: dict, biz_idx: int) -> int:
    biz = BUSINESSES[biz_idx]
    last_collect = user.get("biz_last_collect", {}).get(str(biz_idx))
    if not last_collect:
        return 0
    elapsed_hours = (int(time.time()) - last_collect) / 3600
    lvl = get_biz_level(user, biz_idx)
    multiplier = BIZ_LEVELS.get(lvl, BIZ_LEVELS[1])["multiplier"]
    return int(elapsed_hours * biz["income_per_hour"] * multiplier)


def my_biz_text(user: dict, pos: int) -> str:
    owned = user.get("businesses", [])
    total = len(owned)
    biz_idx = owned[pos]
    biz = BUSINESSES[biz_idx]
    income = _calc_income(user, biz_idx)
    sell_price = int(biz["price"] * SELL_RATIO)
    lvl = get_biz_level(user, biz_idx)
    lvl_info = BIZ_LEVELS.get(lvl, BIZ_LEVELS[1])
    real_income_ph = int(biz["income_per_hour"] * lvl_info["multiplier"])
    next_lvl = lvl + 1
    upgrade_line = ""
    if next_lvl <= MAX_BIZ_LEVEL:
        upgrade_cost = get_biz_upgrade_cost(biz["price"], next_lvl)
        next_mult = BIZ_LEVELS[next_lvl]["multiplier"]
        next_iph = int(biz["income_per_hour"] * next_mult)
        upgrade_line = (
            f"\n⬆️ <b>Лвл {next_lvl} ({BIZ_LEVELS[next_lvl]['name']}):</b> "
            f"{format_amount(upgrade_cost)}$ → {format_amount(next_iph)}$/ч"
        )
    return (
        f"📦 <b>Мой бизнес {pos + 1}/{total}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{biz['name']}</b>\n\n"
        f"📝 {biz['desc']}\n\n"
        f"💰 <b>Стоимость:</b> {format_amount(biz['price'])}$\n"
        f"⭐ <b>Уровень:</b> {lvl}/{MAX_BIZ_LEVEL} — {lvl_info['name']}\n"
        f"📈 <b>Прибыль в час:</b> {format_amount(real_income_ph)}$\n"
        f"💵 <b>Накоплено:</b> {format_amount(income)}$\n"
        f"🔴 Цена продажи: {format_amount(sell_price)}$"
        f"{upgrade_line}"
    )


def my_biz_kb(user: dict, pos: int) -> InlineKeyboardMarkup:
    owned = user.get("businesses", [])
    total = len(owned)
    biz_idx = owned[pos]
    lvl = get_biz_level(user, biz_idx)

    nav_row = []
    if pos > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"mybiz_view:{pos - 1}"))
    if pos < total - 1:
        nav_row.append(InlineKeyboardButton(text="Далее ▶️", callback_data=f"mybiz_view:{pos + 1}"))

    action_row = [
        InlineKeyboardButton(text="💵 Собрать", callback_data=f"mybiz_collect:{pos}"),
        InlineKeyboardButton(text="🔴 Продать", callback_data=f"mybiz_sell:{pos}"),
    ]
    rows = []
    if nav_row:
        rows.append(nav_row)
    rows.append(action_row)
    if lvl < MAX_BIZ_LEVEL:
        biz = BUSINESSES[biz_idx]
        upgrade_cost = get_biz_upgrade_cost(biz["price"], lvl + 1)
        rows.append([InlineKeyboardButton(
            text=f"⬆️ Улучшить до лвл {lvl + 1} ({format_amount(upgrade_cost)}$)",
            callback_data=f"mybiz_upgrade:{pos}"
        )])
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="biz_shop_close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text.lower().in_(["мои бизнесы", "мой бизнес", "📦 мои бизнесы", "/мои_бизнесы"]))
async def cmd_my_biz(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    owned = user.get("businesses", [])
    if not owned:
        await message.answer(
            "📦 У вас пока нет бизнесов.\n\nКупите бизнес в разделе <b>🏢 Бизнес</b>!",
            parse_mode="HTML"
        )
        return
    await message.answer(my_biz_text(user, 0), reply_markup=my_biz_kb(user, 0), parse_mode="HTML")


@router.callback_query(F.data.startswith("mybiz_view:"))
async def cb_mybiz_view(callback: CallbackQuery):
    user_id = callback.from_user.id
    pos = int(callback.data.split(":")[1])
    user = get_user(user_id)
    owned = user.get("businesses", [])
    if not owned:
        await callback.answer("У вас нет бизнесов.", show_alert=True)
        return
    pos = max(0, min(pos, len(owned) - 1))
    await callback.message.edit_text(my_biz_text(user, pos), reply_markup=my_biz_kb(user, pos), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("mybiz_collect:"))
async def cb_mybiz_collect(callback: CallbackQuery):
    user_id = callback.from_user.id
    pos = int(callback.data.split(":")[1])
    user = get_user(user_id)
    owned = user.get("businesses", [])
    if not owned or pos >= len(owned):
        await callback.answer("Бизнес не найден.", show_alert=True)
        return

    biz_idx = owned[pos]
    income = _calc_income(user, biz_idx)
    if income <= 0:
        await callback.answer("💤 Прибыль ещё не накопилась. Подождите немного!", show_alert=True)
        return

    update_balance(user_id, get_balance(user_id) + income)
    if "biz_last_collect" not in user:
        user["biz_last_collect"] = {}
    user["biz_last_collect"][str(biz_idx)] = int(time.time())
    save_user_data()

    await callback.answer(f"✅ Собрано: {format_amount(income)}$!", show_alert=True)
    user = get_user(user_id)
    await callback.message.edit_text(my_biz_text(user, pos), reply_markup=my_biz_kb(user, pos), parse_mode="HTML")


@router.callback_query(F.data.startswith("mybiz_sell:"))
async def cb_mybiz_sell(callback: CallbackQuery):
    user_id = callback.from_user.id
    pos = int(callback.data.split(":")[1])
    user = get_user(user_id)
    owned = user.get("businesses", [])
    if not owned or pos >= len(owned):
        await callback.answer("Бизнес не найден.", show_alert=True)
        return

    biz_idx = owned[pos]
    biz = BUSINESSES[biz_idx]

    income = _calc_income(user, biz_idx)
    sell_price = int(biz["price"] * SELL_RATIO)
    total_payout = sell_price + income

    update_balance(user_id, get_balance(user_id) + total_payout)
    owned.remove(biz_idx)
    user["businesses"] = owned
    if "biz_last_collect" in user:
        user["biz_last_collect"].pop(str(biz_idx), None)
    save_user_data()

    await callback.answer(f"🔴 Продано за {format_amount(sell_price)}$!", show_alert=True)

    user = get_user(user_id)
    new_owned = user.get("businesses", [])
    if not new_owned:
        await callback.message.edit_text(
            f"🔴 <b>{biz['name']}</b> продан!\n\n"
            f"💰 Получено: <b>{format_amount(sell_price)}$</b>"
            + (f"\n💵 + накопленная прибыль: <b>{format_amount(income)}$</b>" if income > 0 else "") +
            f"\n\n📦 Бизнесов больше нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏢 Купить бизнес", callback_data="biz_shop_view:0")],
                [InlineKeyboardButton(text="🏠 Меню", callback_data="biz_shop_close")],
            ]),
            parse_mode="HTML"
        )
    else:
        new_pos = min(pos, len(new_owned) - 1)
        await callback.message.edit_text(my_biz_text(user, new_pos), reply_markup=my_biz_kb(user, new_pos), parse_mode="HTML")


@router.callback_query(F.data.startswith("mybiz_upgrade:"))
async def cb_mybiz_upgrade(callback: CallbackQuery):
    user_id = callback.from_user.id
    pos = int(callback.data.split(":")[1])
    user = get_user(user_id)
    owned = user.get("businesses", [])
    if pos >= len(owned):
        await callback.answer("❌ Бизнес не найден.", show_alert=True)
        return

    biz_idx = owned[pos]
    biz = BUSINESSES[biz_idx]
    lvl = get_biz_level(user, biz_idx)
    if lvl >= MAX_BIZ_LEVEL:
        await callback.answer("✅ Бизнес уже на максимальном уровне!", show_alert=True)
        return

    next_lvl = lvl + 1
    cost = get_biz_upgrade_cost(biz["price"], next_lvl)
    balance = get_balance(user_id)
    if balance < cost:
        await callback.answer(
            f"❌ Недостаточно средств!\nНужно: {format_amount(cost)}$\nВаш баланс: {format_amount(balance)}$",
            show_alert=True
        )
        return

    update_balance(user_id, balance - cost)
    user = get_user(user_id)
    if "biz_levels" not in user:
        user["biz_levels"] = {}
    user["biz_levels"][str(biz_idx)] = next_lvl
    save_user_data()

    lvl_info = BIZ_LEVELS[next_lvl]
    await callback.answer(
        f"⬆️ {biz['name']} улучшен до уровня {next_lvl} — {lvl_info['name']}!",
        show_alert=True
    )
    user = get_user(user_id)
    await callback.message.edit_text(my_biz_text(user, pos), reply_markup=my_biz_kb(user, pos), parse_mode="HTML")
