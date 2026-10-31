"""
Multi-Bot Telegram Support Manager
Production entry point for Render Free Web Service.
"""

import asyncio
import sys
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault
from fastapi import FastAPI
from loguru import logger

from app.config import settings
from database.connection import close_db, init_db
from database.repositories import ensure_owner
from handlers.master import router as master_router
from middlewares.auth import AdminCheckMiddleware
from middlewares.logging import LoggingMiddleware
from services.bot_manager import bot_manager
from webhooks.routes import router as webhook_router

# ───────────────────────────── LOGGING ─────────────────────────────

logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
)


# ───────────────────────────── LIFESPAN ─────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown logic."""
    logger.info("Starting Multi-Bot Support Manager…")

    # Database
    await init_db()
    await ensure_owner(settings.owner_id)

    # Bot manager (master + children)
    await bot_manager.initialize()

    # Attach master handlers & middlewares
    bot_manager.master_dp.include_router(master_router)
    bot_manager.master_dp.message.middleware(LoggingMiddleware())
    bot_manager.master_dp.callback_query.middleware(LoggingMiddleware())
    bot_manager.master_dp.message.middleware(AdminCheckMiddleware())
    bot_manager.master_dp.callback_query.middleware(AdminCheckMiddleware())

    # Master bot commands
    await bot_manager.master_bot.set_my_commands(
        [
            BotCommand(command="start", description="Open Main Menu"),
            BotCommand(command="help", description="Help and Instructions"),
            BotCommand(command="panel", description="Open Admin Panel"),
            BotCommand(command="addbot", description="Add a New Bot"),
            BotCommand(command="bots", description="View Connected Bots"),
            BotCommand(command="removebot", description="Remove a Bot"),
            BotCommand(command="setgroup", description="Configure Support Group"),
            BotCommand(command="admins", description="Manage Administrators"),
            BotCommand(command="stats", description="View Statistics"),
            BotCommand(command="settings", description="General Settings"),
            BotCommand(command="logs", description="View Activity Logs"),
            BotCommand(command="cancel", description="Cancel Current Operation"),
        ],
        scope=BotCommandScopeDefault(),
    )

    # Set webhooks
    await bot_manager.set_webhooks()

    logger.info("Application ready")
    yield

    # Shutdown
    logger.info("Shutting down…")
    await bot_manager.close()
    await close_db()
    logger.info("Shutdown complete")


# ───────────────────────────── APP ─────────────────────────────

app = FastAPI(
    title="Multi-Bot Telegram Support Manager",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

app.include_router(webhook_router)


# ───────────────────────────── LOCAL DEV ENTRY ─────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )
