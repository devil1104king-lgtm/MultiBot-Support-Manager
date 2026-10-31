"""Master Bot handlers – full admin panel."""

from typing import Any, Dict

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from loguru import logger

from app.config import settings
from database.repositories import (
    add_admin,
    create_bot,
    delete_bot,
    ensure_owner,
    get_admin,
    get_all_bots,
    get_bot_by_id,
    get_bot_by_token_hash,
    get_global_stats,
    get_recent_logs,
    is_owner,
    list_admins,
    log_activity,
    remove_admin,
    update_bot,
)
from keyboards.master import (
    admin_detail_kb,
    admins_menu_kb,
    autoreply_edit_kb,
    back_home_kb,
    bot_detail_kb,
    bots_menu_kb,
    cancel_kb,
    confirm_kb,
    main_menu_kb,
    support_settings_kb,
    welcome_edit_kb,
)
from services.bot_manager import bot_manager
from utils.helpers import escape_html, format_datetime, mask_token, status_emoji

router = Router(name="master")


# ───────────────────────────── FSM STATES ─────────────────────────────


class AddBotStates(StatesGroup):
    waiting_token = State()
    confirm = State()


class EditWelcomeStates(StatesGroup):
    waiting_text = State()


class EditAutoReplyStates(StatesGroup):
    waiting_text = State()
    waiting_cooldown = State()


class AddAdminStates(StatesGroup):
    waiting_id = State()


class SetGroupStates(StatesGroup):
    waiting_forward = State()


# ───────────────────────────── HELPERS ─────────────────────────────


async def _require_owner(user_id: int, event) -> bool:
    if not await is_owner(user_id):
        if isinstance(event, CallbackQuery):
            await event.answer("⛔ Owner only", show_alert=True)
        else:
            await event.answer("⛔ This action is restricted to the Owner.")
        return False
    return True


def _bot_info_text(bot) -> str:
    return (
        f"🤖 <b>Bot Information</b>\n\n"
        f"• Username: @{bot.username}\n"
        f"• Name: {escape_html(bot.first_name)}\n"
        f"• ID: <code>{bot.bot_id}</code>\n"
        f"• Status: {status_emoji(bot.is_active)} {'Active' if bot.is_active else 'Disabled'}\n"
        f"• Messages: {bot.total_messages}\n"
        f"• Users: {bot.total_users}\n"
        f"• Replies: {bot.total_replies}\n"
        f"• Welcome: {'✅ On' if bot.welcome_enabled else '❌ Off'}\n"
        f"• Auto-reply: {'✅ On' if bot.auto_reply_enabled else '❌ Off'}\n"
        f"• Added: {format_datetime(bot.created_at)}"
    )


# ───────────────────────────── COMMANDS ─────────────────────────────


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await ensure_owner(settings.owner_id)
    if message.from_user.id != settings.owner_id and not await get_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return
    await message.answer(
        "🎛️ <b>Multi-Bot Support Manager</b>\n\n"
        "Welcome to the premium control panel.\n"
        "Select an option below:",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("panel", "menu"))
async def cmd_panel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "🎛️ <b>Admin Panel</b>",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = (
        "📖 <b>Help & Commands</b>\n\n"
        "<b>Main Commands</b>\n"
        "/start – Open main menu\n"
        "/panel – Admin panel\n"
        "/help – This message\n"
        "/addbot – Add a new bot\n"
        "/bots – List connected bots\n"
        "/removebot – Remove a bot\n"
        "/setgroup – Set support group\n"
        "/admins – Manage administrators\n"
        "/stats – View statistics\n"
        "/settings – General settings\n"
        "/logs – Activity logs\n"
        "/cancel – Cancel current operation\n\n"
        "<b>Quick Tips</b>\n"
        "• Add bots with their tokens\n"
        "• Forward any message from the support group to set it\n"
        "• Reply to forwarded messages to answer users"
    )
    await message.answer(text, reply_markup=back_home_kb())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("✅ Operation cancelled.", reply_markup=main_menu_kb())


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    stats = await get_global_stats()
    text = (
        "📊 <b>Statistics Dashboard</b>\n\n"
        f"🤖 Total Bots: <b>{stats['total_bots']}</b>\n"
        f"🟢 Active: <b>{stats['active_bots']}</b>\n"
        f"🔴 Disabled: <b>{stats['disabled_bots']}</b>\n\n"
        f"👥 Total Users: <b>{stats['total_users']}</b>\n"
        f"📩 Total Messages: <b>{stats['total_messages']}</b>\n"
        f"↩️ Total Replies: <b>{stats['total_replies']}</b>\n"
        f"📅 Today’s Messages: <b>{stats['today_messages']}</b>\n"
    )
    await message.answer(text, reply_markup=back_home_kb())


