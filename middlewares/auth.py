"""Authorization middleware for Master Bot."""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.repositories import get_admin, is_admin


class AdminCheckMiddleware(BaseMiddleware):
    """Restrict Master Bot private messages & callbacks to registered admins/owner."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
            # Allow group messages (support group replies) to pass
            if event.chat and event.chat.type in ("group", "supergroup"):
                return await handler(event, data)
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user is None:
            return await handler(event, data)

        admin = await get_admin(user.id)
        if admin is None:
            if isinstance(event, Message):
                await event.answer(
                    "⛔ <b>Access Denied</b>\n\n"
                    "You are not authorized to use this bot.\n"
                    "Contact the owner if you believe this is an error.",
                    parse_mode="HTML",
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Access denied", show_alert=True)
            return None

        data["admin"] = admin
        return await handler(event, data)
