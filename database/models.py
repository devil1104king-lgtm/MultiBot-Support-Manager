"""Pydantic models and helpers for MongoDB documents."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BotDocument(BaseModel):
    """Connected bot configuration."""

    bot_id: int
    token: str  # stored securely; never logged in full
    token_hash: str
    username: str
    first_name: str
    is_active: bool = True
    welcome_enabled: bool = True
    welcome_message: str = (
        "👋 <b>Welcome!</b>\n\n"
        "Thank you for contacting support.\n"
        "Please describe your issue and our team will reply shortly."
    )
    welcome_buttons: List[Dict[str, str]] = Field(default_factory=list)
    auto_reply_enabled: bool = True
    auto_reply_message: str = (
        "✅ <b>Message received!</b>\n\n"
        "Our support team has been notified and will get back to you soon."
    )
    auto_reply_cooldown: int = 300  # seconds
    support_group_id: Optional[int] = None
    total_messages: int = 0
    total_users: int = 0
    total_replies: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_activity: Optional[datetime] = None

    class Config:
        extra = "ignore"


class AdminDocument(BaseModel):
    """Administrator record."""

    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_owner: bool = False
    permissions: List[str] = Field(default_factory=lambda: ["reply", "view"])
    added_by: Optional[int] = None
    created_at: datetime = Field(default_factory=utcnow)
    is_active: bool = True

    class Config:
        extra = "ignore"


class UserDocument(BaseModel):
    """End-user who interacted with a connected bot."""

    bot_id: int
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    last_auto_reply_at: Optional[datetime] = None
    is_blocked: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    class Config:
        extra = "ignore"


class MessageMappingDocument(BaseModel):
    """Maps a support-group message back to the original user & bot."""

    group_message_id: int
    group_chat_id: int
    bot_id: int
    user_chat_id: int
    user_id: int
    original_message_id: Optional[int] = None
    content_type: str = "text"
    created_at: datetime = Field(default_factory=utcnow)

    class Config:
        extra = "ignore"


class ActivityLogDocument(BaseModel):
    """System activity log entry."""

    action: str
    actor_id: Optional[int] = None
    bot_id: Optional[int] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)

    class Config:
        extra = "ignore"


class StatisticsDocument(BaseModel):
    """Daily aggregated statistics."""

    date: str  # YYYY-MM-DD
    total_messages: int = 0
    total_replies: int = 0
    new_users: int = 0
    active_bots: int = 0
    per_bot: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=utcnow)

    class Config:
        extra = "ignore"
