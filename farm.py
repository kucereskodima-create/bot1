"""
ФЕРМА — полностью переписана с нуля.
Пассивный майнинг BTC (накопление идёт постоянно, сессий нет).
Покупка / улучшение фермы за $.
"""
import random
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

# ──────────────────────────────────────────────────────────────────────────────
#  Конфиг уровней
# ──────────────────────────────────────────────────────────────────────────────
FARM_LEVELS = {
    1: {"name": "Мини-ферма",    "btc_per_hour": 0.0010, "cost_usd": 50_000,     "cost_btc": 2.0,   "emoji": "💻"},
    2: {"name": "Начальная",     "btc_per_hour": 0.0030, "cost_usd": 200_000,    "cost_btc": 7.0,   "emoji": "🖥"},
    3: {"name": "Средняя",       "btc_per_hour": 0.0080, "cost_usd": 750_000,    "cost_btc": 22.0,  "emoji": "⚡"},
    4: {"name": "Мощная ферма",  "btc_per_hour": 0.0200, "cost_usd": 3_000_000,  "cost_btc": 70.0,  "emoji": "🔥"},
    5: {"name": "Мега-ферма",    "btc_per_hour": 0.0500, "cost_usd": 10_000_000, "cost_btc": None,  "emoji": "🚀"},
}
MAX_FARM_LEVEL = 5
MINING_DURATION = 999_999_999   # совместимость — сессий больше нет

# ──────────────────────────────────────────────────────────────────────────────
#  BTC курс
# ──────────────────────────────────────────────────────────────────────────────
_btc_cache: dict = {"price": 65_000, "updated": 0}


def get_btc_price() -> int:
    now = int(time.time())
    if now - _btc_cache["updated"] > 3600:
        _btc_cache["price"]   = random.randint(60_000, 72_000)
        _btc_cache["updated"] = now
    return _btc_cache["price"]


# ──────────────────────────────────────────────────────────────────────────────
#  Вспомогательные форматтеры
# ──────────────────────────────────────────────────────────────────────────────
def _fmt_btc(n: float) -> str:
    return f"{n:.4f}".rstrip("0").rstrip(".")


def _fmt_usd(n) -> str:
    return f"{int(n):,}".replace(",", ".")


# ──────────────────────────────────────────────────────────────────────────────
#  Работа с данными фермы
# ──────────────────────────────────────────────────────────────────────────────
def get_farm(user_id) -> dict:
    from utils import get_user
    user = get_user(user_id)
    if "farm" not in user:
        user["farm"] = {
            "farm_level": 0,
            "btc_balance": 0.0,
            "last_calc": int(time.time()),
        }
    farm = user["farm"]
    farm["_user_id"] = user_id
    return farm


def flush_farm(farm: dict) -> float:
    """Начислить накопленный BTC с момента последнего расчёта. Возвращает сколько добыто."""
    level = farm.get("farm_level", 0)
    if level == 0:
        return 0.0

    now       = int(time.time())
    last_calc = farm.get("last_calc") or now
    elapsed   = max(0, now - last_calc)          # секунды
    rate      = FARM_LEVELS[level]["btc_per_hour"] / 3600.0

    # Буст от дома (если подключён)
    try:
        from house_shop import get_shop_house_boosts
        uid = farm.get("_user_id")
        if uid:
            boost = get_shop_house_boosts(uid).get("farm_boost", 0)
            if boost:
                rate *= 1 + boost / 100
    except Exception:
        pass

    gained = round(elapsed * rate, 6)
    if gained > 0:
        farm["btc_balance"] = round(farm.get("btc_balance", 0.0) + gained, 6)
    farm["last_calc"] = now
    # совместимость: сессий нет — майнинг всегда «активен» если уровень > 0
    farm["mining_active"] = level > 0
    return gained


# ──────────────────────────────────────────────────────────────────────────────
#  Уведомление (оставлено для совместимости, теперь напоминает собрать BTC)
# ──────────────────────────────────────────────────────────────────────────────
async def notify_mining_done():
    """Каждые 2 минуты начисляет BTC всем фермерам (пассивное накопление)."""
    from utils import user_data, save_user_data
    changed = False
    for uid_str, udata in user_data.items():
        farm = udata.get("farm")
        if not farm or farm.get("farm_level", 0) == 0:
            continue
        flush_farm(farm)
        changed = True
    if changed:
        save_user_data()


# ──────────────────────────────────────────────────────────────────────────────
#  FSM
# ──────────────────────────────────────────────────────────────────────────────
class FarmState(StatesGroup):
    sell_btc = State()


