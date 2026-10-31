"""Keyboards used inside the support group."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def support_message_kb(bot_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Buttons attached to every forwarded support message."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ Reply", callback_data=f"sreply:{bot_id}:{user_id}"),
        InlineKeyboardButton(text="👤 User Profile", callback_data=f"suser:{bot_id}:{user_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🤖 Bot Info", callback_data=f"sbot:{bot_id}"),
    )
    return builder.as_markup()
