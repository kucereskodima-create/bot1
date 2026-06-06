import json
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import owners, admins
from utils import (
    load_user_data,
    save_user_data,
    get_user,
    get_balance,
    update_balance,
    format_amount,
    clickable_name,
    safe_reply_kb,
    parse_k,
)

router = Router()

PROMOS_FILE = os.path.join(os.path.dirname(__file__), "promos.json")


def load_promos() -> dict:
    if os.path.exists(PROMOS_FILE):
        try:
            with open(PROMOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_promos(data: dict):
    try:
        with open(PROMOS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения promos.json: {e}")


class CreatePromoState(StatesGroup):
    waiting_for_name = State()
    waiting_for_type = State()
    waiting_for_amount = State()
    waiting_for_uses = State()


def is_admin_or_owner(user_id: int) -> bool:
    return user_id in owners or user_id in admins


def promo_type_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💵 Деньги", callback_data="promo_type_money"),
                InlineKeyboardButton(text="💎 Донат (DC)", callback_data="promo_type_bits"),
            ],
            [
                InlineKeyboardButton(text="₿ BTC", callback_data="promo_type_btc"),
                InlineKeyboardButton(text="⭐ VIP статус", callback_data="promo_type_vip"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="promo_create_cancel")],
        ]
    )


def promo_confirm_kb(code: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Создать", callback_data=f"promo_confirm_{code}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="promo_create_cancel"),
            ]
        ]
    )


@router.message(F.text.lower().in_(["создать промо", "➕ создать промо"]))
async def cmd_create_promo(message: Message, state: FSMContext):
    if not is_admin_or_owner(message.from_user.id):
        await message.answer("❌ У вас нет прав для создания промокодов.")
        return
    await message.answer(
        "🎟 <b>Создание промокода</b>\n\n"
        "Введите <b>название</b> промокода (только латинские буквы и цифры, без пробелов).\n"
        "Пример: <code>BLACKLINE</code>",
        parse_mode="HTML",
    )
    await state.set_state(CreatePromoState.waiting_for_name)


