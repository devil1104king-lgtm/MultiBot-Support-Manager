"""Handlers for every connected (child) bot."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from loguru import logger

from database.repositories import get_bot_by_id, increment_bot_stat, log_activity
from services.support_service import forward_to_support, maybe_send_auto_reply


def create_child_router(bot_id: int) -> Router:
    """Create an isolated router for one connected bot."""
    router = Router(name=f"child_{bot_id}")

    @router.message(CommandStart())
    async def cmd_start(message: Message, bot) -> None:
        bot_doc = await get_bot_by_id(bot_id)
        if not bot_doc or not bot_doc.is_active:
            await message.answer("⚠️ This bot is currently unavailable.")
            return

        if bot_doc.welcome_enabled and bot_doc.welcome_message:
            await message.answer(bot_doc.welcome_message)
        else:
            await message.answer(
                "👋 Welcome!\n\nSend a message and our support team will reply soon."
            )
        await log_activity("user_start", actor_id=message.from_user.id, bot_id=bot_id)

    @router.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        await message.answer(
            "ℹ️ <b>Help</b>\n\n"
            "Simply send any message (text, photo, video, document…) and our support team "
            "will receive it and reply here.\n\n"
            "Commands:\n"
            "/start – Restart\n"
            "/help – This message\n"
            "/contact – Contact support"
        )

    @router.message(Command("contact"))
    async def cmd_contact(message: Message) -> None:
        await message.answer(
            "📬 <b>Contact Support</b>\n\n"
            "Just type your question or problem below. "
            "A human agent will answer as soon as possible."
        )

    @router.message(F.chat.type == "private")
    async def handle_private_message(message: Message, bot) -> None:
        """Main entry: forward every private message to the support group."""
        bot_doc = await get_bot_by_id(bot_id)
        if not bot_doc or not bot_doc.is_active:
            return

        # Ignore commands already handled
        if message.text and message.text.startswith("/"):
            return

        try:
            await forward_to_support(bot, message, bot_doc)
            await maybe_send_auto_reply(bot, message, bot_doc)
        except Exception as e:
            logger.exception(f"Error handling message on bot {bot_id}: {e}")

    return router
