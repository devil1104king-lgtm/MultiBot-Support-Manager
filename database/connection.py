"""MongoDB connection management with Motor."""

from typing import Optional

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
async def init_db() -> AsyncIOMotorDatabase:
    """Initialize MongoDB connection with retry logic."""
    global _client, _db

    if _db is not None:
        return _db

    logger.info("Connecting to MongoDB Atlas...")
    _client = AsyncIOMotorClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=15000,
        connectTimeoutMS=15000,
        maxPoolSize=50,
        minPoolSize=5,
        retryWrites=True,
    )

    # Force connection check
    await _client.admin.command("ping")
    _db = _client[settings.mongodb_db_name]

    # Create indexes
    await _create_indexes(_db)
    logger.info(f"MongoDB connected successfully → database: {settings.mongodb_db_name}")
    return _db


async def _create_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create required indexes for performance and uniqueness."""
    # bots collection
    await db.bots.create_index("bot_id", unique=True)
    await db.bots.create_index("token_hash", unique=True)
    await db.bots.create_index("is_active")

    # admins collection
    await db.admins.create_index("user_id", unique=True)

    # users collection
    await db.users.create_index([("bot_id", 1), ("user_id", 1)], unique=True)
    await db.users.create_index("bot_id")

    # message_mappings – critical for reply routing
    await db.message_mappings.create_index("group_message_id")
    await db.message_mappings.create_index([("bot_id", 1), ("user_chat_id", 1)])
    await db.message_mappings.create_index("created_at", expireAfterSeconds=60 * 60 * 24 * 30)  # 30 days TTL

    # activity_logs
    await db.activity_logs.create_index([("created_at", -1)])
    await db.activity_logs.create_index("action")

    # statistics
    await db.statistics.create_index("date", unique=True)

    # conversations (optional tracking)
    await db.conversations.create_index([("bot_id", 1), ("user_id", 1)])

    logger.debug("MongoDB indexes created / verified")


def get_db() -> AsyncIOMotorDatabase:
    """Return the current database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db


async def close_db() -> None:
    """Close MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")
    _client = None
    _db = None
