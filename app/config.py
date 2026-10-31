"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Required
    master_bot_token: str = Field(..., description="Master bot token from BotFather")
    mongodb_uri: str = Field(..., description="MongoDB Atlas connection URI")
    owner_id: int = Field(..., description="Telegram user ID of the owner")
    webhook_base_url: str = Field(..., description="Public base URL for webhooks")

    # Optional with defaults
    webhook_secret: str = Field(
        default="default_webhook_secret_change_me",
        description="Secret for webhook path validation",
    )
    mongodb_db_name: str = Field(default="support_manager", description="MongoDB database name")
    log_level: str = Field(default="INFO", description="Logging level")

    # Internal
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=10000)

    @field_validator("webhook_base_url")
    @classmethod
    def normalize_webhook_url(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("owner_id", mode="before")
    @classmethod
    def parse_owner_id(cls, v):
        if isinstance(v, str):
            return int(v.strip())
        return v

    @property
    def master_webhook_path(self) -> str:
        return f"/webhook/master/{self.webhook_secret}"

    def bot_webhook_path(self, bot_id: int) -> str:
        return f"/webhook/bot/{bot_id}/{self.webhook_secret}"

    def full_webhook_url(self, path: str) -> str:
        return f"{self.webhook_base_url}{path}"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


# Convenience alias
settings = get_settings()
