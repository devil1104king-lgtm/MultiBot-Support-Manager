"""Data access layer for all collections."""

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, List, Optional

from loguru import logger

from database.connection import get_db
from database.models import (
    ActivityLogDocument,
    AdminDocument,
    BotDocument,
    MessageMappingDocument,
    UserDocument,
    utcnow,
)


def _token_hash(token: str) -> str:
    return sha256(token.encode()).hexdigest()


# ───────────────────────────── BOTS ─────────────────────────────


async def create_bot(token: str, bot_id: int, username: str, first_name: str) -> BotDocument:
    db = get_db()
    doc = BotDocument(
        bot_id=bot_id,
        token=token,
        token_hash=_token_hash(token),
        username=username,
        first_name=first_name,
    )
    data = doc.model_dump()
    await db.bots.insert_one(data)
    logger.info(f"Bot @{username} (ID {bot_id}) registered")
    return doc


async def get_bot_by_id(bot_id: int) -> Optional[BotDocument]:
    db = get_db()
    raw = await db.bots.find_one({"bot_id": bot_id})
    return BotDocument(**raw) if raw else None


async def get_bot_by_token_hash(token: str) -> Optional[BotDocument]:
    db = get_db()
    raw = await db.bots.find_one({"token_hash": _token_hash(token)})
    return BotDocument(**raw) if raw else None


async def get_all_bots(active_only: bool = False) -> List[BotDocument]:
    db = get_db()
    query = {"is_active": True} if active_only else {}
    cursor = db.bots.find(query).sort("created_at", 1)
    return [BotDocument(**doc) async for doc in cursor]


async def update_bot(bot_id: int, **fields) -> bool:
    db = get_db()
    fields["updated_at"] = utcnow()
    result = await db.bots.update_one({"bot_id": bot_id}, {"$set": fields})
    return result.modified_count > 0


async def delete_bot(bot_id: int) -> bool:
    db = get_db()
    result = await db.bots.delete_one({"bot_id": bot_id})
    return result.deleted_count > 0


async def increment_bot_stat(bot_id: int, field: str, amount: int = 1) -> None:
    db = get_db()
    await db.bots.update_one(
        {"bot_id": bot_id},
        {"$inc": {field: amount}, "$set": {"last_activity": utcnow(), "updated_at": utcnow()}},
    )


# ───────────────────────────── ADMINS ─────────────────────────────


async def ensure_owner(owner_id: int) -> AdminDocument:
    """Guarantee the OWNER_ID exists as owner admin."""
    db = get_db()
    existing = await db.admins.find_one({"user_id": owner_id})
    if existing:
        if not existing.get("is_owner"):
            await db.admins.update_one(
                {"user_id": owner_id},
                {"$set": {"is_owner": True, "is_active": True}},
            )
        return AdminDocument(**existing)

    doc = AdminDocument(
        user_id=owner_id,
        is_owner=True,
        permissions=["all"],
        is_active=True,
    )
    await db.admins.insert_one(doc.model_dump())
    logger.info(f"Owner {owner_id} registered")
    return doc


async def get_admin(user_id: int) -> Optional[AdminDocument]:
    db = get_db()
    raw = await db.admins.find_one({"user_id": user_id, "is_active": True})
    return AdminDocument(**raw) if raw else None


async def is_admin(user_id: int) -> bool:
    admin = await get_admin(user_id)
    return admin is not None


async def is_owner(user_id: int) -> bool:
    admin = await get_admin(user_id)
    return bool(admin and admin.is_owner)


async def add_admin(
    user_id: int,
    username: Optional[str],
    first_name: Optional[str],
    added_by: int,
    permissions: Optional[List[str]] = None,
) -> AdminDocument:
    db = get_db()
    doc = AdminDocument(
        user_id=user_id,
        username=username,
        first_name=first_name,
        is_owner=False,
        permissions=permissions or ["reply", "view"],
        added_by=added_by,
    )
    await db.admins.update_one(
        {"user_id": user_id},
        {"$set": doc.model_dump()},
        upsert=True,
    )
    return doc


async def remove_admin(user_id: int) -> bool:
    db = get_db()
    # Never remove owner
    result = await db.admins.update_one(
        {"user_id": user_id, "is_owner": False},
        {"$set": {"is_active": False}},
    )
    return result.modified_count > 0


async def list_admins() -> List[AdminDocument]:
    db = get_db()
    cursor = db.admins.find({"is_active": True}).sort("is_owner", -1)
    return [AdminDocument(**doc) async for doc in cursor]


