"""
Команда инфо — компактная карточка игрока + кнопки продажи донат-имущества.

Использование:
  инфо            — своя карточка
  инфо 123        — по game_id / tg_id / @username
  (ответ на сообщение) инфо — карточка того, кому отвечаешь
"""
import datetime
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile,
)
from utils import (
    get_user, get_balance, format_amount,
    save_user_data, clickable_name, find_user_by_identifier,
)
import utils

router = Router()

SELL_REFUND_PCT = 50   # % возврата DC при продаже донат-предмета

# ─── Должности по работе и уровню ──────────────────────────────────────────────

JOB_RANKS = {
    "chef":        ["Стажёр-повар",    "Повар",           "Шеф-повар",       "Старший шеф",    "Мастер-шеф"],
    "engineer":    ["Стажёр",          "Мл. инженер",     "Инженер",         "Ст. инженер",    "Гл. инженер"],
    "police":      ["Курсант",         "Рядовой",         "Офицер",          "Капитан",        "Полковник"],
    "programmer":  ["Стажёр",          "Junior",          "Middle",          "Senior",         "Tech Lead"],
    "firefighter": ["Стажёр",          "Пожарный",        "Ст. пожарный",    "Лейтенант",      "Брандмейстер"],
    "doctor":      ["Интерн",          "Врач",            "Ст. врач",        "Доктор",         "Главврач"],
}
_LEVEL_BREAKS = [0, 10, 20, 35, 50]

def _job_title(job_id: str, level: int) -> str:
    ranks = JOB_RANKS.get(job_id, ["Стажёр", "Работник", "Специалист", "Ст. специалист", "Эксперт"])
    idx = 0
    for i, threshold in enumerate(_LEVEL_BREAKS):
        if level >= threshold:
            idx = i
    return ranks[min(idx, len(ranks) - 1)]

def _fmt_xp(n: int) -> str:
    s = str(abs(int(n)))
    parts = []
    while s:
        parts.append(s[-3:])
        s = s[:-3]
    return ".".join(reversed(parts))

# ─── Получение данных игрока ──────────────────────────────────────────────────

def _resolve_target(message: Message) -> tuple[int | None, dict | None]:
    """
    Определяет цель команды:
    - reply → тот, кому ответили
    - аргумент → поиск по id/username
    - ничего → сам отправитель
    Возвращает (tg_user_id, user_data) или (None, None)
    """
    # 1) Ответ на сообщение
    if message.reply_to_message:
        uid = message.reply_to_message.from_user.id
        return uid, get_user(uid)

    # 2) Аргумент в тексте
    parts = message.text.strip().split(None, 1)
    if len(parts) > 1:
        arg = parts[1].strip()
        tid, tdata = find_user_by_identifier(arg, utils.user_data)
        if tid:
            return tid, tdata
        return None, None

    # 3) Сам отправитель
    uid = message.from_user.id
    return uid, get_user(uid)


# ─── Построение текста карточки ───────────────────────────────────────────────

