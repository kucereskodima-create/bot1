import time
from aiogram import Router, F
from aiogram.types import (
    CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import bot

router = Router()

MAX_COMPLEX_LEVEL = 35

COMPLEX_LEVELS = {
    1:  {"upgrade_cost":       500_000, "income_per_hour":    10_000},
    2:  {"upgrade_cost":       615_934, "income_per_hour":    20_000},
    3:  {"upgrade_cost":       800_000, "income_per_hour":    25_000},
    4:  {"upgrade_cost":     1_200_000, "income_per_hour":    31_000},
    5:  {"upgrade_cost":     1_151_401, "income_per_hour":    40_000},
    6:  {"upgrade_cost":     1_418_374, "income_per_hour":    42_000},
    7:  {"upgrade_cost":     1_900_250, "income_per_hour":    60_000},
    8:  {"upgrade_cost":     2_190_381, "income_per_hour":   100_000},
    9:  {"upgrade_cost":     3_651_449, "income_per_hour":   150_000},
    10: {"upgrade_cost":     4_266_235, "income_per_hour":   199_871},
    11: {"upgrade_cost":     5_023_573, "income_per_hour":   240_000},
    12: {"upgrade_cost":     4_956_503, "income_per_hour":   260_000},
    13: {"upgrade_cost":     6_105_752, "income_per_hour":   290_000},
    14: {"upgrade_cost":     8_521_493, "income_per_hour":   350_000},
    15: {"upgrade_cost":     9_265_518, "income_per_hour":   370_000},
    16: {"upgrade_cost":    13_413_942, "income_per_hour":   450_000},
    17: {"upgrade_cost":    14_060_558, "income_per_hour":   470_000},
    18: {"upgrade_cost":    25_320_865, "income_per_hour":   540_000},
    19: {"upgrade_cost":    21_337_206, "income_per_hour":   560_000},
    20: {"upgrade_cost":    26_285_005, "income_per_hour":   600_810},
    21: {"upgrade_cost":    40_380_324, "income_per_hour":   675_070},
    22: {"upgrade_cost":    39_889_270, "income_per_hour":   680_000},
    23: {"upgrade_cost":    49_139_648, "income_per_hour":   725_030},
    24: {"upgrade_cost":    60_535_368, "income_per_hour":   900_000},
    25: {"upgrade_cost":    75_573_968, "income_per_hour": 1_000_000},
    26: {"upgrade_cost":   100_868_237, "income_per_hour": 1_250_000},
    27: {"upgrade_cost":   113_173_606, "income_per_hour": 1_300_000},
    28: {"upgrade_cost":   139_419_942, "income_per_hour": 1_421_010},
    29: {"upgrade_cost":   171_753_702, "income_per_hour": 1_840_170},
    30: {"upgrade_cost":   211_586_742, "income_per_hour": 2_001_999},
    31: {"upgrade_cost":   260_658_719, "income_per_hour": 2_470_500},
    32: {"upgrade_cost":   321_112_796, "income_per_hour": 2_650_000},
    33: {"upgrade_cost":   395_589_440, "income_per_hour": 2_840_000},
    34: {"upgrade_cost":   488_341_382, "income_per_hour": 3_040_000},
    35: {"upgrade_cost":   600_000_000, "income_per_hour": 3_250_000},
}

# ─── Базовые показатели на уровне 30 ──────────────────────────────────────────
_BASE_INCOME    = 2_001_999
_BASE_STORAGE   = 877_500
_BASE_RATES = {
    "diamonds":    2_500,
    "gold":        8_400,
    "titan":       3_100,
    "energycores":   870,
    "uranium":       420,
}

RESOURCE_ORDER  = ["diamonds", "gold", "titan", "energycores", "uranium"]
RESOURCE_NAMES  = {
    "diamonds":    "💎 Алмазы",
    "gold":        "🪙 Золото",
    "titan":       "⛓ Титан",
    "energycores": "🔋 Энергоядра",
    "uranium":     "☢ Уран",
}
RESOURCE_UNITS  = {
    "diamonds":    "ед.",
    "gold":        "кг",
    "titan":       "кг",
    "energycores": "шт.",
    "uranium":     "г",
}
RESOURCE_PRICES = {
    "diamonds":    3.00,
    "gold":        0.50,
    "titan":       1.00,
    "energycores": 8.00,
    "uranium":     25.00,
}

LEVEL_BONUSES = {
    5:  [("📦", "+10% к вместимости хранилища")],
    10: [("⚔️", "+5% к наградам за рейды")],
    15: [("🛡", "-5% потерь при атаке"), ("📦", "+25% к вместимости хранилища")],
    20: [("🚀", "+10% к скорости производства"), ("⚔️", "+15% к наградам за рейды")],
    25: [("📦", "+50% к вместимости хранилища"), ("🛡", "-10% потерь при атаке")],
    30: [
        ("⚔️", "+37% к наградам за рейды"),
        ("🛡", "-12% потерь при атаке"),
        ("📦", "+95% к вместимости хранилища"),
        ("🚀", "+18% к скорости производства"),
    ],
    35: [
        ("💎", "+50% к добыче всех ресурсов"),
        ("⚔️", "+50% к наградам за рейды"),
        ("🛡", "-20% потерь при атаке"),
        ("📦", "+150% к вместимости хранилища"),
    ],
}


class CxInvestState(StatesGroup):
    waiting_amount = State()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fmt(n: float) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f} млрд"
    if n >= 1_000_000:
        v = n / 1_000_000
        return f"{v:.1f} млн" if v < 100 else f"{int(v)} млн"
    if n >= 1_000:
        v = n / 1_000
        return f"{v:.1f} тыс" if v < 100 else f"{int(v)} тыс"
    return f"{int(n):,}".replace(",", ".")