# ──────────────────────────────────────────────────────────────────────────────
#  Текст и клавиатура фермы
# ──────────────────────────────────────────────────────────────────────────────
def _farm_text(user_id: int) -> str:
    from utils import save_user_data
    farm = get_farm(user_id)
    flush_farm(farm)
    save_user_data()

    level     = farm.get("farm_level", 0)
    btc_bal   = farm.get("btc_balance", 0.0)
    btc_price = get_btc_price()

    if level == 0:
        return (
            "🖥 <b>БИТКОИН-ФЕРМА</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "❌ У вас пока нет фермы.\n\n"
            f"💰 Купить первую ферму за <b>50.000$</b>\n"
            f"⚡ Добыча: <b>0.0010 BTC/ч</b>\n\n"
            "Нажмите кнопку ниже, чтобы начать майнинг!"
        )

    info = FARM_LEVELS[level]
    lines = [
        "🖥 <b>БИТКОИН-ФЕРМА</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"",
        f"{info['emoji']} <b>{info['name']}</b>  (ур. {level}/{MAX_FARM_LEVEL})",
        f"⚡ Добыча: <b>{info['btc_per_hour']} BTC/ч</b>",
        f"🔋 Статус: <b>⚡ Активен — пассивный майнинг</b>",
        f"",
        f"₿  Кошелёк: <b>{_fmt_btc(btc_bal)} BTC</b>",
        f"💵 Курс BTC: <b>{_fmt_usd(btc_price)}$</b>",
        f"💰 В деньгах: <b>~{_fmt_usd(int(btc_bal * btc_price))}$</b>",
    ]

    if level < MAX_FARM_LEVEL:
        nxt     = FARM_LEVELS[level + 1]
        btc_c   = nxt.get("cost_btc")
        btc_str = f"  или  <b>{btc_c} BTC</b>" if btc_c else ""
        lines += [
            "",
            f"⬆️ Следующий: <b>{nxt['name']}</b>",
            f"   💵 <b>{_fmt_usd(nxt['cost_usd'])}$</b>{btc_str}  •  +{nxt['btc_per_hour']} BTC/ч",
        ]
    else:
        lines.append("\n🏆 <b>Максимальный уровень!</b>")

    return "\n".join(lines)