def _info_text(uid: int, u: dict) -> str:
    import time as _time
    from donate import (
        get_donate_user_data, DONATE_BUSINESSES, DONATE_HOUSES,
        DONATE_CARS, accumulate_biz_income,
    )
    from racing_shop import RACING_CARS
    from house_shop import SHOP_HOUSES
    from business_shop import BUSINESSES
    from farm import get_farm, get_btc_price, flush_farm, _fmt_btc

    name  = u.get("name", "Без имени")
    gid   = u.get("game_id", "—")
    bal   = u.get("balance", 0)
    bank  = u.get("user_bank", 0)
    dc    = u.get("donate_coins", 0)
    level = u.get("level", 1)
    exp   = u.get("experience", 0)
    next_exp = level * 100

    # Донат-данные
    don = get_donate_user_data(u)
    vip_badge = " ⭐" if don.get("vip") else ""

    # ── BTC ──
    try:
        farm = get_farm(uid)
        flush_farm(farm)
        btc_bal = farm.get("btc_balance", 0.0)
        btc_price = get_btc_price()
        btc_usd = int(btc_bal * btc_price)
    except Exception:
        btc_bal = 0.0
        btc_usd = 0

    # ── Дом ──
    don_house_key = don.get("house")
    shop_house_key = u.get("shop_house")
    assets_houses = u.get("assets", {}).get("houses", [])
    if don_house_key and don_house_key in DONATE_HOUSES:
        house_name = DONATE_HOUSES[don_house_key]["name"]
    elif shop_house_key and shop_house_key in SHOP_HOUSES:
        house_name = SHOP_HOUSES[shop_house_key]["name"]
    elif assets_houses:
        house_name = assets_houses[-1].get("name", "Нет")
    else:
        house_name = u.get("houses") or "Нет"

    # ── Авто ──
    don_car_key = don.get("car")
    race_car = u.get("race_car")
    assets_cars = u.get("assets", {}).get("cars", [])
    shop_car_key = u.get("shop_car")
    if don_car_key and don_car_key in DONATE_CARS:
        car_name = DONATE_CARS[don_car_key]["name"]
    elif race_car and "idx" in race_car:
        idx = race_car["idx"]
        car_name = RACING_CARS[idx]["name"] if 0 <= idx < len(RACING_CARS) else "Нет"
    elif shop_car_key:
        from auto_shop import SHOP_CARS
        car_name = SHOP_CARS[shop_car_key]["name"] if shop_car_key in SHOP_CARS else "Нет"
    elif assets_cars:
        car_name = assets_cars[-1].get("name", "Нет")
    else:
        car_name = u.get("cars") or "Нет"

    # ── Бизнес ──
    don_biz_key = don.get("business")
    owned_bizs = u.get("businesses", [])
    if don_biz_key and don_biz_key in DONATE_BUSINESSES:
        biz_name = DONATE_BUSINESSES[don_biz_key]["name"]
    elif owned_bizs:
        first_idx = owned_bizs[0]
        biz_name = BUSINESSES[first_idx]["name"] if 0 <= first_idx < len(BUSINESSES) else "Нет"
    else:
        biz_name = u.get("business") or "Нет"

    # ── Работа и должность ──
    work_id = u.get("current_work")
    work_map = {
        "engineer":    "Инженер",
        "chef":        "Повар",
        "police":      "Полицейский",
        "programmer":  "Программист",
        "firefighter": "Пожарный",
        "doctor":      "Доктор",
    }
    work_name  = work_map.get(work_id, "Не выбрана")
    job_title  = _job_title(work_id, level) if work_id else "—"

    # ── Статус онлайн ──
    from utils import format_last_seen as _fmt_ls
    status_line = _fmt_ls(u.get("last_seen", 0))

    # ── Рейтинг по балансу ──
    total_wealth = bal + bank + btc_usd
    all_sorted = sorted(utils.user_data.values(),
                        key=lambda x: x.get("balance", 0), reverse=True)
    rank = next(
        (i + 1 for i, x in enumerate(all_sorted)
         if str(x.get("game_id")) == str(gid)), "—"
    )

    lines = [
        f"👤 <b>{name}</b>{vip_badge}  •  🆔 <code>{gid}</code>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"",
        f"💰 Баланс: <b>{format_amount(bal)}$</b>",
        f"🏦 Банк: <b>{format_amount(bank)}$</b>",
        f"₿ BTC: <b>{_fmt_btc(btc_bal)}</b>  (~{format_amount(btc_usd)}$)",
        f"💎 DC: <b>{dc}</b>",
        f"",
        f"🏠 Дом: <b>{house_name}</b>",
        f"🚗 Авто: <b>{car_name}</b>",
        f"🏢 Бизнес: <b>{biz_name}</b>",
    ]

    if work_id:
        lines += [
            f"",
            f"💼 Работа: <b>{work_name}</b>  ({job_title})",
        ]

    # ── Клан ──
    try:
        from clans import get_user_clan as _get_clan
        _clan = _get_clan(uid)
        if _clan:
            _clan_name = _clan.get("name", "—")
            _owner_id  = _clan.get("owner")
            _deps      = _clan.get("deputies", [])
            if _owner_id == uid:
                _clan_role = "👑 Лидер"
            elif uid in _deps:
                _clan_role = "⭐ Зам"
            else:
                _clan_role = "👥 Участник"
        else:
            _clan_name = "Нет"
            _clan_role = None
    except Exception:
        _clan_name = "Нет"
        _clan_role = None

    # ── Роль игрока ──
    from admin_roles import get_role as _get_admin_role
    _ROLE_NAMES = {
        "founder":    "👑 Основатель",
        "zam_ld":     "⭐ Зам лидера",
        "tech_admin": "🔧 Тех. Админ",
        "admin":      "🛡 Администратор",
        "designer":   "🎨 Дизайнер",
        "moder":      "🔨 Модератор",
        "follower":   "👁 Фолер",
    }
    _admin_role = _ROLE_NAMES.get(_get_admin_role(uid), "")

    clan_line = f"🛡 Клан: <b>{_clan_name}</b>"
    if _clan_role:
        clan_line += f"  ({_clan_role})"

    lines += ["", clan_line]
    if _admin_role:
        lines.append(f"🎖 Роль: <b>{_admin_role}</b>")

    lines += [
        f"",
        f"📈 Ур. <b>{level}</b>  ⚡ {_fmt_xp(exp)}/{_fmt_xp(next_exp)} XP",
        f"🏆 Место в топе: <b>#{rank}</b>",
        f"🌐 Онлайн: {status_line}",
    ]

    return "\n".join(lines)