def _fmt_num(n: float) -> str:
    return f"{int(n):,}".replace(",", ".")


def _ratio(level: int) -> float:
    lvl = max(1, min(MAX_COMPLEX_LEVEL, level))
    return COMPLEX_LEVELS[lvl]["income_per_hour"] / _BASE_INCOME


def _get_rate(level: int, res: str) -> float:
    return _BASE_RATES[res] * _ratio(level)


def _get_max_storage(level: int) -> float:
    return max(1_000, _BASE_STORAGE * _ratio(level))


def _get_efficiency(level: int) -> int:
    return min(100, round(40 + level * 60 / MAX_COMPLEX_LEVEL))


def _get_active_bonuses(level: int) -> list:
    bonuses = []
    for milestone, blist in sorted(LEVEL_BONUSES.items()):
        if level >= milestone:
            for b in blist:
                if b not in bonuses:
                    bonuses.append(b)
    return bonuses


def _ensure_complex(clan: dict) -> dict:
    now = int(time.time())
    if "complex" not in clan:
        clan["complex"] = {
            "level": 1,
            "resources": {r: 0.0 for r in RESOURCE_ORDER},
            "last_update": now,
            "upgrade_fund": 0,
            "investors": {},
        }
    c = clan["complex"]
    c.setdefault("level", 1)
    c.setdefault("resources", {r: 0.0 for r in RESOURCE_ORDER})
    for r in RESOURCE_ORDER:
        c["resources"].setdefault(r, 0.0)
    c.setdefault("last_update", now)
    c.setdefault("upgrade_fund", 0)
    c.setdefault("investors", {})
    return clan


def _flush_complex(clan: dict):
    _ensure_complex(clan)
    c = clan["complex"]
    clvl = max(1, min(MAX_COMPLEX_LEVEL, c["level"]))
    now = int(time.time())
    last = c.get("last_update", now)
    elapsed_min = (now - last) / 60.0
    if elapsed_min < 0.01:
        return

    max_s = _get_max_storage(clvl)
    resources = c["resources"]
    total_stored = sum(resources.values())

    if total_stored < max_s:
        available = max_s - total_stored
        total_rate = sum(_BASE_RATES[r] * _ratio(clvl) for r in RESOURCE_ORDER)
        total_mined = total_rate * elapsed_min
        factor = min(1.0, available / max(total_mined, 0.001))

        for res in RESOURCE_ORDER:
            rate = _get_rate(clvl, res)
            mined = rate * elapsed_min * factor
            resources[res] = resources.get(res, 0.0) + mined

    c["last_update"] = now


# ─── Auto-mine (called by scheduler every minute) ─────────────────────────────

def auto_mine_all_complexes():
    from clans import clans_data, save_clans
    changed = False
    for clan in clans_data.values():
        try:
            _flush_complex(clan)
            changed = True
        except Exception:
            pass
    if changed:
        save_clans()


# ─── Texts ────────────────────────────────────────────────────────────────────

