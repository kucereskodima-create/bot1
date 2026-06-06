"""
МОДЕРАЦИЯ ГРУППЫ — команды для Telegram-администраторов в группах.

Форматы:
  бан @user/ID причина 7д|навсегда
  мут @user/ID причина 1ч|30м|навсегда
  варн @user/ID причина
  снять бан @user/ID
  снять мут @user/ID
  снять варн @user/ID

3 варна = автобан навсегда.
Только Telegram-администраторы группы могут использовать.
"""

import json
import os
import re
import time

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from utils import get_user, find_user_by_identifier, save_user_data, format_amount, clickable_name
import utils

router = Router()

WARNS_FILE = os.path.join(os.path.dirname(__file__), "admin_warns.json")
GROUP_BANS_FILE = os.path.join(os.path.dirname(__file__), "group_bans.json")
GROUP_MUTES_FILE = os.path.join(os.path.dirname(__file__), "group_mutes.json")
MAX_WARNS = 3


# ──────────────────────────────────────────────────────────────────────────────
#  Хранилища
# ──────────────────────────────────────────────────────────────────────────────

def _load_warns() -> dict:
    if os.path.exists(WARNS_FILE):
        try:
            with open(WARNS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_warns(data: dict):
    with open(WARNS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_gbans() -> dict:
    if os.path.exists(GROUP_BANS_FILE):
        try:
            with open(GROUP_BANS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_gbans(data: dict):
    with open(GROUP_BANS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_gmutes() -> dict:
    if os.path.exists(GROUP_MUTES_FILE):
        try:
            with open(GROUP_MUTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_gmutes(data: dict):
    with open(GROUP_MUTES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────────────────────────────────────
#  Вспомогательные функции
# ──────────────────────────────────────────────────────────────────────────────

def get_warns(user_id: int) -> list:
    warns = _load_warns()
    return warns.get(str(user_id), [])


def add_warn(user_id: int, admin_id: int, reason: str, chat_id: int = None) -> int:
    warns = _load_warns()
    uid = str(user_id)
    if uid not in warns:
        warns[uid] = []
    warns[uid].append({
        "reason": reason,
        "by": admin_id,
        "ts": time.time(),
        "chat_id": chat_id,
    })
    _save_warns(warns)
    return len(warns[uid])


def remove_last_warn(user_id: int) -> bool:
    warns = _load_warns()
    uid = str(user_id)
    if uid in warns and warns[uid]:
        warns[uid].pop()
        _save_warns(warns)
        return True
    return False


def clear_warns(user_id: int):
    warns = _load_warns()
    warns[str(user_id)] = []
    _save_warns(warns)


def parse_duration(token: str) -> tuple:
    """
    Парсит строку времени. Возвращает (seconds, label) или (None, None).
    Поддерживает: 1д, 7д, 30м, 1ч, навсегда
    """
    token = token.strip().lower()
    if token in ("навсегда", "permanent", "inf", "perma", "пермач"):
        return 0, "навсегда"
    m = re.match(r"^(\d+)(д|ч|м|h|d|m)$", token)
    if not m:
        return None, None
    n = int(m.group(1))
    unit = m.group(2)
    if unit in ("д", "d"):
        return n * 86400, f"{n} дн."
    if unit in ("ч", "h"):
        return n * 3600, f"{n} ч."
    if unit in ("м", "m"):
        return n * 60, f"{n} мин."
    return None, None


async def is_group_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def resolve_target(text: str) -> tuple:
    """Пытается найти пользователя по @username, ID или game_id."""
    uid, user = find_user_by_identifier(text.strip(), utils.user_data)
    return uid, user


def _fmt_warn_list(warns: list) -> str:
    if not warns:
        return "нет"
    lines = []
    for i, w in enumerate(warns, 1):
        ts = time.strftime("%d.%m %H:%M", time.localtime(w.get("ts", 0)))
        lines.append(f"  {i}. {w.get('reason', '?')} [{ts}]")
    return "\n" + "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
#  Парсинг цели (реплай или идентификатор)
# ──────────────────────────────────────────────────────────────────────────────

def _parse_target_and_args(message: Message, has_duration: bool = False):
    """
    Возвращает (target_id, name, reason, duration_str, error_str).
    Поддерживает:
      - Реплай на сообщение → цель из reply_to_message
      - @username / числовой ID в аргументах
    """
    text = message.text or ""
    parts = text.strip().split()
    cmd_parts = parts[0].lstrip("/").lower()

    if message.reply_to_message and message.reply_to_message.from_user:
        ru = message.reply_to_message.from_user
        target_id = ru.id
        name = ru.full_name or f"ID:{ru.id}"
        args = parts[1:]
        if has_duration:
            if args and parse_duration(args[-1])[0] is not None:
                duration_str = args[-1]
                reason = " ".join(args[:-1]) or "Без причины"
            else:
                duration_str = "навсегда"
                reason = " ".join(args) or "Без причины"
        else:
            reason = " ".join(args) or "Без причины"
            duration_str = "навсегда"
        return target_id, name, reason, duration_str, None

    if len(parts) < 2:
        return None, None, None, None, "no_identifier"

    identifier = parts[1]
    uid, user = resolve_target(identifier)
    try:
        tg_id = int(identifier.lstrip("@")) if identifier.lstrip("@").isdigit() else None
    except Exception:
        tg_id = None

    if uid is None and tg_id is None:
        return None, None, None, None, identifier

    target_id = uid or tg_id
    name = user.get("name", f"ID:{target_id}") if user else f"ID:{target_id}"

    rest = parts[2:]
    if has_duration:
        if rest and parse_duration(rest[-1])[0] is not None:
            duration_str = rest[-1]
            reason = " ".join(rest[:-1]) or "Без причины"
        else:
            duration_str = "навсегда"
            reason = " ".join(rest) or "Без причины"
    else:
        reason = " ".join(rest) or "Без причины"
        duration_str = "навсегда"

    return target_id, name, reason, duration_str, None


# ──────────────────────────────────────────────────────────────────────────────
#  /мод — справка по командам
# ──────────────────────────────────────────────────────────────────────────────

@router.message(F.text.lower() == "мод")
@router.message(Command("мод"))
async def cmd_mod_help(message: Message):
    if message.chat.type == "private":
        return
    from config import bot
    if not await is_group_admin(bot, message.chat.id, message.from_user.id):
        return
    text = (
        "🛡 <b>Команды модерации</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>🚫 Бан</b>\n"
        "  <code>бан @user причина 7д</code>\n"
        "  <code>/бан @user причина навсегда</code>\n"
        "  <i>или реплай: </i><code>бан причина 7д</code>\n\n"
        "<b>🔇 Мут</b>\n"
        "  <code>мут @user причина 1ч</code>\n"
        "  <code>/мут @user причина 30м</code>\n"
        "  <i>или реплай: </i><code>мут причина 1ч</code>\n\n"
        "<b>⚠️ Варн</b>\n"
        "  <code>варн @user причина</code>\n"
        "  <code>/варн @user причина</code>\n"
        "  <i>или реплай: </i><code>варн причина</code>\n\n"
        "<b>✅ Снять бан</b>\n"
        "  <code>разбан @user</code>  /  <code>/разбан @user</code>\n\n"
        "<b>🔈 Снять мут</b>\n"
        "  <code>размут @user</code>  /  <code>/размут @user</code>\n"
        "  <i>или реплай: </i><code>размут</code>\n\n"
        "<b>🗑 Снять варн</b>\n"
        "  <code>снять варн @user</code>  /  <code>/снять_варн @user</code>\n"
        "  <i>или реплай: </i><code>снять варн</code>\n\n"
        "<b>📋 Варны игрока</b>\n"
        "  <code>варны @user</code>  /  <code>/варны @user</code>\n\n"
        "<i>⏱ Форматы времени: 30м · 1ч · 7д · навсегда</i>"
    )
    await message.reply(text, parse_mode="HTML")


# ──────────────────────────────────────────────────────────────────────────────
#  БАН
# ──────────────────────────────────────────────────────────────────────────────

@router.message(F.text.lower().startswith("бан ") | F.text.lower() == "бан")
@router.message(Command("бан"))
async def cmd_ban(message: Message):
    if message.chat.type == "private":
        return
    from config import bot
    chat_id = message.chat.id
    admin_id = message.from_user.id

    if not await is_group_admin(bot, chat_id, admin_id):
        await message.reply("⛔ Только администраторы группы могут банить!")
        return

    target_id, name, reason, duration_str, err = _parse_target_and_args(message, has_duration=True)
    if err == "no_identifier" and not message.reply_to_message:
        await message.reply(
            "❌ Укажи цель или ответь на сообщение:\n"
            "<code>бан @user причина 7д</code>",
            parse_mode="HTML"
        )
        return
    if err and err != "no_identifier":
        await message.reply(f"❌ Пользователь <code>{err}</code> не найден.", parse_mode="HTML")
        return

    seconds, label = parse_duration(duration_str)
    if seconds is None:
        seconds, label = 0, "навсегда"

    try:
        if seconds == 0:
            await bot.ban_chat_member(chat_id, target_id)
        else:
            await bot.ban_chat_member(chat_id, target_id, until_date=int(time.time()) + seconds)
    except Exception as e:
        await message.reply(f"❌ Не удалось забанить: {e}")
        return

    bans = _load_gbans()
    cid = str(chat_id)
    if cid not in bans:
        bans[cid] = {}
    bans[cid][str(target_id)] = {
        "reason": reason, "by": admin_id, "ts": time.time(),
        "permanent": seconds == 0,
        "until": time.time() + seconds if seconds > 0 else None,
        "label": label,
    }
    _save_gbans(bans)

    await message.reply(
        f"🚫 <b>{name}</b> забанен!\n"
        f"📋 Причина: {reason}\n"
        f"⏱ Срок: <b>{label}</b>",
        parse_mode="HTML"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  МУТ
# ──────────────────────────────────────────────────────────────────────────────

@router.message(F.text.lower().startswith("мут ") | F.text.lower() == "мут")
@router.message(Command("мут"))
async def cmd_mute(message: Message):
    if message.chat.type == "private":
        return
    from config import bot
    chat_id = message.chat.id
    admin_id = message.from_user.id

    if not await is_group_admin(bot, chat_id, admin_id):
        await message.reply("⛔ Только администраторы группы могут мутить!")
        return

    target_id, name, reason, duration_str, err = _parse_target_and_args(message, has_duration=True)
    if err == "no_identifier" and not message.reply_to_message:
        await message.reply(
            "❌ Укажи цель или ответь на сообщение:\n"
            "<code>мут @user причина 1ч</code>",
            parse_mode="HTML"
        )
        return
    if err and err != "no_identifier":
        await message.reply(f"❌ Пользователь <code>{err}</code> не найден.", parse_mode="HTML")
        return

    seconds, label = parse_duration(duration_str)
    if seconds is None:
        seconds, label = 3600, "1 ч."

    no_perms = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_polls=False,
        can_send_other_messages=False,
    )
    try:
        if seconds == 0:
            await bot.restrict_chat_member(chat_id, target_id, permissions=no_perms)
        else:
            await bot.restrict_chat_member(chat_id, target_id, permissions=no_perms,
                                           until_date=int(time.time()) + seconds)
    except Exception as e:
        await message.reply(f"❌ Не удалось замутить: {e}")
        return

    mutes = _load_gmutes()
    cid = str(chat_id)
    if cid not in mutes:
        mutes[cid] = {}
    mutes[cid][str(target_id)] = {
        "reason": reason, "by": admin_id, "ts": time.time(),
        "permanent": seconds == 0,
        "until": time.time() + seconds if seconds > 0 else None,
        "label": label,
    }
    _save_gmutes(mutes)

    await message.reply(
        f"🔇 <b>{name}</b> замьючен!\n"
        f"📋 Причина: {reason}\n"
        f"⏱ Срок: <b>{label}</b>",
        parse_mode="HTML"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  ВАРН
# ──────────────────────────────────────────────────────────────────────────────

@router.message(F.text.lower().startswith("варн ") | F.text.lower() == "варн")
@router.message(Command("варн"))
async def cmd_warn(message: Message):
    if message.chat.type == "private":
        return
    from config import bot
    chat_id = message.chat.id
    admin_id = message.from_user.id

    if not await is_group_admin(bot, chat_id, admin_id):
        await message.reply("⛔ Только администраторы группы могут выдавать варны!")
        return

    target_id, name, reason, _, err = _parse_target_and_args(message, has_duration=False)
    if err == "no_identifier" and not message.reply_to_message:
        await message.reply(
            "❌ Укажи цель или ответь на сообщение:\n"
            "<code>варн @user причина</code>",
            parse_mode="HTML"
        )
        return
    if err and err != "no_identifier":
        await message.reply(f"❌ Пользователь <code>{err}</code> не найден.", parse_mode="HTML")
        return

    warn_count = add_warn(target_id, admin_id, reason, chat_id)

    if warn_count >= MAX_WARNS:
        try:
            await bot.ban_chat_member(chat_id, target_id)
        except Exception:
            pass
        clear_warns(target_id)
        await message.reply(
            f"⚠️ <b>{name}</b> получил варн <b>{warn_count}/{MAX_WARNS}</b>\n"
            f"📋 Причина: {reason}\n\n"
            f"🚫 <b>Автобан!</b> Достигнут лимит варнов.",
            parse_mode="HTML"
        )
    else:
        left = MAX_WARNS - warn_count
        await message.reply(
            f"⚠️ <b>{name}</b> получил варн <b>{warn_count}/{MAX_WARNS}</b>\n"
            f"📋 Причина: {reason}\n\n"
            f"{'⛔ Следующий варн — автобан!' if left == 1 else f'До автобана: {left} варн(а)'}",
            parse_mode="HTML"
        )


# ──────────────────────────────────────────────────────────────────────────────
#  РАЗБАН
# ──────────────────────────────────────────────────────────────────────────────

@router.message(F.text.lower().startswith("разбан ") | F.text.lower() == "разбан")
@router.message(F.text.lower().startswith("снять бан"))
@router.message(Command("разбан"))
async def cmd_unban(message: Message):
    if message.chat.type == "private":
        return
    from config import bot
    chat_id = message.chat.id
    admin_id = message.from_user.id

    if not await is_group_admin(bot, chat_id, admin_id):
        await message.reply("⛔ Только администраторы группы могут снимать бан!")
        return

    text = message.text or ""
    parts = text.strip().split()

    if message.reply_to_message and message.reply_to_message.from_user:
        ru = message.reply_to_message.from_user
        target_id = ru.id
        name = ru.full_name or f"ID:{ru.id}"
    else:
        identifier = parts[-1] if len(parts) >= 2 else None
        if not identifier or identifier.lower() in ("бан", "разбан"):
            await message.reply(
                "❌ Укажи цель или ответь на сообщение:\n"
                "<code>разбан @user</code>",
                parse_mode="HTML"
            )
            return
        uid, user = resolve_target(identifier)
        try:
            tg_id = int(identifier.lstrip("@")) if identifier.lstrip("@").isdigit() else None
        except Exception:
            tg_id = None
        if uid is None and tg_id is None:
            await message.reply(f"❌ Пользователь <code>{identifier}</code> не найден.", parse_mode="HTML")
            return
        target_id = uid or tg_id
        name = user.get("name", f"ID:{target_id}") if user else f"ID:{target_id}"

    try:
        await bot.unban_chat_member(chat_id, target_id, only_if_banned=True)
    except Exception as e:
        await message.reply(f"❌ Не удалось снять бан: {e}")
        return

    bans = _load_gbans()
    cid = str(chat_id)
    if cid in bans and str(target_id) in bans[cid]:
        del bans[cid][str(target_id)]
        _save_gbans(bans)

    await message.reply(f"✅ Бан снят с <b>{name}</b>!", parse_mode="HTML")


# ──────────────────────────────────────────────────────────────────────────────
#  РАЗМУТ
# ──────────────────────────────────────────────────────────────────────────────

@router.message(F.text.lower().startswith("размут ") | F.text.lower() == "размут")
@router.message(F.text.lower().startswith("снять мут"))
@router.message(Command("размут"))
async def cmd_unmute(message: Message):
    if message.chat.type == "private":
        return
    from config import bot
    chat_id = message.chat.id
    admin_id = message.from_user.id

    if not await is_group_admin(bot, chat_id, admin_id):
        await message.reply("⛔ Только администраторы группы могут снимать мут!")
        return

    text = message.text or ""
    parts = text.strip().split()

    if message.reply_to_message and message.reply_to_message.from_user:
        ru = message.reply_to_message.from_user
        target_id = ru.id
        name = ru.full_name or f"ID:{ru.id}"
    else:
        identifier = parts[-1] if len(parts) >= 2 else None
        if not identifier or identifier.lower() in ("мут", "размут"):
            await message.reply(
                "❌ Укажи цель или ответь на сообщение:\n"
                "<code>размут @user</code>",
                parse_mode="HTML"
            )
            return
        uid, user = resolve_target(identifier)
        try:
            tg_id = int(identifier.lstrip("@")) if identifier.lstrip("@").isdigit() else None
        except Exception:
            tg_id = None
        if uid is None and tg_id is None:
            await message.reply(f"❌ Пользователь <code>{identifier}</code> не найден.", parse_mode="HTML")
            return
        target_id = uid or tg_id
        name = user.get("name", f"ID:{target_id}") if user else f"ID:{target_id}"

    full_perms = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
    )
    try:
        await bot.restrict_chat_member(chat_id, target_id, permissions=full_perms)
    except Exception as e:
        await message.reply(f"❌ Не удалось снять мут: {e}")
        return

    mutes = _load_gmutes()
    cid = str(chat_id)
    if cid in mutes and str(target_id) in mutes[cid]:
        del mutes[cid][str(target_id)]
        _save_gmutes(mutes)

    await message.reply(f"🔈 Мут снят с <b>{name}</b>!", parse_mode="HTML")


# ──────────────────────────────────────────────────────────────────────────────
#  СНЯТЬ ВАРН
# ──────────────────────────────────────────────────────────────────────────────

@router.message(F.text.lower().startswith("снять варн"))
@router.message(Command("снять_варн"))
async def cmd_unwarn(message: Message):
    if message.chat.type == "private":
        return
    from config import bot
    chat_id = message.chat.id
    admin_id = message.from_user.id

    if not await is_group_admin(bot, chat_id, admin_id):
        await message.reply("⛔ Только администраторы группы могут снимать варны!")
        return

    text = message.text or ""
    parts = text.strip().split()

    if message.reply_to_message and message.reply_to_message.from_user:
        ru = message.reply_to_message.from_user
        target_id = ru.id
        name = ru.full_name or f"ID:{ru.id}"
        uid = target_id
    else:
        identifier = parts[-1] if len(parts) >= 2 else None
        if not identifier or identifier.lower() in ("варн",):
            await message.reply(
                "❌ Укажи цель или ответь на сообщение:\n"
                "<code>снять варн @user</code>",
                parse_mode="HTML"
            )
            return
        uid, user = resolve_target(identifier)
        if uid is None:
            await message.reply(f"❌ Пользователь <code>{identifier}</code> не найден.", parse_mode="HTML")
            return
        name = user.get("name", f"ID:{uid}") if user else f"ID:{uid}"

    removed = remove_last_warn(uid)
    current = len(get_warns(uid))

    if removed:
        await message.reply(
            f"✅ Последний варн снят с <b>{name}</b>!\n"
            f"📊 Текущих варнов: <b>{current}/{MAX_WARNS}</b>",
            parse_mode="HTML"
        )
    else:
        await message.reply(f"ℹ️ У <b>{name}</b> нет активных варнов.", parse_mode="HTML")


# ──────────────────────────────────────────────────────────────────────────────
#  ВАРНЫ — просмотр
# ──────────────────────────────────────────────────────────────────────────────

@router.message(F.text.lower().startswith("варны "))
@router.message(Command("варны"))
async def cmd_check_warns(message: Message):
    if message.chat.type == "private":
        return
    from config import bot
    chat_id = message.chat.id
    admin_id = message.from_user.id

    if not await is_group_admin(bot, chat_id, admin_id):
        await message.reply("⛔ Только администраторы могут смотреть варны!")
        return

    text = message.text or ""
    parts = text.strip().split()

    if message.reply_to_message and message.reply_to_message.from_user:
        ru = message.reply_to_message.from_user
        uid = ru.id
        name = ru.full_name or f"ID:{ru.id}"
    else:
        if len(parts) < 2:
            await message.reply(
                "❌ Укажи цель или ответь на сообщение:\n"
                "<code>варны @user</code>",
                parse_mode="HTML"
            )
            return
        identifier = parts[1]
        uid, user = resolve_target(identifier)
        if uid is None:
            await message.reply(f"❌ Пользователь <code>{identifier}</code> не найден.", parse_mode="HTML")
            return
        name = user.get("name", f"ID:{uid}") if user else f"ID:{uid}"

    warns = get_warns(uid)
    wlist = _fmt_warn_list(warns)

    await message.reply(
        f"⚠️ <b>Варны игрока {name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Варнов: <b>{len(warns)}/{MAX_WARNS}</b>\n"
        f"{wlist}",
        parse_mode="HTML"
    )
