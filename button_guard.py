"""
Защита кнопок — только владелец сообщения может нажимать кнопки.

Принцип работы:
1. SetCurrentUserMiddleware — запоминает user_id текущего обработчика через contextvar.
2. TrackSentMessagesMiddleware — API-middleware: после каждой отправки сообщения с
   inline-клавиатурой регистрирует (chat_id, message_id) -> user_id.
3. ButtonOwnerMiddleware — перед обработкой callback_query проверяет, совпадает ли
   callback.from_user.id с зарегистрированным владельцем. Если нет и это не админ —
   отвечает "❌ Это не твои кнопки!" и блокирует обработчик.

Установка (bot.py):
    from button_guard import setup_button_guard
    setup_button_guard(dp, bot)
"""

import contextvars
from typing import Any, Callable, Awaitable

from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import TelegramObject, CallbackQuery
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.methods import (
    SendMessage, SendPhoto, SendDocument, SendAnimation,
    SendVideo, SendAudio, SendSticker, EditMessageText,
    EditMessageCaption, EditMessageReplyMarkup,
)

_current_user_ctx: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "button_guard_user_id", default=None
)

_button_owners: dict[tuple[int, int], int] = {}
_MAX_TRACKED = 8_000

SEND_METHODS = (
    SendMessage, SendPhoto, SendDocument, SendAnimation,
    SendVideo, SendAudio, SendSticker,
)
EDIT_METHODS = (EditMessageText, EditMessageCaption, EditMessageReplyMarkup)

PUBLIC_CALLBACKS = {
    "show_menu", "show_alert", "mn_noop", "cases_main", "cases_shop",
    "ip_cancel", "alist_back", "alist_noop",
}
PUBLIC_PREFIXES = (
    "donate_", "show_alert:", "rzv_", "raffle_join_",
)


def _has_inline_kb(method) -> bool:
    kb = getattr(method, "reply_markup", None)
    if kb is None:
        return False
    return bool(getattr(kb, "inline_keyboard", None))


def _register(chat_id: int, msg_id: int, user_id: int) -> None:
    global _button_owners
    if len(_button_owners) > _MAX_TRACKED:
        keys = list(_button_owners.keys())[:_MAX_TRACKED // 2]
        for k in keys:
            del _button_owners[k]
    _button_owners[(chat_id, msg_id)] = user_id


def _is_public(cb_data: str) -> bool:
    if cb_data in PUBLIC_CALLBACKS:
        return True
    return any(cb_data.startswith(p) for p in PUBLIC_PREFIXES)


class SetCurrentUserMiddleware(BaseMiddleware):
    """Устанавливает contextvar с user_id до вызова любого обработчика."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        uid: int | None = None
        user = data.get("event_from_user")
        if user:
            uid = user.id
        token = _current_user_ctx.set(uid)
        try:
            return await handler(event, data)
        finally:
            _current_user_ctx.reset(token)


class TrackSentMessagesMiddleware(BaseRequestMiddleware):
    """
    API-level middleware: после отправки сообщения с inline-клавиатурой
    регистрирует (chat_id, message_id) -> current_user_id.
    """

    async def __call__(self, make_request, bot, method):
        result = await make_request(bot, method)

        try:
            uid = _current_user_ctx.get()
            if uid is None:
                return result

            if isinstance(method, SEND_METHODS) and _has_inline_kb(method):
                if result and hasattr(result, "message_id") and hasattr(result, "chat"):
                    _register(result.chat.id, result.message_id, uid)

            elif isinstance(method, EDIT_METHODS) and _has_inline_kb(method):
                chat_id = getattr(method, "chat_id", None)
                msg_id = getattr(method, "message_id", None)
                if chat_id and msg_id:
                    _register(chat_id, msg_id, uid)

        except Exception:
            pass

        return result


class ButtonOwnerMiddleware(BaseMiddleware):
    """Блокирует callback_query от посторонних пользователей."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        cb_data = event.data or ""

        if _is_public(cb_data):
            return await handler(event, data)

        msg = event.message
        if msg is None:
            return await handler(event, data)

        owner_id = _button_owners.get((msg.chat.id, msg.message_id))
        if owner_id is None:
            return await handler(event, data)

        if owner_id == event.from_user.id:
            return await handler(event, data)

        await event.answer("❌ Это не твои кнопки!", show_alert=True)
        return None


def setup_button_guard(dp: Dispatcher, bot) -> None:
    """Регистрирует все middleware защиты кнопок."""
    dp.update.outer_middleware(SetCurrentUserMiddleware())
    dp.callback_query.outer_middleware(ButtonOwnerMiddleware())
    bot.session.middleware(TrackSentMessagesMiddleware())