def _farm_kb(user_id: int) -> InlineKeyboardMarkup:
    farm  = get_farm(user_id)
    level = farm.get("farm_level", 0)
    rows  = []

    if level == 0:
        rows.append([InlineKeyboardButton(
            text="💰 Купить ферму (50.000$)", callback_data="farm_buy_farm"
        )])
    else:
        rows.append([
            InlineKeyboardButton(text="📥 Собрать BTC",    callback_data="farm_collect"),
            InlineKeyboardButton(text="🔄 Обновить",       callback_data="farm_open"),
        ])
        if level < MAX_FARM_LEVEL:
            nxt        = FARM_LEVELS[level + 1]
            nxt_usd    = nxt["cost_usd"]
            nxt_btc    = nxt["cost_btc"]
            rows.append([InlineKeyboardButton(
                text=f"⚡ Улучшить за {_fmt_usd(nxt_usd)}$ (Быстро)", callback_data="farm_upgrade"
            )])
            if nxt_btc is not None:
                rows.append([InlineKeyboardButton(
                    text=f"₿ Улучшить за {nxt_btc} BTC", callback_data="farm_upgrade_btc"
                )])
        rows.append([
            InlineKeyboardButton(text="💵 Продать BTC",   callback_data="farm_sell_btc"),
            InlineKeyboardButton(text="🛒 Рынок BTC",     callback_data="market_open"),
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ──────────────────────────────────────────────────────────────────────────────
#  Основная функция отправки / обновления панели фермы
# ──────────────────────────────────────────────────────────────────────────────
async def _send_farm(target, user_id: int):
    text = _farm_text(user_id)
    kb   = _farm_kb(user_id)

    try:
        from image_gen import gen_farm_card
        from aiogram.types import BufferedInputFile, InputMediaPhoto
        farm      = get_farm(user_id)
        btc_price = get_btc_price()
        level     = farm.get("farm_level", 1)
        info      = FARM_LEVELS.get(level, FARM_LEVELS[1])
        btc_bal   = farm.get("btc_balance", 0.0)
        status    = "Активен" if level > 0 else "Нет фермы"

        card_data = {
            "farm_name":    info["name"] if level > 0 else "Нет фермы",
            "farm_lvl":     level,
            "btc_per_hour": info["btc_per_hour"] if level > 0 else 0,
            "btc_bal":      _fmt_btc(btc_bal),
            "btc_usd":      _fmt_usd(int(btc_bal * btc_price)),
            "btc_price":    btc_price,
            "status":       status,
            "mining_time":  "",
        }
        buf   = gen_farm_card(card_data)
        photo = BufferedInputFile(buf.read(), filename="farm.png")

        if isinstance(target, CallbackQuery):
            try:
                media = InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
                await target.message.edit_media(media=media, reply_markup=kb)
            except Exception:
                await target.message.answer_photo(photo=photo, caption=text,
                                                  parse_mode="HTML", reply_markup=kb)
            await target.answer()
        else:
            await target.answer_photo(photo=photo, caption=text,
                                      parse_mode="HTML", reply_markup=kb)
        return
    except Exception:
        pass

    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await target.message.answer(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


# ──────────────────────────────────────────────────────────────────────────────
#  Команды / хэндлеры
# ──────────────────────────────────────────────────────────────────────────────

@router.message(F.text.lower().in_(["🖥 ферма", "ферма", "farm", "bitcoin", "btc ферма", "/ферма", "/farm"]))
async def cmd_farm(message: Message):
    await _send_farm(message, message.from_user.id)


@router.callback_query(F.data == "farm_open")
async def cb_farm_open(callback: CallbackQuery):
    await _send_farm(callback, callback.from_user.id)


# ── Покупка фермы ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "farm_buy_farm")
async def cb_buy_farm(callback: CallbackQuery):
    from utils import get_balance, update_balance, save_user_data
    user_id = callback.from_user.id
    farm    = get_farm(user_id)

    if farm.get("farm_level", 0) > 0:
        await callback.answer("У вас уже есть ферма.", show_alert=True)
        return

    cost    = FARM_LEVELS[1]["cost_usd"]
    balance = get_balance(user_id)
    if balance < cost:
        await callback.answer(
            f"❌ Нужно {_fmt_usd(cost)}$\nУ вас: {_fmt_usd(balance)}$",
            show_alert=True
        )
        return

    update_balance(user_id, balance - cost)
    farm["farm_level"]  = 1
    farm["last_calc"]   = int(time.time())
    farm["btc_balance"] = farm.get("btc_balance", 0.0)
    save_user_data()
    await callback.answer("✅ Ферма куплена! Майнинг начался автоматически.", show_alert=True)
    await _send_farm(callback, user_id)


@router.message(F.text.lower().in_(["купить ферму", "ферма купить", "/купить ферму"]))
async def cmd_buy_farm_text(message: Message):
    from utils import get_balance, update_balance, save_user_data
    user_id = message.from_user.id
    farm    = get_farm(user_id)

    if farm.get("farm_level", 0) > 0:
        await message.answer("✅ У вас уже есть ферма! Напиши <code>ферма</code>.", parse_mode="HTML")
        return

    cost    = FARM_LEVELS[1]["cost_usd"]
    balance = get_balance(user_id)
    if balance < cost:
        await message.answer(
            f"❌ Нужно <b>{_fmt_usd(cost)}$</b> для покупки фермы.\n"
            f"💰 У вас: <b>{_fmt_usd(balance)}$</b>",
            parse_mode="HTML"
        )
        return

    update_balance(user_id, balance - cost)
    farm["farm_level"]  = 1
    farm["last_calc"]   = int(time.time())
    save_user_data()
    await message.answer(
        "✅ <b>Ферма куплена!</b>\n\n"
        "⚡ Майнинг запущен автоматически — BTC копится постоянно!\n"
        "Открой <code>ферма</code> чтобы следить за добычей.",
        parse_mode="HTML"
    )


# ── Улучшение фермы ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "farm_upgrade")
async def cb_upgrade_farm(callback: CallbackQuery):
    from utils import get_balance, update_balance, save_user_data
    user_id = callback.from_user.id
    farm    = get_farm(user_id)
    flush_farm(farm)

    level = farm.get("farm_level", 0)
    if level == 0:
        await callback.answer("❌ Сначала купите ферму.", show_alert=True)
        return
    if level >= MAX_FARM_LEVEL:
        await callback.answer("🏆 Максимальный уровень!", show_alert=True)
        return

    cost    = FARM_LEVELS[level + 1]["cost_usd"]
    balance = get_balance(user_id)
    if balance < cost:
        await callback.answer(
            f"❌ Нужно {_fmt_usd(cost)}$\nУ вас: {_fmt_usd(balance)}$",
            show_alert=True
        )
        return

    update_balance(user_id, balance - cost)
    farm["farm_level"] = level + 1
    farm["last_calc"]  = int(time.time())
    save_user_data()
    info = FARM_LEVELS[level + 1]
    await callback.answer(f"✅ Улучшено до {info['name']}!", show_alert=True)
    await _send_farm(callback, user_id)


@router.callback_query(F.data == "farm_upgrade_btc")
async def cb_upgrade_farm_btc(callback: CallbackQuery):
    from utils import save_user_data
    user_id = callback.from_user.id
    farm    = get_farm(user_id)
    flush_farm(farm)

    level = farm.get("farm_level", 0)
    if level == 0:
        await callback.answer("❌ Сначала купите ферму.", show_alert=True)
        return
    if level >= MAX_FARM_LEVEL:
        await callback.answer("🏆 Максимальный уровень!", show_alert=True)
        return

    nxt      = FARM_LEVELS[level + 1]
    btc_cost = nxt.get("cost_btc")
    if btc_cost is None:
        await callback.answer("❌ BTC-улучшение недоступно для этого уровня.", show_alert=True)
        return

    btc_bal = farm.get("btc_balance", 0.0)
    if btc_bal < btc_cost - 1e-9:
        await callback.answer(
            f"❌ Нужно {btc_cost} BTC\nУ вас: {_fmt_btc(btc_bal)} BTC",
            show_alert=True
        )
        return

    farm["btc_balance"] = round(btc_bal - btc_cost, 6)
    farm["farm_level"]  = level + 1
    farm["last_calc"]   = int(time.time())
    save_user_data()

    info = FARM_LEVELS[level + 1]
    await callback.answer(
        f"✅ Улучшено до {info['name']} за {btc_cost} BTC!",
        show_alert=True
    )
    await _send_farm(callback, user_id)


@router.message(F.text.lower().in_(["майнинг улучшить", "улучшить ферму", "ферма улучшить", "/майнинг улучшить"]))
async def cmd_upgrade_text(message: Message):
    from utils import get_balance, update_balance, save_user_data
    user_id = message.from_user.id
    farm    = get_farm(user_id)
    flush_farm(farm)

    level = farm.get("farm_level", 0)
    if level == 0:
        await message.answer("❌ Сначала купите ферму командой <b>купить ферму</b>.", parse_mode="HTML")
        return
    if level >= MAX_FARM_LEVEL:
        await message.answer("🏆 У вас уже максимальный уровень фермы!")
        return

    cost    = FARM_LEVELS[level + 1]["cost_usd"]
    balance = get_balance(user_id)
    if balance < cost:
        await message.answer(
            f"❌ Нужно <b>{_fmt_usd(cost)}$</b> для улучшения.\n"
            f"💰 У вас: <b>{_fmt_usd(balance)}$</b>",
            parse_mode="HTML"
        )
        return

    update_balance(user_id, balance - cost)
    farm["farm_level"] = level + 1
    farm["last_calc"]  = int(time.time())
    save_user_data()
    info = FARM_LEVELS[level + 1]
    await message.answer(
        f"✅ Ферма улучшена до <b>{info['name']}</b>!\n"
        f"⚡ Добыча: <b>{info['btc_per_hour']} BTC/ч</b>\n"
        f"Майнинг продолжается автоматически.",
        parse_mode="HTML"
    )


# ── Сбор BTC ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "farm_collect")
async def cb_farm_collect(callback: CallbackQuery):
    from utils import save_user_data
    farm   = get_farm(callback.from_user.id)
    gained = flush_farm(farm)
    save_user_data()
    if gained > 0:
        await callback.answer(f"📥 Накоплено +{_fmt_btc(gained)} BTC!")
    else:
        await callback.answer("✅ Обновлено")
    await _send_farm(callback, callback.from_user.id)


@router.message(F.text.lower().in_([
    "майнинг собрать", "собрать btc", "собрать биткоин", "/майнинг собрать"
]))
async def cmd_collect_text(message: Message):
    from utils import save_user_data
    user_id   = message.from_user.id
    farm      = get_farm(user_id)
    gained    = flush_farm(farm)
    save_user_data()
    btc_bal   = farm.get("btc_balance", 0.0)
    btc_price = get_btc_price()
    if gained > 0:
        await message.answer(
            f"📥 Собрано <b>+{_fmt_btc(gained)} BTC</b>\n"
            f"₿ Кошелёк: <b>{_fmt_btc(btc_bal)} BTC</b>\n"
            f"💵 (~{_fmt_usd(int(btc_bal * btc_price))}$)",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"⏳ Ещё ничего не накоплено.\n"
            f"₿ Кошелёк: <b>{_fmt_btc(btc_bal)} BTC</b>",
            parse_mode="HTML"
        )


# ── Продать BTC ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "farm_sell_btc")
async def cb_sell_btc_start(callback: CallbackQuery, state: FSMContext):
    from utils import save_user_data
    farm = get_farm(callback.from_user.id)
    flush_farm(farm)
    save_user_data()
    btc_bal   = farm.get("btc_balance", 0.0)
    btc_price = get_btc_price()
    await callback.message.answer(
        f"💵 <b>ПРОДАТЬ БИТКОИНЫ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Курс: <b>1 BTC = {_fmt_usd(btc_price)}$</b>\n"
        f"Ваш BTC: <b>{_fmt_btc(btc_bal)} BTC</b>\n"
        f"Стоимость: <b>~{_fmt_usd(int(btc_bal * btc_price))}$</b>\n\n"
        f"Напишите количество BTC для продажи.\n"
        f"Пример: <code>0.5</code> или <code>все</code>  •  <code>отмена</code> — отменить",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="farm_open")]
        ])
    )
    await state.set_state(FarmState.sell_btc)
    await callback.answer()


