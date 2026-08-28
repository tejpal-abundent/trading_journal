from functools import lru_cache
from typing import Literal

from pydantic import field_validator
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

    @field_validator("database_url")
    @classmethod
    def _ensure_async_driver(cls, v: str) -> str:
        """Managed Postgres providers (Render, Heroku, Neon, Supabase) hand back
        `postgres://` or `postgresql://` connection strings. SQLAlchemy's async
        engine needs the driver name spelled out — rewrite to asyncpg when
        neither driver is specified.

        Also translate the libpq/psycopg2 `sslmode=` query param to the
        asyncpg-friendly `ssl=` form. Neon and Supabase both hand out URLs
        with `?sslmode=require&channel_binding=require`; asyncpg refuses the
        first and doesn't know the second, so we normalize both away."""
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://") :]
        # sslmode -> ssl (asyncpg vocabulary)
        v = v.replace("?sslmode=", "?ssl=").replace("&sslmode=", "&ssl=")
        # channel_binding is a libpq feature asyncpg doesn't parse; drop it
        v = v.replace("&channel_binding=require", "").replace(
            "?channel_binding=require", "?"
        )
        # Clean up a dangling '?' if channel_binding was the only query param
        if v.endswith("?"):
            v = v[:-1]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