def _main_text(clan: dict) -> str:
    _ensure_complex(clan)
    _flush_complex(clan)
    c = clan["complex"]
    clvl = max(1, min(MAX_COMPLEX_LEVEL, c["level"]))
    info = COMPLEX_LEVELS[clvl]
    income_hr = info["income_per_hour"]
    efficiency = _get_efficiency(clvl)
    max_s = _get_max_storage(clvl)
    total_stored = sum(c["resources"].values())
    filled = round(total_stored / max_s * 10) if max_s > 0 else 0
    bar = "▰" * filled + "▱" * (10 - filled)
    return (
        f"🏛 <b>ЦЕНТР ДОБЫЧИ РЕСУРСОВ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📡 Уровень комплекса: <b>{clvl} / {MAX_COMPLEX_LEVEL}</b>\n"
        f"⚡ Эффективность системы: <b>{efficiency}%</b>\n"
        f"📦 Вместимость хранилища: <b>{_fmt_num(int(total_stored))} / {_fmt_num(int(max_s))}</b>\n"
        f"<code>[{bar}]</code>\n"
        f"💸 Доход комплекса: <b>{_fmt_num(income_hr)}$/час</b>\n\n"
        f"☢ <i>Центр добычи автоматически производит редкие материалы для развития клана.</i>"
    )


def _main_kb(clan_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 Хранилище",    callback_data=f"cx_warehouse:{clan_id}"),
            InlineKeyboardButton(text="🚀 Модернизация", callback_data=f"cx_upgrade:{clan_id}"),
        ],
        [
            InlineKeyboardButton(text="📊 Статистика",   callback_data=f"cx_stats:{clan_id}"),
            InlineKeyboardButton(text="🏆 Инвесторы",    callback_data=f"cx_investors:{clan_id}"),
        ],
        [
            InlineKeyboardButton(text="💰 Продать ресурсы", callback_data=f"cx_sell:{clan_id}"),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад в клан", callback_data=f"clan_back:{clan_id}"),
        ],
    ])


def _warehouse_text(clan: dict) -> str:
    _flush_complex(clan)
    c = clan["complex"]
    clvl = max(1, min(MAX_COMPLEX_LEVEL, c["level"]))
    resources = c["resources"]
    max_s = _get_max_storage(clvl)
    total_stored = sum(resources.values())
    filled = round(total_stored / max_s * 10) if max_s > 0 else 0
    bar = "▰" * filled + "▱" * (10 - filled)
    total_value = sum(resources.get(r, 0) * RESOURCE_PRICES[r] for r in RESOURCE_ORDER)

    lines = [
        "🏛 <b>ХРАНИЛИЩЕ КОМПЛЕКСА</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━\n",
    ]
    for r in RESOURCE_ORDER:
        amount = resources.get(r, 0)
        lines.append(f"— {RESOURCE_NAMES[r]}: <b>{_fmt_num(int(amount))} {RESOURCE_UNITS[r]}</b>")
    lines += [
        "",
        f"<code>[{bar}]</code>",
        f"📦 Заполнено: <b>{_fmt_num(int(total_stored))} / {_fmt_num(int(max_s))}</b>",
        f"💰 Рыночная стоимость: <b>{_fmt_num(int(total_value))}$</b>",
        "",
        "🏦 <i>После продажи прибыль автоматически отправляется в казну клана.</i>",
    ]
    return "\n".join(lines)


def _warehouse_kb(clan_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Продать ресурсы", callback_data=f"cx_sell:{clan_id}")],
        [InlineKeyboardButton(text="🔙 Назад",           callback_data=f"cx_back:{clan_id}")],
    ])


def _stats_text(clan: dict) -> str:
    _ensure_complex(clan)
    c = clan["complex"]
    clvl = max(1, min(MAX_COMPLEX_LEVEL, c["level"]))
    efficiency = _get_efficiency(clvl)

    rate_lines = []
    for i, r in enumerate(RESOURCE_ORDER):
        rate = _get_rate(clvl, r)
        prefix = "└" if i == len(RESOURCE_ORDER) - 1 else "├"
        rate_lines.append(
            f"{prefix} {RESOURCE_NAMES[r]}: <b>{_fmt_num(int(rate))} {RESOURCE_UNITS[r]}/мин</b>"
        )

    bonuses = _get_active_bonuses(clvl)
    if bonuses:
        bonus_lines = []
        for i, (icon, text) in enumerate(bonuses):
            prefix = "└" if i == len(bonuses) - 1 else "├"
            bonus_lines.append(f"{prefix} {icon} {text}")
        bonus_block = "\n".join(bonus_lines)
    else:
        bonus_block = "└ <i>Разблокируются с повышением уровня</i>"

    return (
        f"🏛 <b>СТАТИСТИКА КОМПЛЕКСА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📡 Уровень: <b>{clvl}</b>  •  ⚡ Эффективность: <b>{efficiency}%</b>\n\n"
        f"⚒ <b>Производство ресурсов:</b>\n"
        f"{chr(10).join(rate_lines)}\n\n"
        f"🎖 <b>Активные улучшения:</b>\n"
        f"{bonus_block}\n\n"
        f"⚙ <i>С повышением уровня комплекса увеличивается эффективность, "
        f"добыча ресурсов и дополнительные бонусы.</i>"
    )


