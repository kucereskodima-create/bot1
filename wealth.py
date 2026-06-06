"""
Команда «состояние» — полный финансовый портрет игрока.
"""
import time
from aiogram import Router, F
from aiogram.types import Message
from utils import get_user, format_amount

router = Router()


def _calc_net_worth(user_id: int, user: dict) -> dict:
    from donate import get_donate_user_data, DONATE_BUSINESSES, DONATE_HOUSES, DONATE_CARS
    from house_shop import SHOP_HOUSES
    from auto_shop import SHOP_CARS
    from business_shop import BUSINESSES, BIZ_LEVELS, get_biz_level
    from farm import get_farm, get_btc_price, flush_farm

    bal  = user.get("balance", 0)
    bank = user.get("user_bank", 0)

    try:
        farm = get_farm(user_id)
        flush_farm(farm)
        btc_bal   = farm.get("btc_balance", 0.0)
        btc_price = get_btc_price()
        btc_usd   = int(btc_bal * btc_price)
    except Exception:
        btc_bal  = 0.0
        btc_usd  = 0
        btc_price = 0

    don = get_donate_user_data(user)

    # ── Дома ──
    houses_val = 0
    house_lines = []
    don_house = don.get("house")
    if don_house and don_house in DONATE_HOUSES:
        h = DONATE_HOUSES[don_house]
        houses_val += h["sell_price"]
        house_lines.append(f"  🏛 {h['name']} — {format_amount(h['sell_price'])}$")
    shop_house = user.get("shop_house")
    if shop_house and shop_house in SHOP_HOUSES:
        h = SHOP_HOUSES[shop_house]
        houses_val += h["price"]
        house_lines.append(f"  🏠 {h['name']} — {format_amount(h['price'])}$")

    # ── Авто ──
    cars_val = 0
    car_lines = []
    don_car = don.get("car")
    if don_car and don_car in DONATE_CARS:
        c = DONATE_CARS[don_car]
        cars_val += c["sell_price"]
        car_lines.append(f"  🏎 {c['name']} — {format_amount(c['sell_price'])}$")
    shop_car = user.get("shop_car")
    if shop_car and shop_car in SHOP_CARS:
        c = SHOP_CARS[shop_car]
        cars_val += c["price"]
        car_lines.append(f"  🚗 {c['name']} — {format_amount(c['price'])}$")

    # ── Бизнесы ──
    biz_val = 0
    biz_lines = []
    don_biz = don.get("business")
    if don_biz and don_biz in DONATE_BUSINESSES:
        b = DONATE_BUSINESSES[don_biz]
        biz_val += b["sell_price"]
        biz_lines.append(f"  🃏 {b['name']} — {format_amount(b['sell_price'])}$")
    owned_bizs = user.get("businesses", [])
    for biz_idx in owned_bizs:
        if 0 <= biz_idx < len(BUSINESSES):
            b = BUSINESSES[biz_idx]
            lvl = get_biz_level(user, biz_idx)
            mult = BIZ_LEVELS[lvl]["multiplier"]
            val = int(b["price"] * mult)
            biz_val += val
            biz_lines.append(f"  🏢 {b['name']} (лвл {lvl}) — {format_amount(val)}$")

    # ── Ферма ──
    farm_val = 0
    farm_lines = []
    try:
        farm_lvl = farm.get("farm_level", 0)
        from farm import FARM_LEVELS
        if farm_lvl > 0:
            from farm import FARM_LEVELS
            farm_cost = FARM_LEVELS[farm_lvl].get("cost_usd", 50_000) if farm_lvl < len(FARM_LEVELS) else 50_000
            farm_val = farm_cost + btc_usd
            farm_lines.append(f"  ₿ Ферма лвл {farm_lvl} + {btc_bal:.4f} BTC — {format_amount(farm_val)}$")
    except Exception:
        pass

    total = bal + bank + btc_usd + houses_val + cars_val + biz_val + farm_val
    return {
        "balance": bal,
        "bank":    bank,
        "btc_bal": btc_bal,
        "btc_usd": btc_usd,
        "btc_price": btc_price,
        "houses_val": houses_val,
        "house_lines": house_lines,
        "cars_val": cars_val,
        "car_lines": car_lines,
        "biz_val": biz_val,
        "biz_lines": biz_lines,
        "farm_val": farm_val,
        "farm_lines": farm_lines,
        "total": total,
    }


def wealth_text(user_id: int, user: dict) -> str:
    w = _calc_net_worth(user_id, user)
    name = user.get("name", "Без имени")

    lines = [
        f"💼 <b>Состояние: {name}</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"",
        f"💰 Наличные:   <b>{format_amount(w['balance'])}$</b>",
        f"🏦 Банк:       <b>{format_amount(w['bank'])}$</b>",
    ]

    if w["btc_bal"] > 0:
        lines.append(f"₿ Bitcoin:     <b>{w['btc_bal']:.4f} BTC</b>  (~{format_amount(w['btc_usd'])}$)")

    if w["house_lines"]:
        lines += ["", "🏠 <b>Недвижимость:</b>"] + w["house_lines"]

    if w["car_lines"]:
        lines += ["", "🚗 <b>Транспорт:</b>"] + w["car_lines"]

    if w["biz_lines"]:
        lines += ["", "🏢 <b>Бизнесы:</b>"] + w["biz_lines"]

    if w["farm_lines"]:
        lines += ["", "⛏ <b>Ферма:</b>"] + w["farm_lines"]

    lines += [
        "",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"🏆 <b>Итого: {format_amount(w['total'])}$</b>",
    ]
    return "\n".join(lines)


@router.message(F.text.lower().in_(["состояние", "💼 состояние", "/состояние", "нетворт", "net worth"]))
async def cmd_wealth(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    text = wealth_text(user_id, user)
    await message.answer(text, parse_mode="HTML")
