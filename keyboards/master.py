"""Master bot inline keyboards – premium UI."""

from typing import List, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import AdminDocument, BotDocument
from utils.helpers import status_emoji


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🤖 Manage Bots", callback_data="menu:bots"),
    )
    builder.row(
        InlineKeyboardButton(text="💬 Support Settings", callback_data="menu:support"),
        InlineKeyboardButton(text="👥 Administrators", callback_data="menu:admins"),
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ General Settings", callback_data="menu:settings"),
        InlineKeyboardButton(text="📊 Statistics", callback_data="menu:stats"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Activity Logs", callback_data="menu:logs"),
        InlineKeyboardButton(text="❓ Help & Commands", callback_data="menu:help"),
    )
    return builder.as_markup()


def back_home_kb(back_to: str = "menu:home") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data=back_to),
        InlineKeyboardButton(text="🏠 Home", callback_data="menu:home"),
    )
    return builder.as_markup()


def bots_menu_kb(bots: List[BotDocument], page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * per_page
    chunk = bots[start : start + per_page]

    for bot in chunk:
        emoji = status_emoji(bot.is_active)
        builder.row(
            InlineKeyboardButton(
                text=f"{emoji} @{bot.username}",
                callback_data=f"bot:view:{bot.bot_id}",
            )
        )

    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"bots:page:{page - 1}"))
    if start + per_page < len(bots):
        nav.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"bots:page:{page + 1}"))
    if nav:
        builder.row(*nav)

    builder.row(
        InlineKeyboardButton(text="➕ Add Bot", callback_data="bot:add"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="menu:home"),
        InlineKeyboardButton(text="🏠 Home", callback_data="menu:home"),
    )
    return builder.as_markup()


def bot_detail_kb(bot: BotDocument) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    toggle_text = "🔴 Disable" if bot.is_active else "🟢 Enable"
    builder.row(
        InlineKeyboardButton(text="✏️ Welcome Message", callback_data=f"bot:welcome:{bot.bot_id}"),
        InlineKeyboardButton(text="💬 Auto Reply", callback_data=f"bot:autoreply:{bot.bot_id}"),
    )
    builder.row(
        InlineKeyboardButton(text=toggle_text, callback_data=f"bot:toggle:{bot.bot_id}"),
        InlineKeyboardButton(text="📊 Stats", callback_data=f"bot:stats:{bot.bot_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Remove Bot", callback_data=f"bot:remove:{bot.bot_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="menu:bots"),
        InlineKeyboardButton(text="🏠 Home", callback_data="menu:home"),
    )
    return builder.as_markup()


def confirm_kb(action: str, yes_data: str, no_data: str = "menu:home") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Confirm", callback_data=yes_data),
        InlineKeyboardButton(text="❌ Cancel", callback_data=no_data),
    )
    return builder.as_markup()


def admins_menu_kb(admins: List[AdminDocument], page: int = 0, per_page: int = 6) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * per_page
    chunk = admins[start : start + per_page]

    for admin in chunk:
        role = "👑 Owner" if admin.is_owner else "🛡 Admin"
        name = admin.first_name or admin.username or str(admin.user_id)
        builder.row(
            InlineKeyboardButton(
                text=f"{role} · {name}",
                callback_data=f"admin:view:{admin.user_id}",
            )
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"admins:page:{page - 1}"))
    if start + per_page < len(admins):
        nav.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"admins:page:{page + 1}"))
    if nav:
        builder.row(*nav)

    builder.row(
        InlineKeyboardButton(text="➕ Add Admin", callback_data="admin:add"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="menu:home"),
        InlineKeyboardButton(text="🏠 Home", callback_data="menu:home"),
    )
    return builder.as_markup()


def admin_detail_kb(admin: AdminDocument, viewer_is_owner: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if viewer_is_owner and not admin.is_owner:
        builder.row(
            InlineKeyboardButton(
                text="🗑 Remove Admin",
                callback_data=f"admin:remove:{admin.user_id}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="menu:admins"),
        InlineKeyboardButton(text="🏠 Home", callback_data="menu:home"),
    )
    return builder.as_markup()


def support_settings_kb(group_id: Optional[int] = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    status = f"✅ Set ({group_id})" if group_id else "⚠️ Not configured"
    builder.row(
        InlineKeyboardButton(text=f"📍 Support Group: {status}", callback_data="support:info"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Set / Change Group", callback_data="support:set"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="menu:home"),
        InlineKeyboardButton(text="🏠 Home", callback_data="menu:home"),
    )
    return builder.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data="action:cancel"))
    return builder.as_markup()


def welcome_edit_kb(bot_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Edit Text", callback_data=f"welcome:edit:{bot_id}"),
        InlineKeyboardButton(text="👁 Preview", callback_data=f"welcome:preview:{bot_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Toggle On/Off", callback_data=f"welcome:toggle:{bot_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data=f"bot:view:{bot_id}"),
        InlineKeyboardButton(text="🏠 Home", callback_data="menu:home"),
    )
    return builder.as_markup()


def autoreply_edit_kb(bot_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Edit Text", callback_data=f"autoreply:edit:{bot_id}"),
        InlineKeyboardButton(text="👁 Preview", callback_data=f"autoreply:preview:{bot_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Toggle On/Off", callback_data=f"autoreply:toggle:{bot_id}"),
        InlineKeyboardButton(text="⏱ Cooldown", callback_data=f"autoreply:cooldown:{bot_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data=f"bot:view:{bot_id}"),
        InlineKeyboardButton(text="🏠 Home", callback_data="menu:home"),
    )
    return builder.as_markup()
