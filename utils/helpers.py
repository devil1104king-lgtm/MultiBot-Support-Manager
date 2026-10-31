"""General helper functions."""

from datetime import datetime, timezone
from typing import Optional

import pytz


def mask_token(token: str) -> str:
    """Mask a bot token for safe display (never show full token)."""
    if not token or len(token) < 15:
        return "***"
    return f"{token[:8]}...{token[-4:]}"


def format_datetime(dt: Optional[datetime], tz_name: str = "Asia/Kolkata") -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(pytz.timezone(tz_name))
    return local.strftime("%d %b %Y, %H:%M")


def escape_html(text: str) -> str:
    """Basic HTML escape for Telegram HTML parse mode."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def truncate(text: str, max_len: int = 200) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def status_emoji(active: bool) -> str:
    return "🟢" if active else "🔴"