@router.message(Command("logs"))
async def cmd_logs(message: Message) -> None:
    logs = await get_recent_logs(15)
    if not logs:
        await message.answer("📋 No activity logs yet.", reply_markup=back_home_kb())
        return
    lines = ["📋 <b>Recent Activity</b>\n"]
    for log in logs:
        time = format_datetime(log.created_at)
        lines.append(f"• <code>{time}</code> – {escape_html(log.action)}")
    await message.answer("\n".join(lines), reply_markup=back_home_kb())


@router.message(Command("bots"))
async def cmd_bots(message: Message) -> None:
    bots = await get_all_bots()
    if not bots:
        await message.answer(
            "🤖 No bots connected yet.\nUse /addbot or the menu to add one.",
            reply_markup=bots_menu_kb([]),
        )
        return
    await message.answer(
        f"🤖 <b>Connected Bots</b> ({len(bots)})\nSelect a bot to manage:",
        reply_markup=bots_menu_kb(bots),
    )


@router.message(Command("admins"))
async def cmd_admins(message: Message) -> None:
    admins = await list_admins()
    await message.answer(
        f"👥 <b>Administrators</b> ({len(admins)})",
        reply_markup=admins_menu_kb(admins),
    )


@router.message(Command("addbot"))
async def cmd_addbot(message: Message, state: FSMContext) -> None:
    if not await _require_owner(message.from_user.id, message):
        return
    await state.set_state(AddBotStates.waiting_token)
    await message.answer(
        "🔑 <b>Add New Bot</b>\n\n"
        "Send the Bot Token you received from @BotFather.\n\n"
        "<i>The token will never be shown in full after validation.</i>",
        reply_markup=cancel_kb(),
    )


