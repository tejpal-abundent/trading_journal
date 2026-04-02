from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
import os

# Use Turso in production (set TURSO_DB_URL env var), SQLite locally
TURSO_URL = os.environ.get("TURSO_DB_URL")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

if TURSO_URL:
    DATABASE_URL = f"sqlite+aiosqlite://?uri={TURSO_URL}&authToken={TURSO_TOKEN}"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "trading_journal.db")
    DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
