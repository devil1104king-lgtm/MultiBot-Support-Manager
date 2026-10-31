"""Support group forwarding and two-way reply logic."""

from datetime import datetime, timezone
from typing import Optional

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import Message
from loguru import logger

from database.models import BotDocument
from database.repositories import (
    get_bot_by_id,
    get_mapping_by_reply,
    increment_bot_stat,
    increment_daily_stat,
    log_activity,
    save_message_mapping,
    update_user_auto_reply,
    upsert_user,
)
from keyboards.support import support_message_kb
from utils.helpers import escape_html, format_datetime


async def forward_to_support(
    child_bot: Bot,
    message: Message,
    bot_doc: BotDocument,
) -> None:
    """
    Forward any incoming user message to the centralized support group
    and store the mapping for later replies.
    """
    if not bot_doc.support_group_id:
        # Fallback: try to find any configured group from other bots or skip
        logger.warning(f"Bot {bot_doc.bot_id} has no support_group_id configured")
        return

    group_id = bot_doc.support_group_id
    user = message.from_user
    if not user:
        return

    # Upsert user record
    await upsert_user(
        bot_id=bot_doc.bot_id,
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
    )

    # Build header
    user_display = escape_html(user.full_name or "Unknown")
    username_part = f" (@{user.username})" if user.username else ""
    time_str = format_datetime(datetime.now(timezone.utc))

    header = (
        "━━━━━━━━━━━━━━━━━━\n"
        "📩 <b>NEW SUPPORT MESSAGE</b>\n\n"
        f"🤖 Bot: @{bot_doc.username}\n"
        f"👤 User: {user_display}{username_part}\n"
        f"🆔 User ID: <code>{user.id}</code>\n\n"
        "💬 <b>MESSAGE:</b>\n"
    )

    footer = f"\n\n🕒 {time_str}\n━━━━━━━━━━━━━━━━━━"

    kb = support_message_kb(bot_doc.bot_id, user.id)

    # We need a bot that is a member of the support group.
    # Prefer the child bot itself; if it cannot post, we fall back to master later if needed.
    try:
        sent = await _copy_or_send(
            bot=child_bot,
            group_id=group_id,
            message=message,
            header=header,
            footer=footer,
            reply_markup=kb,
        )
        if sent:
            await save_message_mapping(
                group_message_id=sent.message_id,
                group_chat_id=group_id,
                bot_id=bot_doc.bot_id,
                user_chat_id=message.chat.id,
                user_id=user.id,
                original_message_id=message.message_id,
                content_type=message.content_type or "text",
            )
            await increment_bot_stat(bot_doc.bot_id, "total_messages")
            await increment_daily_stat("total_messages", bot_doc.bot_id)
            await log_activity(
                "message_received",
                actor_id=user.id,
                bot_id=bot_doc.bot_id,
                details={"chat_id": message.chat.id},
            )
    except TelegramForbiddenError:
        logger.error(
            f"Bot @{bot_doc.username} cannot post to support group {group_id}. "
            "Make sure the bot is added as admin."
        )
    except Exception as e:
        logger.exception(f"Failed to forward message from bot {bot_doc.bot_id}: {e}")