@router.message(Command("setgroup"))
async def cmd_setgroup(message: Message, state: FSMContext) -> None:
    if not await _require_owner(message.from_user.id, message):
        return
    await state.set_state(SetGroupStates.waiting_forward)
    await message.answer(
        "📍 <b>Set Support Group</b>\n\n"
        "1. Add the <b>Master Bot</b> (and preferably all child bots) to your support group as admins.\n"
        "2. Forward any message from that group here, or send the group ID.\n\n"
        "Waiting for a forwarded message or group ID…",
        reply_markup=cancel_kb(),
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    # Global support group is stored on bots; show current
    bots = await get_all_bots()
    group_ids = {b.support_group_id for b in bots if b.support_group_id}
    group_id = next(iter(group_ids), None)
    await message.answer(
        "⚙️ <b>General Settings</b>\n\n"
        f"Support Group ID: <code>{group_id or 'Not set'}</code>\n"
        f"Owner ID: <code>{settings.owner_id}</code>\n"
        f"Connected Bots: {len(bots)}",
        reply_markup=support_settings_kb(group_id),
    )


# ───────────────────────────── CALLBACKS – MAIN MENU ─────────────────────────────


@router.callback_query(F.data == "menu:home")
async def cb_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "🎛️ <b>Multi-Bot Support Manager</b>\n\nSelect an option:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:bots")
async def cb_bots(callback: CallbackQuery) -> None:
    bots = await get_all_bots()
    await callback.message.edit_text(
        f"🤖 <b>Connected Bots</b> ({len(bots)})\nSelect a bot:",
        reply_markup=bots_menu_kb(bots),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bots:page:"))
async def cb_bots_page(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":")[-1])
    bots = await get_all_bots()
    await callback.message.edit_text(
        f"🤖 <b>Connected Bots</b> ({len(bots)})",
        reply_markup=bots_menu_kb(bots, page=page),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:support")
async def cb_support(callback: CallbackQuery) -> None:
    bots = await get_all_bots()
    group_ids = {b.support_group_id for b in bots if b.support_group_id}
    group_id = next(iter(group_ids), None)
    await callback.message.edit_text(
        "💬 <b>Support Settings</b>\n\n"
        "All connected bots share one central support group.",
        reply_markup=support_settings_kb(group_id),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:admins")
async def cb_admins(callback: CallbackQuery) -> None:
    admins = await list_admins()
    await callback.message.edit_text(
        f"👥 <b>Administrators</b> ({len(admins)})",
        reply_markup=admins_menu_kb(admins),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:stats")
async def cb_stats(callback: CallbackQuery) -> None:
    stats = await get_global_stats()
    text = (
        "📊 <b>Statistics Dashboard</b>\n\n"
        f"🤖 Total Bots: <b>{stats['total_bots']}</b>\n"
        f"🟢 Active: <b>{stats['active_bots']}</b>\n"
        f"🔴 Disabled: <b>{stats['disabled_bots']}</b>\n\n"
        f"👥 Total Users: <b>{stats['total_users']}</b>\n"
        f"📩 Total Messages: <b>{stats['total_messages']}</b>\n"
        f"↩️ Total Replies: <b>{stats['total_replies']}</b>\n"
        f"📅 Today’s Messages: <b>{stats['today_messages']}</b>\n"
    )
    await callback.message.edit_text(text, reply_markup=back_home_kb())
    await callback.answer()


@router.callback_query(F.data == "menu:logs")
async def cb_logs(callback: CallbackQuery) -> None:
    logs = await get_recent_logs(12)
    if not logs:
        text = "📋 No activity logs yet."
    else:
        lines = ["📋 <b>Recent Activity</b>\n"]
        for log in logs:
            time = format_datetime(log.created_at)
            lines.append(f"• <code>{time}</code> – {escape_html(log.action)}")
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=back_home_kb())
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def cb_help(callback: CallbackQuery) -> None:
    text = (
        "📖 <b>Help & Commands</b>\n\n"
        "/start /panel – Main menu\n"
        "/addbot – Add bot\n"
        "/bots – List bots\n"
        "/setgroup – Configure support group\n"
        "/admins – Manage admins\n"
        "/stats – Statistics\n"
        "/logs – Activity logs\n"
        "/cancel – Cancel operation\n\n"
        "Reply to any forwarded support message in the group to answer the user."
    )
    await callback.message.edit_text(text, reply_markup=back_home_kb())
    await callback.answer()


@router.callback_query(F.data == "menu:settings")
async def cb_settings(callback: CallbackQuery) -> None:
    await cb_support(callback)


@router.callback_query(F.data == "action:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "✅ Cancelled.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


# ───────────────────────────── ADD BOT FLOW ─────────────────────────────


@router.callback_query(F.data == "bot:add")
async def cb_bot_add(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _require_owner(callback.from_user.id, callback):
        return
    await state.set_state(AddBotStates.waiting_token)
    await callback.message.edit_text(
        "🔑 <b>Add New Bot</b>\n\n"
        "Send the Bot Token from @BotFather.\n"
        "It will be validated automatically.",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(AddBotStates.waiting_token, F.text)
async def process_bot_token(message: Message, state: FSMContext) -> None:
    token = message.text.strip()
    # Basic format check
    if ":" not in token or len(token) < 30:
        await message.answer(
            "❌ Invalid token format. Please send a valid BotFather token.",
            reply_markup=cancel_kb(),
        )
        return

    # Check duplicate
    existing = await get_bot_by_token_hash(token)
    if existing:
        await message.answer(
            f"⚠️ This bot (@{existing.username}) is already registered.",
            reply_markup=main_menu_kb(),
        )
        await state.clear()
        return

    # Validate with Telegram
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    test_bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        me = await test_bot.get_me()
    except Exception as e:
        await test_bot.session.close()
        await message.answer(
            f"❌ Token validation failed.\n<code>{escape_html(str(e)[:120])}</code>",
            reply_markup=cancel_kb(),
        )
        return
    finally:
        await test_bot.session.close()

    await state.update_data(
        token=token,
        bot_id=me.id,
        username=me.username or "",
        first_name=me.first_name or "",
    )
    await state.set_state(AddBotStates.confirm)

    await message.answer(
        "✅ <b>Token Validated</b>\n\n"
        f"🤖 Name: {escape_html(me.first_name or '')}\n"
        f"🔗 Username: @{me.username}\n"
        f"🆔 ID: <code>{me.id}</code>\n\n"
        "Confirm adding this bot?",
        reply_markup=confirm_kb("add_bot", "bot:confirm_add", "menu:bots"),
    )


@router.callback_query(F.data == "bot:confirm_add", AddBotStates.confirm)
async def cb_confirm_add_bot(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()

    token = data["token"]
    bot_id = data["bot_id"]
    username = data["username"]
    first_name = data["first_name"]

    # Inherit support group from any existing bot
    bots = await get_all_bots()
    support_group_id = None
    for b in bots:
        if b.support_group_id:
            support_group_id = b.support_group_id
            break

    try:
        bot_doc = await create_bot(token, bot_id, username, first_name)
        if support_group_id:
            await update_bot(bot_id, support_group_id=support_group_id)

        # Start the bot in memory and set webhook
        await bot_manager.add_bot(bot_id, token)
        path = settings.bot_webhook_path(bot_id)
        url = settings.full_webhook_url(path)
        child = await bot_manager.get_child_bot(bot_id)
        if child:
            await child.set_webhook(
                url=url,
                secret_token=settings.webhook_secret,
                drop_pending_updates=False,
            )

        await log_activity("bot_added", actor_id=callback.from_user.id, bot_id=bot_id)
        await callback.message.edit_text(
            f"✅ <b>Bot Added Successfully</b>\n\n"
            f"@{username} is now connected and receiving updates.",
            reply_markup=bot_detail_kb(bot_doc),
        )
    except Exception as e:
        logger.exception(e)
        await callback.message.edit_text(
            f"❌ Failed to register bot: {escape_html(str(e)[:150])}",
            reply_markup=main_menu_kb(),
        )
    await callback.answer()


# ───────────────────────────── BOT DETAIL & ACTIONS ─────────────────────────────


@router.callback_query(F.data.startswith("bot:view:"))
async def cb_bot_view(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split(":")[-1])
    bot = await get_bot_by_id(bot_id)
    if not bot:
        await callback.answer("Bot not found", show_alert=True)
        return
    await callback.message.edit_text(
        _bot_info_text(bot),
        reply_markup=bot_detail_kb(bot),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bot:toggle:"))
async def cb_bot_toggle(callback: CallbackQuery) -> None:
    if not await _require_owner(callback.from_user.id, callback):
        return
    bot_id = int(callback.data.split(":")[-1])
    bot = await get_bot_by_id(bot_id)
    if not bot:
        await callback.answer("Not found", show_alert=True)
        return
    new_state = not bot.is_active
    await update_bot(bot_id, is_active=new_state)
    if new_state:
        await bot_manager.add_bot(bot_id, bot.token)
        path = settings.bot_webhook_path(bot_id)
        url = settings.full_webhook_url(path)
        child = await bot_manager.get_child_bot(bot_id)
        if child:
            await child.set_webhook(url=url, secret_token=settings.webhook_secret)
    else:
        await bot_manager.remove_bot(bot_id)
    await log_activity(
        "bot_enabled" if new_state else "bot_disabled",
        actor_id=callback.from_user.id,
        bot_id=bot_id,
    )
    bot = await get_bot_by_id(bot_id)
    await callback.message.edit_text(
        _bot_info_text(bot),
        reply_markup=bot_detail_kb(bot),
    )
    await callback.answer("Updated")


@router.callback_query(F.data.startswith("bot:remove:"))
async def cb_bot_remove(callback: CallbackQuery) -> None:
    if not await _require_owner(callback.from_user.id, callback):
        return
    bot_id = int(callback.data.split(":")[-1])
    bot = await get_bot_by_id(bot_id)
    if not bot:
        await callback.answer("Not found", show_alert=True)
        return
    await callback.message.edit_text(
        f"🗑 <b>Remove Bot?</b>\n\n"
        f"@{bot.username} will be permanently removed.\n"
        f"This cannot be undone.",
        reply_markup=confirm_kb("remove", f"bot:confirm_remove:{bot_id}", f"bot:view:{bot_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bot:confirm_remove:"))
async def cb_confirm_remove(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split(":")[-1])
    bot = await get_bot_by_id(bot_id)
    await bot_manager.remove_bot(bot_id)
    await delete_bot(bot_id)
    await log_activity("bot_removed", actor_id=callback.from_user.id, bot_id=bot_id)
    name = bot.username if bot else str(bot_id)
    await callback.message.edit_text(
        f"✅ Bot @{name} has been removed.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bot:stats:"))
async def cb_bot_stats(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split(":")[-1])
    bot = await get_bot_by_id(bot_id)
    if not bot:
        await callback.answer("Not found", show_alert=True)
        return
    text = (
        f"📊 <b>Stats for @{bot.username}</b>\n\n"
        f"Messages: {bot.total_messages}\n"
        f"Users: {bot.total_users}\n"
        f"Replies: {bot.total_replies}\n"
        f"Last activity: {format_datetime(bot.last_activity)}"
    )
    await callback.message.edit_text(text, reply_markup=back_home_kb(f"bot:view:{bot_id}"))
    await callback.answer()


# ───────────────────────────── WELCOME MESSAGE ─────────────────────────────


@router.callback_query(F.data.startswith("bot:welcome:"))
async def cb_welcome_menu(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split(":")[-1])
    bot = await get_bot_by_id(bot_id)
    if not bot:
        await callback.answer("Not found", show_alert=True)
        return
    status = "✅ Enabled" if bot.welcome_enabled else "❌ Disabled"
    text = (
        f"✏️ <b>Welcome Message</b> – @{bot.username}\n\n"
        f"Status: {status}\n\n"
        f"<b>Current text:</b>\n{bot.welcome_message}"
    )
    await callback.message.edit_text(text, reply_markup=welcome_edit_kb(bot_id))
    await callback.answer()


@router.callback_query(F.data.startswith("welcome:toggle:"))
async def cb_welcome_toggle(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split(":")[-1])
    bot = await get_bot_by_id(bot_id)
    if not bot:
        return
    await update_bot(bot_id, welcome_enabled=not bot.welcome_enabled)
    await log_activity("welcome_updated", actor_id=callback.from_user.id, bot_id=bot_id)
    await cb_welcome_menu(callback)


@router.callback_query(F.data.startswith("welcome:preview:"))
async def cb_welcome_preview(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split(":")[-1])
    bot = await get_bot_by_id(bot_id)
    if not bot:
        return
    await callback.message.answer(
        f"👁 <b>Preview</b>\n\n{bot.welcome_message}",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("welcome:edit:"))
async def cb_welcome_edit(callback: CallbackQuery, state: FSMContext) -> None:
    bot_id = int(callback.data.split(":")[-1])
    await state.set_state(EditWelcomeStates.waiting_text)
    await state.update_data(bot_id=bot_id)
    await callback.message.edit_text(
        "✏️ Send the new welcome message.\n"
        "HTML formatting is supported.\n\n"
        "Send /cancel to abort.",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(EditWelcomeStates.waiting_text, F.text)
async def process_welcome_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    bot_id = data["bot_id"]
    await update_bot(bot_id, welcome_message=message.text)
    await log_activity("welcome_updated", actor_id=message.from_user.id, bot_id=bot_id)
    await state.clear()
    bot = await get_bot_by_id(bot_id)
    await message.answer(
        "✅ Welcome message updated.",
        reply_markup=welcome_edit_kb(bot_id),
    )


# ───────────────────────────── AUTO REPLY ─────────────────────────────


@router.callback_query(F.data.startswith("bot:autoreply:"))
async def cb_autoreply_menu(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split(":")[-1])
    bot = await get_bot_by_id(bot_id)
    if not bot:
        return
    status = "✅ Enabled" if bot.auto_reply_enabled else "❌ Disabled"
    text = (
        f"💬 <b>Auto Reply</b> – @{bot.username}\n\n"
        f"Status: {status}\n"
        f"Cooldown: {bot.auto_reply_cooldown}s\n\n"
        f"<b>Current text:</b>\n{bot.auto_reply_message}"
    )
    await callback.message.edit_text(text, reply_markup=autoreply_edit_kb(bot_id))
    await callback.answer()


@router.callback_query(F.data.startswith("autoreply:toggle:"))
async def cb_autoreply_toggle(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split(":")[-1])
    bot = await get_bot_by_id(bot_id)
    if not bot:
        return
    await update_bot(bot_id, auto_reply_enabled=not bot.auto_reply_enabled)
    await log_activity("auto_reply_updated", actor_id=callback.from_user.id, bot_id=bot_id)
    await cb_autoreply_menu(callback)


@router.callback_query(F.data.startswith("autoreply:preview:"))
async def cb_autoreply_preview(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split(":")[-1])
    bot = await get_bot_by_id(bot_id)
    if not bot:
        return
    await callback.message.answer(f"👁 <b>Preview</b>\n\n{bot.auto_reply_message}")
    await callback.answer()


@router.callback_query(F.data.startswith("autoreply:edit:"))
async def cb_autoreply_edit(callback: CallbackQuery, state: FSMContext) -> None:
    bot_id = int(callback.data.split(":")[-1])
    await state.set_state(EditAutoReplyStates.waiting_text)
    await state.update_data(bot_id=bot_id)
    await callback.message.edit_text(
        "✏️ Send the new auto-reply message (HTML supported).\n/cancel to abort.",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(EditAutoReplyStates.waiting_text, F.text)
async def process_autoreply_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    bot_id = data["bot_id"]
    await update_bot(bot_id, auto_reply_message=message.text)
    await log_activity("auto_reply_updated", actor_id=message.from_user.id, bot_id=bot_id)
    await state.clear()
    await message.answer("✅ Auto-reply updated.", reply_markup=autoreply_edit_kb(bot_id))


@router.callback_query(F.data.startswith("autoreply:cooldown:"))
async def cb_autoreply_cooldown(callback: CallbackQuery, state: FSMContext) -> None:
    bot_id = int(callback.data.split(":")[-1])
    await state.set_state(EditAutoReplyStates.waiting_cooldown)
    await state.update_data(bot_id=bot_id)
    await callback.message.edit_text(
        "⏱ Send the cooldown in seconds (e.g. 300 for 5 minutes).\n"
        "Minimum 30, maximum 86400.",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(EditAutoReplyStates.waiting_cooldown, F.text)
async def process_cooldown(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    bot_id = data["bot_id"]
    try:
        seconds = int(message.text.strip())
        if seconds < 30 or seconds > 86400:
            raise ValueError
    except ValueError:
        await message.answer("❌ Please send a number between 30 and 86400.")
        return
    await update_bot(bot_id, auto_reply_cooldown=seconds)
    await state.clear()
    await message.answer(
        f"✅ Cooldown set to {seconds} seconds.",
        reply_markup=autoreply_edit_kb(bot_id),
    )


# ───────────────────────────── SUPPORT GROUP ─────────────────────────────


@router.callback_query(F.data == "support:set")
async def cb_support_set(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _require_owner(callback.from_user.id, callback):
        return
    await state.set_state(SetGroupStates.waiting_forward)
    await callback.message.edit_text(
        "📍 <b>Set Support Group</b>\n\n"
        "Forward any message from the target group, or send the numeric group ID.\n"
        "Make sure the Master Bot (and ideally all child bots) are admins in that group.",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(SetGroupStates.waiting_forward)
async def process_set_group(message: Message, state: FSMContext) -> None:
    group_id = None
    if message.forward_from_chat and message.forward_from_chat.type in ("group", "supergroup"):
        group_id = message.forward_from_chat.id
    elif message.text and message.text.lstrip("-").isdigit():
        group_id = int(message.text.strip())
    else:
        await message.answer(
            "❌ Please forward a message from the group or send a valid group ID.",
            reply_markup=cancel_kb(),
        )
        return

    # Apply to all bots
    bots = await get_all_bots()
    for bot in bots:
        await update_bot(bot.bot_id, support_group_id=group_id)

    await log_activity(
        "support_group_set",
        actor_id=message.from_user.id,
        details={"group_id": group_id},
    )
    await state.clear()
    await message.answer(
        f"✅ Support group set to <code>{group_id}</code>\n"
        f"Applied to {len(bots)} bot(s).",
        reply_markup=support_settings_kb(group_id),
    )


@router.callback_query(F.data == "support:info")
async def cb_support_info(callback: CallbackQuery) -> None:
    bots = await get_all_bots()
    group_ids = {b.support_group_id for b in bots if b.support_group_id}
    group_id = next(iter(group_ids), None)
    await callback.answer(
        f"Current group: {group_id or 'Not set'}",
        show_alert=True,
    )


# ───────────────────────────── ADMINS ─────────────────────────────


@router.callback_query(F.data.startswith("admins:page:"))
async def cb_admins_page(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":")[-1])
    admins = await list_admins()
    await callback.message.edit_text(
        f"👥 <b>Administrators</b> ({len(admins)})",
        reply_markup=admins_menu_kb(admins, page=page),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:view:"))
async def cb_admin_view(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split(":")[-1])
    admin = await get_admin(user_id)
    if not admin:
        await callback.answer("Not found", show_alert=True)
        return
    role = "Owner" if admin.is_owner else "Admin"
    name = admin.first_name or admin.username or str(admin.user_id)
    text = (
        f"👤 <b>{escape_html(name)}</b>\n\n"
        f"Role: {role}\n"
        f"ID: <code>{admin.user_id}</code>\n"
        f"Username: @{admin.username or '—'}\n"
        f"Permissions: {', '.join(admin.permissions)}\n"
        f"Added: {format_datetime(admin.created_at)}"
    )
    viewer_is_owner = await is_owner(callback.from_user.id)
    await callback.message.edit_text(
        text,
        reply_markup=admin_detail_kb(admin, viewer_is_owner),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:add")
async def cb_admin_add(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _require_owner(callback.from_user.id, callback):
        return
    await state.set_state(AddAdminStates.waiting_id)
    await callback.message.edit_text(
        "➕ <b>Add Administrator</b>\n\n"
        "Send the Telegram User ID of the new admin.\n"
        "(The user can get it from @userinfobot)",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(AddAdminStates.waiting_id, F.text)
async def process_add_admin(message: Message, state: FSMContext) -> None:
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Please send a valid numeric User ID.")
        return

    if user_id == settings.owner_id:
        await message.answer("ℹ️ This user is already the Owner.")
        await state.clear()
        return

    existing = await get_admin(user_id)
    if existing and existing.is_active:
        await message.answer("⚠️ This user is already an admin.")
        await state.clear()
        return

    await add_admin(
        user_id=user_id,
        username=None,
        first_name=None,
        added_by=message.from_user.id,
    )
    await log_activity("admin_added", actor_id=message.from_user.id, details={"user_id": user_id})
    await state.clear()
    await message.answer(
        f"✅ User <code>{user_id}</code> has been added as Admin.",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data.startswith("admin:remove:"))
async def cb_admin_remove(callback: CallbackQuery) -> None:
    if not await _require_owner(callback.from_user.id, callback):
        return
    user_id = int(callback.data.split(":")[-1])
    ok = await remove_admin(user_id)
    if ok:
        await log_activity("admin_removed", actor_id=callback.from_user.id, details={"user_id": user_id})
        await callback.message.edit_text(
            f"✅ Admin <code>{user_id}</code> removed.",
            reply_markup=main_menu_kb(),
        )
    else:
        await callback.answer("Cannot remove owner or not found", show_alert=True)
    await callback.answer()


# ───────────────────────────── SUPPORT GROUP REPLY HANDLING ─────────────────────────────


@router.message(F.chat.type.in_({"group", "supergroup"}), F.reply_to_message)
async def handle_group_reply(message: Message) -> None:
    """When an admin replies to a forwarded support message in the group."""
    from database.repositories import get_mapping_by_reply
    from services.support_service import handle_admin_reply

    reply = message.reply_to_message
    if not reply:
        return

    mapping = await get_mapping_by_reply(message.chat.id, reply.message_id)
    if not mapping:
        # Not a tracked support message – ignore
        return

    # Only admins may reply
    admin = await get_admin(message.from_user.id)
    if not admin:
        return

    success = await handle_admin_reply(message.bot, message, mapping)
    if success:
        try:
            await message.reply("✅ Reply delivered to user.")
        except Exception:
            pass
    else:
        try:
            await message.reply("⚠️ Failed to deliver reply. User may have blocked the bot.")
        except Exception:
            pass


# Inline reply button
@router.callback_query(F.data.startswith("sreply:"))
async def cb_support_reply_hint(callback: CallbackQuery) -> None:
    await callback.answer(
        "↩️ Reply to this message (native Telegram reply) to answer the user.",
        show_alert=True,
    )


@router.callback_query(F.data.startswith("suser:"))
async def cb_support_user(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    bot_id, user_id = int(parts[1]), int(parts[2])
    from database.repositories import get_user

    user = await get_user(bot_id, user_id)
    if not user:
        await callback.answer("User not found in database", show_alert=True)
        return
    name = user.first_name or "—"
    text = (
        f"👤 {name}\n"
        f"ID: {user.user_id}\n"
        f"Username: @{user.username or '—'}\n"
        f"Messages: {user.message_count}"
    )
    await callback.answer(text, show_alert=True)


@router.callback_query(F.data.startswith("sbot:"))
async def cb_support_bot(callback: CallbackQuery) -> None:
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot_by_id(bot_id)
    if not bot:
        await callback.answer("Bot not found", show_alert=True)
        return
    await callback.answer(
        f"@{bot.username} | ID {bot.bot_id} | {'Active' if bot.is_active else 'Disabled'}",
        show_alert=True,
    )
