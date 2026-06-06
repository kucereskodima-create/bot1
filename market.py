"""
РЫНОК — игровой маркетплейс.
Игроки могут выставлять BTC, машины, дома, бизнес на продажу.
Команда: 🛒 Рынок
"""
import json
import os
import time
import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

MARKET_FILE = os.path.join(os.path.dirname(__file__), "market.json")
PAGE_SIZE = 5

TYPE_LABELS = {
    "btc":  "₿ BTC",
    "case": "📦 Кейс",
}

CANCEL_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❌ Отмена", callback_data="mkt_main")]
])


class MarketState(StatesGroup):
    btc_amount  = State()
    btc_price   = State()
    item_pick   = State()
    item_price  = State()


# ──────────────────────────────────────────────────────────────────────────────
#  Хранилище
# ──────────────────────────────────────────────────────────────────────────────

def _load() -> dict:
    if os.path.exists(MARKET_FILE):
        try:
            with open(MARKET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save(data: dict):
    with open(MARKET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────────────────────────────────────
#  Форматтеры
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_usd(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def _fmt_btc(n: float) -> str:
    return f"{n:.4f}".rstrip("0").rstrip(".")


# ──────────────────────────────────────────────────────────────────────────────
#  Клавиатуры
# ──────────────────────────────────────────────────────────────────────────────

def _market_main_kb() -> InlineKeyboardMarkup:
    data = _load()
    count = len(data)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"🛍 Просмотр ({count} лот.)", callback_data="mkt_browse:0"),
        ],
        [
            InlineKeyboardButton(text="➕ Выставить товар",   callback_data="mkt_list_start"),
            InlineKeyboardButton(text="📦 Мои объявления",    callback_data="mkt_my:0"),
        ],
        [InlineKeyboardButton(text="🔄 Обновить",            callback_data="mkt_main")],
    ])


def _browse_kb(page: int, items: list, total: int) -> InlineKeyboardMarkup:
    rows = []
    for lid, listing in items:
        t     = TYPE_LABELS.get(listing["type"], listing["type"])
        name  = listing.get("item_name", t)
        price = _fmt_usd(listing["price"])
        rows.append([InlineKeyboardButton(
            text=f"{t} · {name} — {price}$",
            callback_data=f"mkt_view:{lid}"
        )])

    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"mkt_browse:{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{pages}", callback_data="mkt_noop"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"mkt_browse:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="mkt_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _view_kb(lid: str, is_owner: bool) -> InlineKeyboardMarkup:
    rows = []
    if is_owner:
        rows.append([InlineKeyboardButton(text="🗑 Снять с продажи", callback_data=f"mkt_cancel:{lid}")])
    else:
        rows.append([InlineKeyboardButton(text="💰 Купить", callback_data=f"mkt_buy:{lid}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад к рынку", callback_data="mkt_browse:0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _my_kb(page: int, items: list, total: int) -> InlineKeyboardMarkup:
    rows = []
    for lid, listing in items:
        t    = TYPE_LABELS.get(listing["type"], listing["type"])
        name = listing.get("item_name", t)
        price = _fmt_usd(listing["price"])
        rows.append([
            InlineKeyboardButton(text=f"{t} · {name} — {price}$", callback_data=f"mkt_view:{lid}"),
        ])

    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"mkt_my:{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{pages}", callback_data="mkt_noop"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"mkt_my:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="mkt_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _type_pick_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="₿ BTC",       callback_data="mkt_type:btc"),
            InlineKeyboardButton(text="📦 Кейс",      callback_data="mkt_type:case"),
        ],
        [InlineKeyboardButton(text="❌ Отмена",       callback_data="mkt_main")],
    ])


# ──────────────────────────────────────────────────────────────────────────────
#  Текст главной
# ──────────────────────────────────────────────────────────────────────────────

def market_main_text() -> str:
    data = _load()
    active = len(data)
    btc_count  = sum(1 for v in data.values() if v["type"] == "btc")
    case_count = sum(1 for v in data.values() if v["type"] == "case")
    lines = [
        "🛒 <b>РЫНОК BLACKLINE</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        f"📦 Активных лотов: <b>{active}</b>",
        f"  ₿ BTC: <b>{btc_count}</b>  📦 Кейсы: <b>{case_count}</b>",
        "",
        "💡 Выставляй товары — другие игроки могут купить их у тебя.",
        "💸 Цены устанавливает сам продавец.",
    ]
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
#  Команда / кнопка меню
# ──────────────────────────────────────────────────────────────────────────────