async def _copy_or_send(
    bot: Bot,
    group_id: int,
    message: Message,
    header: str,
    footer: str,
    reply_markup,
) -> Optional[Message]:
    """
    Prefer copying media with caption; fall back to text description.
    """
    caption = (message.caption or message.text or "").strip()
    full_caption = header + (escape_html(caption) if caption else "<i>(no text)</i>") + footer

    # Telegram caption limit is 1024
    if len(full_caption) > 1024:
        full_caption = full_caption[:1020] + "…"

    try:
        if message.content_type == ContentType.TEXT:
            return await bot.send_message(
                chat_id=group_id,
                text=full_caption,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        elif message.content_type == ContentType.PHOTO:
            return await bot.send_photo(
                chat_id=group_id,
                photo=message.photo[-1].file_id,
                caption=full_caption,
                reply_markup=reply_markup,
            )
        elif message.content_type == ContentType.VIDEO:
            return await bot.send_video(
                chat_id=group_id,
                video=message.video.file_id,
                caption=full_caption,
                reply_markup=reply_markup,
            )
        elif message.content_type == ContentType.DOCUMENT:
            return await bot.send_document(
                chat_id=group_id,
                document=message.document.file_id,
                caption=full_caption,
                reply_markup=reply_markup,
            )
        elif message.content_type == ContentType.AUDIO:
            return await bot.send_audio(
                chat_id=group_id,
                audio=message.audio.file_id,
                caption=full_caption,
                reply_markup=reply_markup,
            )
        elif message.content_type == ContentType.VOICE:
            # Voice has no caption → send header + voice + footer
            await bot.send_message(chat_id=group_id, text=header + footer, reply_markup=reply_markup)
            return await bot.send_voice(chat_id=group_id, voice=message.voice.file_id)
        elif message.content_type == ContentType.VIDEO_NOTE:
            await bot.send_message(chat_id=group_id, text=header + footer, reply_markup=reply_markup)
            return await bot.send_video_note(chat_id=group_id, video_note=message.video_note.file_id)
        elif message.content_type == ContentType.STICKER:
            await bot.send_message(chat_id=group_id, text=header + footer, reply_markup=reply_markup)
            return await bot.send_sticker(chat_id=group_id, sticker=message.sticker.file_id)
        elif message.content_type == ContentType.ANIMATION:
            return await bot.send_animation(
                chat_id=group_id,
                animation=message.animation.file_id,
                caption=full_caption,
                reply_markup=reply_markup,
            )
        elif message.content_type == ContentType.CONTACT:
            contact_text = (
                f"{header}"
                f"📇 Contact: {message.contact.first_name or ''} {message.contact.last_name or ''}\n"
                f"Phone: {message.contact.phone_number or '—'}"
                f"{footer}"
            )
            return await bot.send_message(chat_id=group_id, text=contact_text, reply_markup=reply_markup)
        elif message.content_type == ContentType.LOCATION:
            loc_text = f"{header}📍 Location shared{footer}"
            await bot.send_message(chat_id=group_id, text=loc_text, reply_markup=reply_markup)
            return await bot.send_location(
                chat_id=group_id,
                latitude=message.location.latitude,
                longitude=message.location.longitude,
            )
        else:
            # Generic fallback
            return await bot.send_message(
                chat_id=group_id,
                text=header + f"<i>[{message.content_type}]</i>" + footer,
                reply_markup=reply_markup,
            )
    except TelegramAPIError as e:
        logger.error(f"Telegram error while forwarding: {e}")
        # Last resort – text only
        return await bot.send_message(
            chat_id=group_id,
            text=header + f"<i>Media could not be forwarded ({message.content_type})</i>" + footer,
            reply_markup=reply_markup,
        )


async def handle_admin_reply(
    admin_bot: Bot,  # the bot that received the admin's message (usually master or any)
    message: Message,
    mapping: "MessageMappingDocument",
) -> bool:
    """
    Deliver an admin's reply to the original user through the correct child bot.
    Returns True on success.
    """
    from services.bot_manager import bot_manager

    child_bot = await bot_manager.get_child_bot(mapping.bot_id)
    if not child_bot:
        # Try to reload from DB
        bot_doc = await get_bot_by_id(mapping.bot_id)
        if not bot_doc or not bot_doc.is_active:
            logger.error(f"Cannot deliver reply – bot {mapping.bot_id} not active")
            return False
        child_bot = await bot_manager.add_bot(bot_doc.bot_id, bot_doc.token)

    try:
        if message.content_type == ContentType.TEXT:
            await child_bot.send_message(
                chat_id=mapping.user_chat_id,
                text=message.text,
            )
        elif message.content_type == ContentType.PHOTO:
            await child_bot.send_photo(
                chat_id=mapping.user_chat_id,
                photo=message.photo[-1].file_id,
                caption=message.caption,
            )
        elif message.content_type == ContentType.VIDEO:
            await child_bot.send_video(
                chat_id=mapping.user_chat_id,
                video=message.video.file_id,
                caption=message.caption,
            )
        elif message.content_type == ContentType.DOCUMENT:
            await child_bot.send_document(
                chat_id=mapping.user_chat_id,
                document=message.document.file_id,
                caption=message.caption,
            )
        elif message.content_type == ContentType.AUDIO:
            await child_bot.send_audio(
                chat_id=mapping.user_chat_id,
                audio=message.audio.file_id,
                caption=message.caption,
            )
        elif message.content_type == ContentType.VOICE:
            await child_bot.send_voice(
                chat_id=mapping.user_chat_id,
                voice=message.voice.file_id,
            )
        elif message.content_type == ContentType.VIDEO_NOTE:
            await child_bot.send_video_note(
                chat_id=mapping.user_chat_id,
                video_note=message.video_note.file_id,
            )
        elif message.content_type == ContentType.STICKER:
            await child_bot.send_sticker(
                chat_id=mapping.user_chat_id,
                sticker=message.sticker.file_id,
            )
        elif message.content_type == ContentType.ANIMATION:
            await child_bot.send_animation(
                chat_id=mapping.user_chat_id,
                animation=message.animation.file_id,
                caption=message.caption,
            )
        else:
            # Fallback text
            await child_bot.send_message(
                chat_id=mapping.user_chat_id,
                text=message.text or message.caption or "Support reply",
            )

        await increment_bot_stat(mapping.bot_id, "total_replies")
        await increment_daily_stat("total_replies", mapping.bot_id)
        await log_activity(
            "reply_sent",
            actor_id=message.from_user.id if message.from_user else None,
            bot_id=mapping.bot_id,
            details={"user_id": mapping.user_id},
        )
        return True
    except TelegramForbiddenError:
        logger.warning(f"User {mapping.user_id} has blocked bot {mapping.bot_id}")
        return False
    except Exception as e:
        logger.exception(f"Failed to deliver reply via bot {mapping.bot_id}: {e}")
        return False


async def maybe_send_auto_reply(
    child_bot: Bot,
    message: Message,
    bot_doc: BotDocument,
) -> None:
    """Send auto-reply if enabled and cooldown has passed."""
    if not bot_doc.auto_reply_enabled or not bot_doc.auto_reply_message:
        return

    user = message.from_user
    if not user:
        return

    from database.repositories import get_user

    user_doc = await get_user(bot_doc.bot_id, user.id)
    now = datetime.now(timezone.utc)

    if user_doc and user_doc.last_auto_reply_at:
        delta = (now - user_doc.last_auto_reply_at).total_seconds()
        if delta < bot_doc.auto_reply_cooldown:
            return

    try:
        await child_bot.send_message(
            chat_id=message.chat.id,
            text=bot_doc.auto_reply_message,
        )
        await update_user_auto_reply(bot_doc.bot_id, user.id)
    except Exception as e:
        logger.debug(f"Auto-reply failed: {e}")
