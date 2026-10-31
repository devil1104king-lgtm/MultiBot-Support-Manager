"""FastAPI routes for Telegram webhooks and health checks."""

from fastapi import APIRouter, Header, HTTPException, Request, Response
from loguru import logger

from app.config import settings
from services.bot_manager import bot_manager

router = APIRouter()


@router.get("/")
async def root():
    return {
        "service": "Multi-Bot Telegram Support Manager",
        "status": "running",
        "bots": len(bot_manager.child_bots),
    }


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/webhook/master/{secret}")
async def master_webhook(
    secret: str,
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None),
):
    if secret != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")
    if (
        x_telegram_bot_api_secret_token
        and x_telegram_bot_api_secret_token != settings.webhook_secret
    ):
        raise HTTPException(status_code=403, detail="Invalid header secret")

    if not bot_manager.master_bot or not bot_manager.master_dp:
        raise HTTPException(status_code=503, detail="Master bot not ready")

    try:
        update = await request.json()
        from aiogram.types import Update

        telegram_update = Update(**update)
        await bot_manager.master_dp.feed_update(
            bot=bot_manager.master_bot,
            update=telegram_update,
        )
    except Exception as e:
        logger.exception(f"Master webhook error: {e}")
        # Still return 200 so Telegram does not retry endlessly on our bugs
    return Response(status_code=200)


@router.post("/webhook/bot/{bot_id}/{secret}")
async def child_webhook(
    bot_id: int,
    secret: str,
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None),
):
    if secret != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")
    if (
        x_telegram_bot_api_secret_token
        and x_telegram_bot_api_secret_token != settings.webhook_secret
    ):
        raise HTTPException(status_code=403, detail="Invalid header secret")

    child_bot = bot_manager.child_bots.get(bot_id)
    child_dp = bot_manager.child_dps.get(bot_id)
    if not child_bot or not child_dp:
        # Bot may have been disabled or not yet loaded
        logger.warning(f"Received update for unknown/inactive bot {bot_id}")
        return Response(status_code=200)

    try:
        update = await request.json()
        from aiogram.types import Update

        telegram_update = Update(**update)
        await child_dp.feed_update(bot=child_bot, update=telegram_update)
    except Exception as e:
        logger.exception(f"Child webhook error (bot {bot_id}): {e}")
    return Response(status_code=200)