@router.message(F.text.lower().in_(["🛒 рынок", "рынок", "/рынок", "/market"]))
async def cmd_market(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(market_main_text(), parse_mode="HTML", reply_markup=_market_main_kb())


# ──────────────────────────────────────────────────────────────────────────────
#  Главная через callback
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "mkt_main")
async def cb_mkt_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text(
            market_main_text(), parse_mode="HTML", reply_markup=_market_main_kb()
        )
    except Exception:
        await callback.message.answer(
            market_main_text(), parse_mode="HTML", reply_markup=_market_main_kb()
        )
    await callback.answer()


@router.callback_query(F.data == "mkt_noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
#  Просмотр рынка
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mkt_browse:"))
async def cb_browse(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    data = _load()
    all_items = sorted(data.items(), key=lambda x: x[1].get("created_at", 0), reverse=True)
    total = len(all_items)

    if total == 0:
        try:
            await callback.message.edit_text(
                "🛒 <b>Рынок пуст</b>\n\nПока нет ни одного объявления. Будь первым!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Выставить товар", callback_data="mkt_list_start")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="mkt_main")],
                ])
            )
        except Exception:
            await callback.message.answer(
                "🛒 <b>Рынок пуст</b>\n\nПока нет ни одного объявления.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Выставить товар", callback_data="mkt_list_start")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="mkt_main")],
                ])
            )
        await callback.answer()
        return

    page = max(0, min(page, (total - 1) // PAGE_SIZE))
    start = page * PAGE_SIZE
    page_items = all_items[start:start + PAGE_SIZE]

    lines = ["🛒 <b>РЫНОК — все лоты</b>", "━━━━━━━━━━━━━━━━━━━━", ""]
    for i, (lid, lst) in enumerate(page_items, start + 1):
        t     = TYPE_LABELS.get(lst["type"], lst["type"])
        name  = lst.get("item_name", t)
        price = _fmt_usd(lst["price"])
        seller = lst.get("seller_name", "?")
        lines.append(f"<b>{i}.</b> {t} · <b>{name}</b>\n    💰 {price}$ · продавец: {seller}")

    text = "\n".join(lines)
    kb   = _browse_kb(page, page_items, total)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
#  Просмотр конкретного лота
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mkt_view:"))
async def cb_view(callback: CallbackQuery):
    lid  = callback.data.split(":", 1)[1]
    data = _load()
    lst  = data.get(lid)
    if not lst:
        await callback.answer("❌ Лот не найден или уже продан.", show_alert=True)
        return

    user_id  = callback.from_user.id
    is_owner = (lst["seller_id"] == user_id)
    t        = TYPE_LABELS.get(lst["type"], lst["type"])
    name     = lst.get("item_name", t)
    price    = _fmt_usd(lst["price"])
    seller   = lst.get("seller_name", "?")
    desc     = lst.get("item_desc", "")

    lines = [
        f"🏷 <b>Лот: {t} · {name}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"💰 Цена: <b>{price}$</b>",
        f"👤 Продавец: <b>{seller}</b>",
    ]
    if desc:
        lines.append(f"📝 {desc}")
    if is_owner:
        lines.append("\n<i>Это ваш лот.</i>")

    text = "\n".join(lines)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_view_kb(lid, is_owner))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=_view_kb(lid, is_owner))
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
#  Покупка лота
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mkt_buy:"))
async def cb_buy(callback: CallbackQuery):
    from utils import get_user, get_balance, update_balance, save_user_data
    from config import bot as tg_bot

    lid     = callback.data.split(":", 1)[1]
    data    = _load()
    lst     = data.get(lid)
    if not lst:
        await callback.answer("❌ Лот уже куплен или снят.", show_alert=True)
        return

    user_id   = callback.from_user.id
    seller_id = lst["seller_id"]
    if seller_id == user_id:
        await callback.answer("❌ Нельзя купить у самого себя.", show_alert=True)
        return

    price   = lst["price"]
    balance = get_balance(user_id)
    if balance < price:
        await callback.answer(
            f"❌ Недостаточно средств.\nНужно: {_fmt_usd(price)}$\nВаш баланс: {_fmt_usd(balance)}$",
            show_alert=True
        )
        return

    lst_type = lst["type"]
    buyer    = get_user(user_id)
    seller   = get_user(seller_id)

    if lst_type == "btc":
        btc_amount = lst.get("btc_amount", 0.0)
        from farm import get_farm, flush_farm
        buyer_farm = get_farm(user_id)
        buyer_farm["btc_balance"] = round(buyer_farm.get("btc_balance", 0.0) + btc_amount, 6)

    elif lst_type == "case":
        item = lst.get("item_data", {})
        buyer.setdefault("assets", {}).setdefault("cases", []).append(item)

    update_balance(user_id, balance - price)
    update_balance(seller_id, get_balance(seller_id) + price)

    del data[lid]
    _save(data)
    save_user_data()

    t         = TYPE_LABELS.get(lst_type, lst_type)
    item_name = lst.get("item_name", t)
    buyer_name  = buyer.get("name", "Без имени")
    seller_name = lst.get("seller_name", "?")

    await callback.message.edit_text(
        f"✅ <b>Покупка совершена!</b>\n\n"
        f"{t} · <b>{item_name}</b>\n"
        f"💰 Цена: <b>{_fmt_usd(price)}$</b>\n\n"
        f"Товар добавлен в ваш инвентарь.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 На рынок", callback_data="mkt_main")]
        ])
    )
    try:
        await tg_bot.send_message(
            seller_id,
            f"💸 <b>Ваш товар куплен!</b>\n\n"
            f"{t} · <b>{item_name}</b>\n"
            f"💰 Вы получили: <b>{_fmt_usd(price)}$</b>\n"
            f"👤 Покупатель: {buyer_name}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
#  Снять с продажи
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mkt_cancel:"))
async def cb_cancel_listing(callback: CallbackQuery):
    from utils import get_user, save_user_data
    lid     = callback.data.split(":", 1)[1]
    data    = _load()
    lst     = data.get(lid)
    if not lst:
        await callback.answer("❌ Лот не найден.", show_alert=True)
        return
    if lst["seller_id"] != callback.from_user.id:
        await callback.answer("❌ Это не ваш лот.", show_alert=True)
        return

    lst_type = lst["type"]
    user_id  = callback.from_user.id
    user     = get_user(user_id)

    if lst_type == "btc":
        from farm import get_farm
        farm = get_farm(user_id)
        farm["btc_balance"] = round(farm.get("btc_balance", 0.0) + lst.get("btc_amount", 0.0), 6)

    elif lst_type == "case":
        user.setdefault("assets", {}).setdefault("cases", []).append(lst.get("item_data", {}))

    del data[lid]
    _save(data)
    save_user_data()

    t         = TYPE_LABELS.get(lst_type, lst_type)
    item_name = lst.get("item_name", t)

    await callback.message.edit_text(
        f"✅ Лот снят с продажи.\n{t} · <b>{item_name}</b> возвращён вам.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 На рынок", callback_data="mkt_main")]
        ])
    )
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
#  Мои объявления
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mkt_my:"))
async def cb_my_listings(callback: CallbackQuery):
    user_id = callback.from_user.id
    page    = int(callback.data.split(":")[1])
    data    = _load()
    mine    = [(lid, lst) for lid, lst in data.items() if lst["seller_id"] == user_id]
    mine.sort(key=lambda x: x[1].get("created_at", 0), reverse=True)
    total = len(mine)

    if total == 0:
        try:
            await callback.message.edit_text(
                "📦 <b>Ваши объявления</b>\n\nУ вас нет активных объявлений.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Выставить товар", callback_data="mkt_list_start")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="mkt_main")],
                ])
            )
        except Exception:
            await callback.message.answer(
                "📦 <b>Ваши объявления</b>\n\nУ вас нет активных объявлений.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Выставить товар", callback_data="mkt_list_start")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="mkt_main")],
                ])
            )
        await callback.answer()
        return

    page  = max(0, min(page, (total - 1) // PAGE_SIZE))
    start = page * PAGE_SIZE
    page_items = mine[start:start + PAGE_SIZE]

    text = "📦 <b>Ваши объявления</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    kb   = _my_kb(page, page_items, total)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
#  Выставить товар — выбор типа
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "mkt_list_start")
async def cb_list_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text(
            "➕ <b>Выставить товар</b>\n\nЧто хочешь продать?",
            parse_mode="HTML",
            reply_markup=_type_pick_kb()
        )
    except Exception:
        await callback.message.answer(
            "➕ <b>Выставить товар</b>\n\nЧто хочешь продать?",
            parse_mode="HTML",
            reply_markup=_type_pick_kb()
        )
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
#  Выставить BTC
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "mkt_type:btc")
async def cb_type_btc(callback: CallbackQuery, state: FSMContext):
    from farm import get_farm, flush_farm, _fmt_btc as fb, get_btc_price
    from utils import save_user_data
    farm = get_farm(callback.from_user.id)
    flush_farm(farm)
    save_user_data()
    btc_bal = farm.get("btc_balance", 0.0)
    if btc_bal <= 0:
        await callback.answer("❌ У вас нет BTC для продажи.", show_alert=True)
        return
    rate = get_btc_price()
    await state.update_data(list_type="btc")
    await state.set_state(MarketState.btc_amount)
    await callback.message.answer(
        f"₿ <b>Продажа BTC</b>\n\n"
        f"Ваш BTC: <b>{fb(btc_bal)} BTC</b>\n"
        f"💵 Курс биржи: <b>{_fmt_usd(rate)}$</b>\n\n"
        f"Введи количество BTC для продажи:\n"
        f"Пример: <code>0.5</code> или <code>все</code>",
        parse_mode="HTML",
        reply_markup=CANCEL_KB
    )
    await callback.answer()


