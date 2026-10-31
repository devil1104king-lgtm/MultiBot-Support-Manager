"""Central multi-bot manager – creates, starts and routes updates for all bots."""

from typing import Dict, Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault
from loguru import logger

from app.config import settings
from database.repositories import get_all_bots, get_bot_by_id, update_bot
from handlers.child_bot import create_child_router


class BotManager:
    """Manages the Master Bot and all connected child bots."""

    def __init__(self) -> None:
        self.master_bot: Optional[Bot] = None
        self.master_dp: Optional[Dispatcher] = None
        self.child_bots: Dict[int, Bot] = {}          # bot_id → Bot
        self.child_dps: Dict[int, Dispatcher] = {}    # bot_id → Dispatcher
        self._initialized = False

    async def initialize(self) -> None:
        """Create Master Bot and load all active child bots from DB."""
        if self._initialized:
            return

        # Master bot
        self.master_bot = Bot(
            token=settings.master_bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.master_dp = Dispatcher()

        # Load connected bots
        bots = await get_all_bots()
        for bot_doc in bots:
            if bot_doc.is_active:
                try:
                    await self._start_child_bot(bot_doc.bot_id, bot_doc.token)
                except Exception as e:
                    logger.error(f"Failed to start bot {bot_doc.bot_id}: {e}")
                    await update_bot(bot_doc.bot_id, is_active=False)

        self._initialized = True
        logger.info(
            f"BotManager ready – Master + {len(self.child_bots)} child bot(s)"
        )

    async def _start_child_bot(self, bot_id: int, token: str) -> Bot:
        """Create Bot + Dispatcher for a connected bot and register its router."""
        if bot_id in self.child_bots:
            return self.child_bots[bot_id]

        bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        # Validate token quickly
        me = await bot.get_me()
        if me.id != bot_id:
            await bot.session.close()
            raise ValueError(f"Token bot_id mismatch: expected {bot_id}, got {me.id}")

        dp = Dispatcher()
        router = create_child_router(bot_id)
        dp.include_router(router)

        self.child_bots[bot_id] = bot
        self.child_dps[bot_id] = dp

        # Set commands for the child bot
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Start Bot"),
                BotCommand(command="help", description="Help"),
                BotCommand(command="contact", description="Contact Support"),
            ],
            scope=BotCommandScopeDefault(),
        )
        logger.info(f"Child bot @{me.username} (ID {bot_id}) started")
        return bot

    async def add_bot(self, bot_id: int, token: str) -> Bot:
        """Register and start a newly added bot."""
        return await self._start_child_bot(bot_id, token)

    async def remove_bot(self, bot_id: int) -> None:
        """Stop and unload a child bot."""
        bot = self.child_bots.pop(bot_id, None)
        self.child_dps.pop(bot_id, None)
        if bot:
            try:
                await bot.delete_webhook(drop_pending_updates=False)
            except Exception:
                pass
            await bot.session.close()
            logger.info(f"Child bot {bot_id} removed from memory")

    async def get_child_bot(self, bot_id: int) -> Optional[Bot]:
        return self.child_bots.get(bot_id)

    async def set_webhooks(self) -> None:
        """Register webhooks for Master and all active child bots."""
        if not self.master_bot:
            return

        # Master
        master_url = settings.full_webhook_url(settings.master_webhook_path)
        await self.master_bot.set_webhook(
            url=master_url,
            secret_token=settings.webhook_secret,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "my_chat_member"],
        )
        logger.info(f"Master webhook set → {master_url}")

        # Children
        for bot_id, bot in list(self.child_bots.items()):
            try:
                path = settings.bot_webhook_path(bot_id)
                url = settings.full_webhook_url(path)
                await bot.set_webhook(
                    url=url,
                    secret_token=settings.webhook_secret,
                    drop_pending_updates=False,
                    allowed_updates=["message", "callback_query", "my_chat_member"],
                )
                logger.info(f"Webhook set for bot {bot_id}")
            except Exception as e:
                logger.error(f"Failed to set webhook for bot {bot_id}: {e}")

    async def delete_all_webhooks(self) -> None:
        if self.master_bot:
            try:
                await self.master_bot.delete_webhook()
            except Exception:
                pass
        for bot in self.child_bots.values():
            try:
                await bot.delete_webhook()
            except Exception:
                pass

    async def close(self) -> None:
        """Graceful shutdown."""
        await self.delete_all_webhooks()
        if self.master_bot:
            await self.master_bot.session.close()
        for bot in self.child_bots.values():
            await bot.session.close()
        self.child_bots.clear()
        self.child_dps.clear()
        self._initialized = False
        logger.info("BotManager closed")


# Global singleton
bot_manager = BotManager()