def _info_kb(target_uid: int, viewer_uid: int) -> InlineKeyboardMarkup:
    """Кнопки профиля игрока."""
    rows = [
        [InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data=f"pi_refresh:{target_uid}"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── Отправка карточки ────────────────────────────────────────────────────────

async def _send_info(message_or_cb, target_uid: int, viewer_uid: int, edit: bool = False):
    u    = get_user(target_uid)
    text = _info_text(target_uid, u)
    kb   = _info_kb(target_uid, viewer_uid)

    # Маленькая карточка профиля (изображение)
    photo = None
    try:
        from image_gen import gen_profile_card
        from farm import get_farm, get_btc_price, flush_farm, FARM_LEVELS, _fmt_btc
        from donate import get_donate_user_data

        farm      = get_farm(target_uid)
        btc_bal   = farm.get("btc_balance", 0.0)
        farm_lvl  = max(farm.get("farm_level", 0), 1)
        btc_price = get_btc_price()
        farm_info = FARM_LEVELS.get(farm_lvl, FARM_LEVELS[1])
        farm_act  = farm.get("farm_level", 0) > 0
        don       = get_donate_user_data(u)

        from racing_shop import RACING_CARS
        rc       = u.get("race_car")
        race_str = RACING_CARS[rc["idx"]]["name"] if rc and "idx" in rc else "Нет"

        all_sorted = sorted(utils.user_data.values(),
                            key=lambda x: x.get("balance", 0), reverse=True)
        rank = next(
            (i + 1 for i, x in enumerate(all_sorted)
             if str(x.get("game_id")) == str(u.get("game_id"))), "—"
        )
        import datetime
        reg_ts   = u.get("registration_date")
        reg_date = datetime.datetime.fromtimestamp(reg_ts).strftime("%d.%m.%Y") if reg_ts else "—"

        card_data = {
            "name":        u.get("name", "Игрок"),
            "game_id":     u.get("game_id", "—"),
            "balance_fmt": format_amount(u.get("balance", 0)),
            "bank_fmt":    format_amount(u.get("user_bank", 0)),
            "btc_bal":     _fmt_btc(btc_bal),
            "btc_usd":     format_amount(int(btc_bal * btc_price)),
            "dc":          u.get("donate_coins", 0),
            "level":       u.get("level", 1),
            "exp":         u.get("experience", 0),
            "next_exp":    u.get("level", 1) * 100,
            "work":        {
                "engineer": "Инженер", "chef": "Повар",
                "police": "Полицейский", "programmer": "Программист",
                "firefighter": "Пожарный", "doctor": "Доктор",
            }.get(u.get("current_work"), "—"),
            "car":         (
                DONATE_CARS[don.get("car")]["name"] if don.get("car") and don.get("car") in DONATE_CARS
                else RACING_CARS[u["race_car"]["idx"]]["name"] if u.get("race_car") and "idx" in u["race_car"] and 0 <= u["race_car"]["idx"] < len(RACING_CARS)
                else u.get("assets", {}).get("cars", [{}])[-1].get("name") if u.get("assets", {}).get("cars")
                else u.get("cars") or "Нет"
            ),
            "house":       (
                DONATE_HOUSES[don.get("house")]["name"] if don.get("house") and don.get("house") in DONATE_HOUSES
                else SHOP_HOUSES[u.get("shop_house")]["name"] if u.get("shop_house") and u.get("shop_house") in SHOP_HOUSES
                else u.get("assets", {}).get("houses", [{}])[-1].get("name") if u.get("assets", {}).get("houses")
                else u.get("houses") or "Нет"
            ),
            "farm_name":   farm_info["name"],
            "farm_lvl":    farm_lvl,
            "farm_status": "Активен" if farm_act else "Нет фермы",
            "race_car":    race_str,
            "rank":        rank,
            "reg_date":    reg_date,
            "vip":         don.get("vip"),
        }
        buf   = gen_profile_card(card_data)
        photo = BufferedInputFile(buf.read(), filename="info.png")
    except Exception:
        pass

    if isinstance(message_or_cb, CallbackQuery):
        msg = message_or_cb.message
        if edit and photo:
            from aiogram.types import InputMediaPhoto
            try:
                await msg.edit_media(
                    InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"),
                    reply_markup=kb
                )
                await message_or_cb.answer()
                return
            except Exception:
                pass
        if photo:
            await msg.answer_photo(photo=photo, caption=text,
                                   parse_mode="HTML", reply_markup=kb)
        else:
            await msg.answer(text, parse_mode="HTML", reply_markup=kb)
        await message_or_cb.answer()
    else:
        if photo:
            await message_or_cb.answer_photo(photo=photo, caption=text,
                                             parse_mode="HTML", reply_markup=kb)
        else:
            await message_or_cb.answer(text, parse_mode="HTML", reply_markup=kb)


# ─── Хэндлеры ─────────────────────────────────────────────────────────────────

@router.message(F.text.lower().regexp(r'^(инфо|/инфо|чек|/чек|info|/info)(\s+.*)?$'))
async def cmd_info(message: Message):
    from admin_roles import is_admin_any as _is_admin
    if not _is_admin(message.from_user.id):
        return
    target_uid, target_data = _resolve_target(message)
    if target_uid is None:
        await message.answer(
            "❌ Игрок не найден.\n"
            "Используй: <code>инфо [ID / @username / gameID]</code>\n"
            "Или ответь на сообщение игрока командой <code>инфо</code>",
            parse_mode="HTML"
        )
        return
    await _send_info(message, target_uid, message.from_user.id)


# ─── Обновление карточки ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pi_refresh:"))
async def cb_pi_refresh(callback: CallbackQuery):
    target_uid = int(callback.data.split(":")[1])
    await _send_info(callback, target_uid, callback.from_user.id, edit=True)


# ─── Продажа донат-бизнеса ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pi_sell_biz:"))
async def cb_pi_sell_biz(callback: CallbackQuery):
    from donate import get_donate_user_data, DONATE_BUSINESSES
    from admin_roles import get_role

    target_uid  = int(callback.data.split(":")[1])
    viewer_uid  = callback.from_user.id
    is_owner    = (target_uid == viewer_uid)
    viewer_role = get_role(viewer_uid)
    has_access  = is_owner or viewer_role in ("founder", "zam_ld", "tech_admin", "admin")

    if not has_access:
        await callback.answer("❌ Нет доступа.", show_alert=True)
        return

    user    = get_user(target_uid)
    don     = get_donate_user_data(user)
    biz_key = don.get("business")

    if not biz_key or biz_key not in DONATE_BUSINESSES:
        await callback.answer("❌ Нет донат-бизнеса для продажи.", show_alert=True)
        return

    biz       = DONATE_BUSINESSES[biz_key]
    sell_cash = biz.get("sell_price", 0)
    from utils import update_balance as _upd, get_balance as _bal
    _upd(target_uid, _bal(target_uid) + sell_cash)
    don["business"]         = None
    don["biz_last_collect"] = None
    save_user_data()

    await callback.answer(
        f"✅ Бизнес «{biz['name']}» продан за {format_amount(sell_cash)}$!",
        show_alert=True
    )
    await _send_info(callback, target_uid, viewer_uid, edit=True)


# ─── Продажа донат-дома ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pi_sell_house:"))
async def cb_pi_sell_house(callback: CallbackQuery):
    from donate import get_donate_user_data, DONATE_HOUSES
    from admin_roles import get_role

    target_uid  = int(callback.data.split(":")[1])
    viewer_uid  = callback.from_user.id
    is_owner    = (target_uid == viewer_uid)
    viewer_role = get_role(viewer_uid)
    has_access  = is_owner or viewer_role in ("founder", "zam_ld", "tech_admin", "admin")

    if not has_access:
        await callback.answer("❌ Нет доступа.", show_alert=True)
        return

    user      = get_user(target_uid)
    don       = get_donate_user_data(user)
    house_key = don.get("house")

    if not house_key or house_key not in DONATE_HOUSES:
        await callback.answer("❌ Нет донат-дома для продажи.", show_alert=True)
        return

    house     = DONATE_HOUSES[house_key]
    sell_cash = house.get("sell_price", 0)
    from utils import update_balance as _upd, get_balance as _bal
    _upd(target_uid, _bal(target_uid) + sell_cash)
    don["house"] = None
    save_user_data()

    await callback.answer(
        f"✅ Дом «{house['name']}» продан за {format_amount(sell_cash)}$!",
        show_alert=True
    )
    await _send_info(callback, target_uid, viewer_uid, edit=True)


# ─── Продажа донат-авто ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pi_sell_car:"))
async def cb_pi_sell_car(callback: CallbackQuery):
    from donate import get_donate_user_data, DONATE_CARS
    from admin_roles import get_role

    target_uid  = int(callback.data.split(":")[1])
    viewer_uid  = callback.from_user.id
    is_owner    = (target_uid == viewer_uid)
    viewer_role = get_role(viewer_uid)
    has_access  = is_owner or viewer_role in ("founder", "zam_ld", "tech_admin", "admin")

    if not has_access:
        await callback.answer("❌ Нет доступа.", show_alert=True)
        return

    user    = get_user(target_uid)
    don     = get_donate_user_data(user)
    car_key = don.get("car")

    if not car_key or car_key not in DONATE_CARS:
        await callback.answer("❌ Нет донат-авто для продажи.", show_alert=True)
        return

    car       = DONATE_CARS[car_key]
    sell_cash = car.get("sell_price", 0)
    from utils import update_balance as _upd, get_balance as _bal
    _upd(target_uid, _bal(target_uid) + sell_cash)
    don["car"] = None
    save_user_data()

    await callback.answer(
        f"✅ Авто «{car['name']}» продано за {format_amount(sell_cash)}$!",
        show_alert=True
    )
    await _send_info(callback, target_uid, viewer_uid, edit=True)