@router.message(MarketState.btc_amount)
async def msg_btc_amount(message: Message, state: FSMContext):
    from farm import get_farm, flush_farm, get_btc_price
    from utils import save_user_data
    txt = message.text.strip().lower()
    if txt in ("отмена", "cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 На рынок", callback_data="mkt_main")]
        ]))
        return
    farm    = get_farm(message.from_user.id)
    btc_bal = farm.get("btc_balance", 0.0)
    if txt in ("все", "all", "max"):
        amount = btc_bal
    else:
        try:
            amount = round(float(txt.replace(",", ".")), 6)
        except ValueError:
            await message.answer("❌ Введи число, например <code>0.5</code>", parse_mode="HTML")
            return
    if amount <= 0 or amount > btc_bal + 1e-9:
        await message.answer(f"❌ Неверная сумма. У вас {_fmt_btc(btc_bal)} BTC.")
        return
    amount = min(amount, btc_bal)
    rate   = get_btc_price()
    await state.update_data(btc_amount=amount)
    await state.set_state(MarketState.btc_price)
    await message.answer(
        f"₿ Количество: <b>{_fmt_btc(amount)} BTC</b>\n\n"
        f"Введи цену за <b>1 BTC</b> в долларах:\n"
        f"Биржевой курс: <b>{_fmt_usd(rate)}$</b>\n"
        f"Пример: <code>{rate}</code>",
        parse_mode="HTML",
        reply_markup=CANCEL_KB
    )


