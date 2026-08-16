import pytest
from sqlalchemy import text
from app.db import engine


@pytest.mark.asyncio
async def test_all_tej_tables_exist_after_upgrade():
    expected = {
        "tej_accounts", "tej_nav_snapshots", "tej_cash_flows", "tej_playbook_setups",
        "tej_trades", "tej_journal_entries", "tej_policy_limits",
        "tej_policy_amendments", "tej_limit_breaches", "tej_policy_document",
        "tej_corrections_ledger", "tej_metric_snapshots",
        "tej_broker_reconciliations", "tej_settings", "tej_targets",
        "tej_allocator_tokens",
    }
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE tablename LIKE 'tej_%'"
        ))
        actual = {row[0] for row in result}
    missing = expected - actual
    assert not missing, f"missing tables: {missing}"