def _upgrade_text(clan: dict) -> str:
    _ensure_complex(clan)
    c = clan["complex"]
    clvl = max(1, min(MAX_COMPLEX_LEVEL, c["level"]))
    upgrade_fund = c.get("upgrade_fund", 0)

    if clvl >= MAX_COMPLEX_LEVEL:
        return (
            f"🚀 <b>МОДЕРНИЗАЦИЯ КОМПЛЕКСА</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📡 Уровень комплекса: <b>{clvl} / {MAX_COMPLEX_LEVEL}</b>\n\n"
            f"🏆 <b>Комплекс достиг максимального уровня!</b>\n\n"
            f"⚡ Все системы работают на максимальной мощности."
        )

    cost = COMPLEX_LEVELS[clvl]["upgrade_cost"]
    progress_pct = round(upgrade_fund / cost * 100, 1) if cost > 0 else 0
    filled = round(progress_pct / 10)
    bar = "▰" * filled + "▱" * (10 - filled)

    # Next level bonuses
    next_lvl = clvl + 1
    d_now = _get_rate(clvl, "diamonds")
    g_now = _get_rate(clvl, "gold")
    d_next = _get_rate(next_lvl, "diamonds")
    g_next = _get_rate(next_lvl, "gold")
    spd_delta = round((_ratio(next_lvl) - _ratio(clvl)) * 100, 1)
    stor_delta = round(
        (_get_max_storage(next_lvl) - _get_max_storage(clvl)) / max(_get_max_storage(clvl), 1) * 100, 1
    )

    prod_lines = [
        f"├ 💎 Алмазы: +{_fmt_num(int(d_next - d_now))} ед./мин",
        f"├ 🪙 Золото: +{_fmt_num(int(g_next - g_now))} кг/мин",
        f"└ 🚀 Скорость добычи: +{spd_delta}%",
    ]
    extra_lines = [f"└ 📦 +{stor_delta}% к вместимости склада"]

    return (
        f"🚀 <b>МОДЕРНИЗАЦИЯ КОМПЛЕКСА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📈 Следующий уровень: <b>{next_lvl}</b>\n"
        f"💰 Требуется: <b>{_fmt_num(cost)}$</b>\n"
        f"📥 Внесено: <b>{_fmt_num(int(upgrade_fund))}$</b>\n\n"
        f"<code>[{bar}]</code>  <b>{progress_pct}%</b>\n\n"
        f"⚡ <b>Улучшения после повышения:</b>\n"
        f"{chr(10).join(prod_lines)}\n\n"
        f"🎖 <b>Дополнительные бонусы:</b>\n"
        f"{chr(10).join(extra_lines)}\n\n"
        f"⚒ <i>Инвестируйте в развитие комплекса вместе с кланом.</i>"
    )