@router.message(CreatePromoState.waiting_for_name)
async def promo_set_name(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    if not code or ' ' in code or len(code) > 30:
        await message.answer(
            "❌ Название промокода не должно содержать пробелов и быть не длиннее 30 символов.\n"
            "Попробуйте ещё раз:"
        )
        return
    promos = load_promos()
    if code in promos:
        await message.answer(
            f"❌ Промокод <code>{code}</code> уже существует. Введите другое название:",
            parse_mode="HTML",
        )
        return
    await state.update_data(promo_code=code)
    await message.answer(
        f"🎟 Промокод: <code>{code}</code>\n\n"
        "Выберите тип награды:",
        parse_mode="HTML",
        reply_markup=promo_type_kb(),
    )
    await state.set_state(CreatePromoState.waiting_for_type)


@router.callback_query(F.data.in_(["promo_type_money", "promo_type_bits", "promo_type_btc", "promo_type_vip"]), CreatePromoState.waiting_for_type)
async def promo_set_type(callback: CallbackQuery, state: FSMContext):
    if callback.data == "promo_type_money":
        reward_type = "money"
        label = "💵 Деньги ($)"
    elif callback.data == "promo_type_bits":
        reward_type = "bits"
        label = "💎 Донат (DC)"
    elif callback.data == "promo_type_btc":
        reward_type = "btc"
        label = "₿ BTC"
    else:
        reward_type = "vip"
        label = "⭐ VIP статус"

    await state.update_data(promo_type=reward_type)

    if reward_type == "vip":
        await callback.message.edit_text(
            f"Тип награды: <b>{label}</b>\n\n"
            "Введите <b>количество дней</b> VIP (например <code>30</code>):",
            parse_mode="HTML",
        )
    elif reward_type == "btc":
        await callback.message.edit_text(
            f"Тип награды: <b>{label}</b>\n\n"
            "Введите <b>количество BTC</b> (например <code>0.5</code>):",
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            f"Тип награды: <b>{label}</b>\n\n"
            "Введите <b>сумму</b> награды:\n\n"
            "📌 Примеры:\n"
            "• <code>1000</code> — тысяча\n"
            "• <code>100к</code> — 100 000\n"
            "• <code>1кк</code> — 1 000 000\n"
            "• <code>50кк</code> — 50 000 000",
            parse_mode="HTML",
        )
    await state.set_state(CreatePromoState.waiting_for_amount)
    await callback.answer()


@router.callback_query(F.data == "promo_create_cancel")
async def promo_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Создание промокода отменено.")
    await callback.answer()


@router.message(CreatePromoState.waiting_for_amount)
async def promo_set_amount(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    reward_type = data.get("promo_type", "money")

    if reward_type == "vip":
        try:
            amount = int(text)
            assert amount > 0
        except Exception:
            await message.answer("❌ Введите целое число дней VIP, например <code>30</code>:", parse_mode="HTML")
            return
        await state.update_data(promo_amount=amount)
        await message.answer(
            f"⭐ VIP на <b>{amount} дн.</b>\n\n"
            "Введите <b>количество активаций</b>:",
            parse_mode="HTML",
        )
    elif reward_type == "btc":
        try:
            amount = float(text.replace(",", "."))
            assert amount > 0
        except Exception:
            await message.answer("❌ Введите корректное количество BTC, например <code>0.5</code>:", parse_mode="HTML")
            return
        await state.update_data(promo_amount=amount)
        await message.answer(
            f"₿ BTC: <b>{amount}</b>\n\n"
            "Введите <b>количество активаций</b>:",
            parse_mode="HTML",
        )
    else:
        amount = parse_k(text)
        if amount is None or amount <= 0:
            await message.answer(
                "❌ Введите корректную сумму.\n\n"
                "📌 Примеры:\n"
                "• <code>1000</code> — тысяча\n"
                "• <code>100к</code> — 100 000\n"
                "• <code>1кк</code> — 1 000 000\n"
                "• <code>50кк</code> — 50 000 000",
                parse_mode="HTML",
            )
            return
        await state.update_data(promo_amount=amount)
        await message.answer(
            f"Сумма: <b>{format_amount(amount)}</b>\n\n"
            "Введите <b>количество активаций</b> (сколько раз можно использовать промокод):",
            parse_mode="HTML",
        )
    await state.set_state(CreatePromoState.waiting_for_uses)


@router.message(CreatePromoState.waiting_for_uses)
async def promo_set_uses(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        uses = int(text)
        if uses <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное количество активаций (целое положительное число):")
        return
    data = await state.get_data()
    code = data["promo_code"]
    reward_type = data["promo_type"]
    amount = data["promo_amount"]
    if reward_type == "money":
        type_label = "💵 Деньги ($)"
        amount_label = f"{format_amount(amount)}$"
    elif reward_type == "bits":
        type_label = "💎 Донат (DC)"
        amount_label = f"{format_amount(amount)} DC"
    elif reward_type == "btc":
        type_label = "₿ BTC"
        amount_label = f"{amount} BTC"
    else:
        type_label = "⭐ VIP статус"
        amount_label = f"{amount} дн."
    await state.update_data(promo_uses=uses)
    await message.answer(
        "━━━━━━━━━━━━━━━\n"
        "🎟 <b>Итог промокода</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        f"🔑 Код: <code>{code}</code>\n"
        f"🎁 Тип: {type_label}\n"
        f"💰 Кол-во: <b>{amount_label}</b>\n"
        f"🔢 Активаций: <b>{uses}</b>\n\n"
        "━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=promo_confirm_kb(code),
    )


@router.callback_query(F.data.startswith("promo_confirm_"))
async def promo_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    code = data.get("promo_code")
    reward_type = data.get("promo_type")
    amount = data.get("promo_amount")
    uses = data.get("promo_uses")

    if not all([code, reward_type, amount, uses]):
        await callback.answer("Ошибка данных. Попробуйте снова.", show_alert=True)
        await state.clear()
        return

    promos = load_promos()
    promos[code] = {
        "type": reward_type,
        "amount": amount,
        "max_uses": uses,
        "used_by": [],
        "created_by": callback.from_user.id,
    }
    save_promos(promos)
    await state.clear()

    if reward_type == "money":
        type_label = "💵 Деньги ($)"
        amount_label = f"{format_amount(amount)}$"
    elif reward_type == "bits":
        type_label = "💎 Донат (DC)"
        amount_label = f"{format_amount(amount)} DC"
    elif reward_type == "btc":
        type_label = "₿ BTC"
        amount_label = f"{amount} BTC"
    else:
        type_label = "⭐ VIP статус"
        amount_label = f"{amount} дн."
    await callback.message.edit_text(
        f"✅ Промокод успешно создан!\n\n"
        f"🔑 Код: <code>{code}</code>\n"
        f"🎁 Тип: {type_label}\n"
        f"💰 Кол-во: <b>{amount_label}</b>\n"
        f"🔢 Активаций: <b>{uses}</b>",
        parse_mode="HTML",
    )
    await callback.answer("Промокод создан!")


@router.message(F.text.lower().startswith(("промо ", "promo ", "активировать ", "активация ")))
async def cmd_activate_promo(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user.get("name", "Без имени")

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите код промокода.\n"
            "Пример: <code>промо BLACKLINE</code>",
            parse_mode="HTML",
        )
        return

    code = parts[1].strip().upper()
    promos = load_promos()

    if code not in promos:
        await message.answer(
            f"❌ Промокод <code>{code}</code> не найден.",
            parse_mode="HTML",
        )
        return

    promo = promos[code]
    used_by = promo.get("used_by", [])

    if user_id in used_by:
        await message.answer(
            f"❌ {clickable_name(user_id, name)}, вы уже активировали этот промокод.",
            parse_mode="HTML",
        )
        return

    if len(used_by) >= promo["max_uses"]:
        await message.answer(
            f"❌ Промокод <code>{code}</code> исчерпан — все активации использованы.",
            parse_mode="HTML",
        )
        return

    reward_type = promo["type"]
    amount = promo["amount"]

    if reward_type == "money":
        update_balance(user_id, get_balance(user_id) + amount)
        save_user_data()
        reward_text = f"<b>+{format_amount(amount)}$</b>"
        new_val_text = f"💰 Новый баланс: <b>{format_amount(get_balance(user_id))}$</b>"
    elif reward_type == "bits":
        user["donate_coins"] = user.get("donate_coins", 0) + amount
        save_user_data()
        reward_text = f"<b>+{format_amount(amount)} DC</b>"
        new_val_text = f"💎 Донат: <b>{format_amount(user['donate_coins'])} DC</b>"
    elif reward_type == "btc":
        from farm import get_farm, flush_farm, _fmt_btc
        farm = get_farm(user_id)
        flush_farm(farm)
        if farm.get("farm_level", 0) == 0:
            farm["farm_level"] = 1
            farm["btc_balance"] = 0.0
            farm["mining_start"] = 0
        farm["btc_balance"] = round(farm.get("btc_balance", 0.0) + float(amount), 8)
        save_user_data()
        reward_text = f"<b>+{_fmt_btc(float(amount))} BTC</b>"
        new_val_text = f"₿ BTC баланс: <b>{_fmt_btc(farm['btc_balance'])}</b>"
    else:
        from donate import get_donate_user_data
        d = get_donate_user_data(user)
        d["vip"] = True
        save_user_data()
        reward_text = f"<b>⭐ VIP на {amount} дн.</b>"
        new_val_text = "⭐ VIP статус активирован!"

    promo["used_by"].append(user_id)
    save_promos(promos)

    await message.answer(
        f"✅ Промокод <code>{code}</code> активирован!\n\n"
        f"🎁 Награда: {reward_text}\n"
        f"{new_val_text}",
        parse_mode="HTML",
    )


def _build_promo_list_text(promos: dict) -> str:
    text = "📋 <b>Список промокодов:</b>\n\n"
    for code, data in promos.items():
        reward_type = "💵" if data["type"] == "money" else "💎"
        used = len(data.get("used_by", []))
        total = data["max_uses"]
        amount = data["amount"]
        status = "✅" if used < total else "❌"
        text += f"{status} <code>{code}</code> — {reward_type} {format_amount(amount)} [{used}/{total}]\n"
    text += "\n👆 Нажмите на промокод для подробностей"
    return text


def _build_promo_list_kb(promos: dict) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"🔑 {code}", callback_data=f"promo_info_{code}")]
        for code in promos
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_promo_info_text(code: str, data: dict) -> str:
    _type = data["type"]
    if _type == "money":
        reward_type = "💵 Деньги ($)"
    elif _type == "bits":
        reward_type = "💎 Донат (DC)"
    elif _type == "btc":
        reward_type = "₿ BTC"
    else:
        reward_type = "⭐ VIP статус"
    used_by = data.get("used_by", [])
    used = len(used_by)
    total = data["max_uses"]
    remaining = total - used
    status = "✅ Активен" if used < total else "❌ Исчерпан"
    amount = data["amount"]

    users_list = ""
    if used_by:
        from utils import get_user as _get_user
        for uid in used_by[-10:]:
            u = _get_user(uid)
            uname = u.get("name", "Без имени") if u else str(uid)
            users_list += f"  • {uname} (ID: <code>{uid}</code>)\n"
        if used > 10:
            users_list += f"  ... и ещё {used - 10}\n"
    else:
        users_list = "  Никто ещё не активировал\n"

    return (
        f"━━━━━━━━━━━━━━━\n"
        f"🎟 <b>Промокод: <code>{code}</code></b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📌 Статус: {status}\n"
        f"🎁 Тип: {reward_type}\n"
        f"💰 Сумма: <b>{format_amount(amount)}</b>\n\n"
        f"📊 Активаций: <b>{used} / {total}</b>\n"
        f"🔓 Осталось: <b>{remaining}</b>\n\n"
        f"👥 Активировали:\n{users_list}\n"
        f"━━━━━━━━━━━━━━━"
    )


def _build_promo_info_kb(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить промокод", callback_data=f"promo_del_{code}")],
            [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="promo_back_to_list")],
        ]
    )


