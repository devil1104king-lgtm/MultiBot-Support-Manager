"""Simple request logging middleware."""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from loguru import logger


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            logger.debug(
                f"MSG from {event.from_user.id} chat={event.chat.id} "
                f"text={ (event.text or '')[:80] }"
            )
        elif isinstance(event, CallbackQuery) and event.from_user:
            logger.debug(
                f"CB from {event.from_user.id} data={event.data}"
            )
        return await handler(event, data)