def _upgrade_kb(clan_id: str, at_max: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if not at_max:
        buttons.append([InlineKeyboardButton(text="💸 Вложить средства", callback_data=f"cx_invest:{clan_id}")])
    buttons.append([InlineKeyboardButton(text="🏆 Топ инвесторов", callback_data=f"cx_investors:{clan_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад",           callback_data=f"cx_back:{clan_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _investors_text(clan: dict) -> str:
    _ensure_complex(clan)
    from utils import user_data as udata
    investors = clan["complex"].get("investors", {})
    sorted_inv = sorted(investors.items(), key=lambda x: x[1], reverse=True)[:10]

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "1️⃣0️⃣"]
    lines = [
        "🏆 <b>КРУПНЕЙШИЕ ИНВЕСТОРЫ</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━\n",
    ]
    if not sorted_inv:
        lines.append("<i>Пока никто не вкладывал средства в развитие комплекса.</i>")
    else:
        for i, (uid, amount) in enumerate(sorted_inv):
            name = udata.get(uid, {}).get("name", f"ID {uid}")
            lines.append(f"⠀{medals[i]} <b>{name}</b> — {_fmt(amount)}$")

    return "\n".join(lines)


# ─── Callbacks ────────────────────────────────────────────────────────────────

def _get_clan_checked(callback: CallbackQuery, clan_id: str):
    from clans import clans_data
    clan = clans_data.get(clan_id)
    if not clan or str(callback.from_user.id) not in clan.get("members", {}):
        return None
    return clan


@router.callback_query(F.data.startswith("cx_main:"))
async def cb_cx_main(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan = _get_clan_checked(callback, clan_id)
    if not clan:
        await callback.answer("❌ Нет доступа.", show_alert=True)
        return
    from clans import save_clans
    _flush_complex(clan)
    save_clans()
    await callback.message.edit_text(
        _main_text(clan),
        parse_mode="HTML",
        reply_markup=_main_kb(clan_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cx_back:"))
async def cb_cx_back(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan = _get_clan_checked(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True)
        return
    from clans import save_clans
    _flush_complex(clan)
    save_clans()
    await callback.message.edit_text(
        _main_text(clan),
        parse_mode="HTML",
        reply_markup=_main_kb(clan_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cx_warehouse:"))
async def cb_cx_warehouse(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan = _get_clan_checked(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True)
        return
    from clans import save_clans
    _flush_complex(clan)
    save_clans()
    await callback.message.edit_text(
        _warehouse_text(clan),
        parse_mode="HTML",
        reply_markup=_warehouse_kb(clan_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cx_stats:"))
async def cb_cx_stats(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan = _get_clan_checked(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True)
        return
    await callback.message.edit_text(
        _stats_text(clan),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"cx_back:{clan_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cx_upgrade:"))
async def cb_cx_upgrade(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan = _get_clan_checked(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True)
        return
    _ensure_complex(clan)
    clvl = clan["complex"]["level"]
    at_max = clvl >= MAX_COMPLEX_LEVEL
    await callback.message.edit_text(
        _upgrade_text(clan),
        parse_mode="HTML",
        reply_markup=_upgrade_kb(clan_id, at_max=at_max)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cx_investors:"))
async def cb_cx_investors(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan = _get_clan_checked(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True)
        return
    await callback.message.edit_text(
        _investors_text(clan),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"cx_upgrade:{clan_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cx_sell:"))
async def cb_cx_sell(callback: CallbackQuery):
    clan_id = callback.data.split(":", 1)[1]
    clan = _get_clan_checked(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True)
        return
    from clans import save_clans
    _flush_complex(clan)
    c = clan["complex"]
    resources = c["resources"]
    total_value = sum(resources.get(r, 0) * RESOURCE_PRICES[r] for r in RESOURCE_ORDER)

    if total_value < 1:
        await callback.answer("📦 Хранилище пусто — нечего продавать.", show_alert=True)
        return

    earn = int(total_value)
    clan["treasury"] = clan.get("treasury", 0) + earn
    for r in RESOURCE_ORDER:
        resources[r] = 0.0
    c["last_update"] = int(time.time())
    save_clans()

    await callback.message.edit_text(
        f"✅ <b>Ресурсы проданы!</b>\n\n"
        f"💰 Выручка: <b>{_fmt(earn)}$</b>\n"
        f"🏦 Казна клана: <b>{_fmt(clan['treasury'])}$</b>\n\n"
        f"<i>Хранилище очищено — производство продолжается.</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Хранилище", callback_data=f"cx_warehouse:{clan_id}")],
            [InlineKeyboardButton(text="🔙 Назад",     callback_data=f"cx_back:{clan_id}")],
        ])
    )
    await callback.answer("✅ Продано!")


@router.callback_query(F.data.startswith("cx_invest:"))
async def cb_cx_invest(callback: CallbackQuery, state: FSMContext):
    clan_id = callback.data.split(":", 1)[1]
    clan = _get_clan_checked(callback, clan_id)
    if not clan:
        await callback.answer("❌", show_alert=True)
        return
    _ensure_complex(clan)
    clvl = clan["complex"]["level"]
    if clvl >= MAX_COMPLEX_LEVEL:
        await callback.answer("🏆 Комплекс уже на максимальном уровне!", show_alert=True)
        return

    cost = COMPLEX_LEVELS[clvl]["upgrade_cost"]
    fund = clan["complex"].get("upgrade_fund", 0)
    remaining = cost - fund

    from utils import get_balance
    balance = get_balance(callback.from_user.id)

    await state.set_state(CxInvestState.waiting_amount)
    await state.update_data(clan_id=clan_id)
    await callback.message.edit_text(
        f"💸 <b>ИНВЕСТИРОВАНИЕ В КОМПЛЕКС</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📈 Текущий уровень: <b>{clvl}</b>  →  <b>{clvl + 1}</b>\n"
        f"💰 Требуется: <b>{_fmt_num(cost)}$</b>\n"
        f"📥 Уже внесено: <b>{_fmt_num(int(fund))}$</b>\n"
        f"🔓 Осталось собрать: <b>{_fmt_num(int(remaining))}$</b>\n\n"
        f"💼 Ваш баланс: <b>{_fmt(balance)}$</b>\n\n"
        f"Введите сумму для вложения:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cx_upgrade:{clan_id}")]
        ])
    )
    await callback.answer()


@router.message(CxInvestState.waiting_amount)
async def msg_cx_invest_amount(message: Message, state: FSMContext):
    from clans import clans_data, save_clans
    from utils import get_balance, update_balance, save_user_data, parse_k

    user_id = message.from_user.id
    data = await state.get_data()
    clan_id = data.get("clan_id")

    if not clan_id:
        await state.clear()
        await message.answer("❌ Сессия устарела. Зайди в Центр заново.")
        return

    import clans as _clans_mod
    clan = _clans_mod.clans_data.get(clan_id)
    if not clan or str(user_id) not in clan.get("members", {}):
        await state.clear()
        await message.answer("❌ Клан не найден. Попробуй снова через меню.")
        return

    raw = message.text.strip()
    amount = parse_k(raw)
    if not amount or amount <= 0:
        await message.answer(
            "❌ Неверная сумма. Примеры: <code>1000000</code>, <code>1кк</code>, <code>5к</code>",
            parse_mode="HTML"
        )
        return

    balance = get_balance(user_id)
    if amount > balance:
        await message.answer(
            f"❌ Недостаточно средств.\n"
            f"💼 Ваш баланс: <b>{_fmt(balance)}$</b>",
            parse_mode="HTML"
        )
        return

    await state.clear()

    _ensure_complex(clan)
    c = clan["complex"]
    clvl = max(1, min(MAX_COMPLEX_LEVEL, c["level"]))

    if clvl >= MAX_COMPLEX_LEVEL:
        await message.answer("🏆 Комплекс уже на максимальном уровне!")
        return

    cost = COMPLEX_LEVELS[clvl]["upgrade_cost"]
    remaining = cost - c.get("upgrade_fund", 0)
    invest = min(amount, int(remaining) + 1)

    update_balance(user_id, balance - invest)
    save_user_data()

    uid_str = str(user_id)
    c["investors"][uid_str] = c["investors"].get(uid_str, 0) + invest
    c["upgrade_fund"] = c.get("upgrade_fund", 0) + invest

    leveled_up = False
    while c["upgrade_fund"] >= COMPLEX_LEVELS[max(1, min(MAX_COMPLEX_LEVEL, c["level"]))]["upgrade_cost"]:
        lvl = c["level"]
        if lvl >= MAX_COMPLEX_LEVEL:
            break
        overshoot = c["upgrade_fund"] - COMPLEX_LEVELS[lvl]["upgrade_cost"]
        c["level"] += 1
        c["upgrade_fund"] = max(0, overshoot)
        leveled_up = True

    import clans as _clans_mod
    _clans_mod.save_clans()

    text_parts = [
        f"✅ <b>Вложено: {_fmt(invest)}$</b>",
        f"📥 Итого внесено в фонд: <b>{_fmt(c['upgrade_fund'])}$</b>",
    ]
    if leveled_up:
        text_parts.insert(0, f"🎉 <b>Комплекс повышен до уровня {c['level']}!</b>\n")
        text_parts.append(f"\n⚡ Новый доход: <b>{_fmt_num(COMPLEX_LEVELS[c['level']]['income_per_hour'])}$/час</b>")

    await message.answer(
        "\n".join(text_parts),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Модернизация", callback_data=f"cx_upgrade:{clan_id}")],
            [InlineKeyboardButton(text="🏛 Центр",        callback_data=f"cx_main:{clan_id}")],
        ])
    )