@router.message(MarketState.btc_price)
async def msg_btc_price(message: Message, state: FSMContext):
    from utils import get_user, save_user_data
    txt = message.text.strip().lower()
    if txt in ("отмена", "cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 На рынок", callback_data="mkt_main")]
        ]))
        return
    try:
        price_per_btc = int(float(txt.replace(",", ".").replace(" ", "")))
    except ValueError:
        await message.answer("❌ Введи цену числом, например <code>65000</code>", parse_mode="HTML")
        return
    if price_per_btc <= 0:
        await message.answer("❌ Цена должна быть больше 0.")
        return

    data_st   = await state.get_data()
    btc_amount = data_st["btc_amount"]
    total_price = int(btc_amount * price_per_btc)
    user_id    = message.from_user.id

    from farm import get_farm
    farm = get_farm(user_id)
    if farm.get("btc_balance", 0.0) < btc_amount - 1e-9:
        await message.answer("❌ Недостаточно BTC (возможно уже потрачено).")
        await state.clear()
        return
    farm["btc_balance"] = round(farm["btc_balance"] - btc_amount, 6)
    save_user_data()

    user = get_user(user_id)
    lid  = str(uuid.uuid4())[:8]
    data = _load()
    data[lid] = {
        "id":          lid,
        "seller_id":   user_id,
        "seller_name": user.get("name", "Без имени"),
        "type":        "btc",
        "item_name":   f"{_fmt_btc(btc_amount)} BTC",
        "item_desc":   f"₿ {_fmt_btc(btc_amount)} BTC · по {_fmt_usd(price_per_btc)}$/BTC",
        "btc_amount":  btc_amount,
        "price":       total_price,
        "created_at":  int(time.time()),
    }
    _save(data)
    await state.clear()
    await message.answer(
        f"✅ <b>Лот выставлен!</b>\n\n"
        f"₿ <b>{_fmt_btc(btc_amount)} BTC</b>\n"
        f"💰 Цена: <b>{_fmt_usd(total_price)}$</b>\n"
        f"(по {_fmt_usd(price_per_btc)}$/BTC)\n\n"
        f"Другие игроки смогут купить твой лот.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 На рынок", callback_data="mkt_main")]
        ])
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Выставить кейс
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "mkt_type:case")
async def cb_type_case(callback: CallbackQuery, state: FSMContext):
    from utils import get_user
    from cases import CASES
    user  = get_user(callback.from_user.id)
    cases = user.get("assets", {}).get("cases", [])
    if not cases:
        await callback.answer("❌ У вас нет кейсов для продажи.", show_alert=True)
        return
    counts = {}
    for c in cases:
        cid = c.get("case_id", "unicorn")
        counts[cid] = counts.get(cid, 0) + 1
    rows = []
    for cid, cnt in counts.items():
        cinfo = CASES.get(cid, {})
        cname = cinfo.get("name", cid)
        rows.append([InlineKeyboardButton(text=f"{cname} ×{cnt}", callback_data=f"mkt_pick_case:{cid}")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="mkt_main")])
    await state.update_data(list_type="case")
    await state.set_state(MarketState.item_pick)
    try:
        await callback.message.edit_text(
            "📦 <b>Выбери кейс для продажи:</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
    except Exception:
        await callback.message.answer(
            "📦 <b>Выбери кейс для продажи:</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("mkt_pick_case:"), MarketState.item_pick)
async def cb_pick_case(callback: CallbackQuery, state: FSMContext):
    from utils import get_user
    from cases import CASES
    case_id = callback.data.split(":")[1]
    user    = get_user(callback.from_user.id)
    cases   = user.get("assets", {}).get("cases", [])
    idx = next((i for i, c in enumerate(cases) if c.get("case_id") == case_id), None)
    if idx is None:
        await callback.answer("❌ Кейс не найден.", show_alert=True)
        return
    case_item = cases[idx]
    cinfo = CASES.get(case_id, {})
    cname = cinfo.get("name", case_id)
    await state.update_data(item_idx=idx, item_data=case_item, item_name=cname, case_id=case_id)
    await state.set_state(MarketState.item_price)
    await callback.message.answer(
        f"📦 <b>{cname}</b>\n\n"
        f"Введи цену продажи в $:\nПример: <code>10000</code>",
        parse_mode="HTML",
        reply_markup=CANCEL_KB
    )
    await callback.answer()


# ──────────────────────────────────────────────────────────────────────────────
#  Ввод цены для предметов
# ──────────────────────────────────────────────────────────────────────────────

@router.message(MarketState.item_price)
async def msg_item_price(message: Message, state: FSMContext):
    from utils import get_user, save_user_data
    txt = message.text.strip().lower()
    if txt in ("отмена", "cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 На рынок", callback_data="mkt_main")]
        ]))
        return
    try:
        price = int(float(txt.replace(",", ".").replace(" ", "")))
    except ValueError:
        await message.answer("❌ Введи цену числом, например <code>1000000</code>", parse_mode="HTML")
        return
    if price <= 0:
        await message.answer("❌ Цена должна быть больше 0.")
        return

    data_st   = await state.get_data()
    lst_type  = data_st["list_type"]
    item_data = data_st.get("item_data", {})
    item_name = data_st.get("item_name", "Товар")
    item_idx  = data_st.get("item_idx")
    user_id   = message.from_user.id
    user      = get_user(user_id)

    if lst_type == "case":
        cases = user.get("assets", {}).get("cases", [])
        case_id = data_st.get("case_id")
        if item_idx is None or item_idx >= len(cases):
            await message.answer("❌ Кейс не найден.")
            await state.clear()
            return
        cases.pop(item_idx)

    save_user_data()

    lid  = str(uuid.uuid4())[:8]
    data = _load()
    t    = TYPE_LABELS.get(lst_type, lst_type)
    data[lid] = {
        "id":          lid,
        "seller_id":   user_id,
        "seller_name": user.get("name", "Без имени"),
        "type":        lst_type,
        "item_name":   item_name,
        "item_desc":   f"{t} · {item_name}",
        "item_data":   item_data,
        "price":       price,
        "created_at":  int(time.time()),
    }
    _save(data)
    await state.clear()

    await message.answer(
        f"✅ <b>Лот выставлен!</b>\n\n"
        f"{t} · <b>{item_name}</b>\n"
        f"💰 Цена: <b>{_fmt_usd(price)}$</b>\n\n"
        f"Другие игроки смогут купить твой лот.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 На рынок", callback_data="mkt_main")]
        ])
    )