# ───────────────────────────── USERS ─────────────────────────────


async def upsert_user(
    bot_id: int,
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    language_code: Optional[str] = None,
) -> UserDocument:
    db = get_db()
    now = utcnow()
    update = {
        "$set": {
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "language_code": language_code,
            "updated_at": now,
            "last_message_at": now,
        },
        "$inc": {"message_count": 1},
        "$setOnInsert": {
            "bot_id": bot_id,
            "user_id": user_id,
            "created_at": now,
            "is_blocked": False,
        },
    }
    await db.users.update_one(
        {"bot_id": bot_id, "user_id": user_id},
        update,
        upsert=True,
    )
    raw = await db.users.find_one({"bot_id": bot_id, "user_id": user_id})
    return UserDocument(**raw)


async def get_user(bot_id: int, user_id: int) -> Optional[UserDocument]:
    db = get_db()
    raw = await db.users.find_one({"bot_id": bot_id, "user_id": user_id})
    return UserDocument(**raw) if raw else None


async def update_user_auto_reply(bot_id: int, user_id: int) -> None:
    db = get_db()
    await db.users.update_one(
        {"bot_id": bot_id, "user_id": user_id},
        {"$set": {"last_auto_reply_at": utcnow()}},
    )


async def count_users(bot_id: Optional[int] = None) -> int:
    db = get_db()
    query = {"bot_id": bot_id} if bot_id else {}
    return await db.users.count_documents(query)


# ───────────────────────────── MESSAGE MAPPINGS ─────────────────────────────


async def save_message_mapping(
    group_message_id: int,
    group_chat_id: int,
    bot_id: int,
    user_chat_id: int,
    user_id: int,
    original_message_id: Optional[int] = None,
    content_type: str = "text",
) -> MessageMappingDocument:
    db = get_db()
    doc = MessageMappingDocument(
        group_message_id=group_message_id,
        group_chat_id=group_chat_id,
        bot_id=bot_id,
        user_chat_id=user_chat_id,
        user_id=user_id,
        original_message_id=original_message_id,
        content_type=content_type,
    )
    await db.message_mappings.insert_one(doc.model_dump())
    return doc


async def get_mapping_by_group_message(
    group_chat_id: int, group_message_id: int
) -> Optional[MessageMappingDocument]:
    db = get_db()
    raw = await db.message_mappings.find_one(
        {"group_chat_id": group_chat_id, "group_message_id": group_message_id}
    )
    return MessageMappingDocument(**raw) if raw else None


async def get_mapping_by_reply(
    group_chat_id: int, reply_to_message_id: int
) -> Optional[MessageMappingDocument]:
    """Find mapping when admin replies to a forwarded message."""
    return await get_mapping_by_group_message(group_chat_id, reply_to_message_id)


# ───────────────────────────── ACTIVITY LOGS ─────────────────────────────


async def log_activity(
    action: str,
    actor_id: Optional[int] = None,
    bot_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    db = get_db()
    doc = ActivityLogDocument(
        action=action,
        actor_id=actor_id,
        bot_id=bot_id,
        details=details or {},
    )
    await db.activity_logs.insert_one(doc.model_dump())


async def get_recent_logs(limit: int = 20) -> List[ActivityLogDocument]:
    db = get_db()
    cursor = db.activity_logs.find().sort("created_at", -1).limit(limit)
    return [ActivityLogDocument(**doc) async for doc in cursor]


# ───────────────────────────── STATISTICS ─────────────────────────────


async def get_global_stats() -> Dict[str, Any]:
    db = get_db()
    bots = await get_all_bots()
    active = sum(1 for b in bots if b.is_active)
    total_messages = sum(b.total_messages for b in bots)
    total_replies = sum(b.total_replies for b in bots)
    total_users = await count_users()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_doc = await db.statistics.find_one({"date": today})
    today_messages = today_doc.get("total_messages", 0) if today_doc else 0

    return {
        "total_bots": len(bots),
        "active_bots": active,
        "disabled_bots": len(bots) - active,
        "total_users": total_users,
        "total_messages": total_messages,
        "total_replies": total_replies,
        "today_messages": today_messages,
        "bots": bots,
    }


async def increment_daily_stat(field: str = "total_messages", bot_id: Optional[int] = None) -> None:
    db = get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    update: Dict[str, Any] = {"$inc": {field: 1}, "$set": {"updated_at": utcnow()}}
    if bot_id is not None:
        update["$inc"][f"per_bot.{bot_id}.{field}"] = 1
    await db.statistics.update_one({"date": today}, update, upsert=True)
