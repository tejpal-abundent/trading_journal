import pytest

from app.db import engine as app_engine


@pytest.fixture(autouse=True)
async def _dispose_app_engine():
    """See tests/api/conftest.py for the full rationale: app.db.engine is a
    module-level singleton whose pooled asyncpg connections are bound to
    the event loop they were created on, and pytest-asyncio gives each
    test function its own loop. Dispose the pool after every test in this
    package so each test starts clean.
    """
    yield
    await app_engine.dispose()
