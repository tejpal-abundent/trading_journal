from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="TEJ_", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "postgresql+asyncpg://tej:tej@localhost:5432/tej_capital"
    timescale_enabled: bool = True

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    qdrant_url: str | None = None
    llm_api_key: str | None = None

    mt5_login: str | None = None
    bybit_api_key: str | None = None
    darwinex_api_key: str | None = None

    allocator_link_secret: str = "change-me-in-prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
