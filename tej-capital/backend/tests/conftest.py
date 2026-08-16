import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db import Base
from app.db import engine as app_engine
import app.domain  # noqa


@pytest.fixture(autouse=True)
async def _dispose_app_engine():
    """app.db.engine is a module-level singleton whose pooled asyncpg
    connections are bound to the event loop they were created on. Since
    pytest-asyncio gives each test function its own loop, a connection
    checked out here (via the ASGI app -> get_db -> SessionLocal) would
    otherwise leak into a later test file's loop and blow up with
    'Future attached to a different loop'. Dispose the pool after every
    test in this package so each test starts clean.

    Mirrors tests/api/conftest.py so root-level tests (e.g.
    test_full_flow.py) that drive the app through the ASGI transport get
    the same guarantee.
    """
    yield
    await app_engine.dispose()


@pytest.fixture(scope="session")
async def test_engine():
    url = get_settings().database_url.replace("/tej_capital", "/tej_capital_test")
    engine = create_async_engine(url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db(test_engine):
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as s:
        yield s
        await s.rollback()