@router.message(F.text.lower().in_(["промокоды", "список промо", "📋 промокоды"]))
async def cmd_list_promos(message: Message):
    if not is_admin_or_owner(message.from_user.id):
        await message.answer("❌ У вас нет прав для просмотра промокодов.")
        return
    promos = load_promos()
    if not promos:
        await message.answer("📋 Промокодов нет.")
        return
    await message.answer(
        _build_promo_list_text(promos),
        parse_mode="HTML",
        reply_markup=_build_promo_list_kb(promos),
    )


@router.callback_query(F.data.startswith("promo_info_"))
async def promo_info_callback(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("Нет прав.", show_alert=True)
        return
    code = callback.data.replace("promo_info_", "")
    promos = load_promos()
    if code not in promos:
        await callback.answer("Промокод не найден.", show_alert=True)
        return
    await callback.message.edit_text(
        _build_promo_info_text(code, promos[code]),
        parse_mode="HTML",
        reply_markup=_build_promo_info_kb(code),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("promo_del_"))
async def promo_delete_confirm(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("Нет прав.", show_alert=True)
        return
    code = callback.data.replace("promo_del_", "")
    promos = load_promos()
    if code in promos:
        del promos[code]
        save_promos(promos)
        await callback.message.edit_text(
            f"✅ Промокод <code>{code}</code> удалён.\n\n"
            "Нажмите 📋 Промокоды для просмотра оставшихся.",
            parse_mode="HTML",
        )
    else:
        await callback.answer("Промокод не найден.", show_alert=True)
    await callback.answer()


@router.callback_query(F.data == "promo_back_to_list")
async def promo_back_to_list(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("Нет прав.", show_alert=True)
        return
    promos = load_promos()
    if not promos:
        await callback.message.edit_text("📋 Промокодов нет.")
        await callback.answer()
        return
    await callback.message.edit_text(
        _build_promo_list_text(promos),
        parse_mode="HTML",
        reply_markup=_build_promo_list_kb(promos),
    )
    await callback.answer()