@router.message(F.text.lower().in_(["продать btc", "продать биткоин", "продать bitcoin", "/продать btc"]))
async def cmd_sell_btc_text(message: Message, state: FSMContext):
    from utils import save_user_data
    user_id = message.from_user.id
    farm    = get_farm(user_id)
    flush_farm(farm)
    save_user_data()
    btc_bal   = farm.get("btc_balance", 0.0)
    btc_price = get_btc_price()
    if btc_bal <= 0:
        await message.answer("❌ У вас нет BTC для продажи.")
        return
    await message.answer(
        f"💵 <b>ПРОДАТЬ БИТКОИНЫ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Курс: <b>1 BTC = {_fmt_usd(btc_price)}$</b>\n"
        f"Ваш BTC: <b>{_fmt_btc(btc_bal)} BTC</b>\n\n"
        f"Напишите количество BTC.\n"
        f"Пример: <code>0.5</code> или <code>все</code>",
        parse_mode="HTML"
    )
    await state.set_state(FarmState.sell_btc)


@router.message(FarmState.sell_btc)
async def msg_sell_btc(message: Message, state: FSMContext):
    from utils import get_balance, update_balance, save_user_data
    if message.text.strip().lower() == "отмена":
        await state.clear()
        await message.answer("❌ Отменено.")
        return
    user_id = message.from_user.id
    farm    = get_farm(user_id)
    btc_bal = farm.get("btc_balance", 0.0)
    txt     = message.text.strip().lower()
    if txt in ("все", "all", "max"):
        btc_amount = btc_bal
    else:
        try:
            btc_amount = round(float(txt.replace(",", ".")), 6)
        except ValueError:
            await message.answer("❌ Введите число или «все».")
            return
    if btc_amount <= 0 or btc_amount > btc_bal + 1e-9:
        await message.answer(f"❌ Неверная сумма. У вас {_fmt_btc(btc_bal)} BTC.")
        return
    btc_amount = min(btc_amount, btc_bal)
    btc_price  = get_btc_price()
    usd_earned = int(btc_amount * btc_price)
    farm["btc_balance"] = round(btc_bal - btc_amount, 6)
    update_balance(user_id, get_balance(user_id) + usd_earned)
    save_user_data()
    await state.clear()
    await message.answer(
        f"✅ Продано <b>{_fmt_btc(btc_amount)} BTC</b> → <b>{_fmt_usd(usd_earned)}$</b>\n"
        f"Курс: <b>1 BTC = {_fmt_usd(btc_price)}$</b>\n"
        f"₿ Кошелёк: <b>{_fmt_btc(farm['btc_balance'])} BTC</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🖥 Открыть ферму", callback_data="farm_open")]
        ])
    )


@router.callback_query(F.data == "market_open")
async def cb_market_from_farm(callback: CallbackQuery, state: FSMContext):
    from market import market_main_text, _market_main_kb
    await callback.message.answer(
        market_main_text(),
        parse_mode="HTML",
        reply_markup=_market_main_kb()
    )
    await callback.answer()
