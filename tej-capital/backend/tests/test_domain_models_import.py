def test_all_models_importable_and_registered_on_base():
    from app.db import Base
    import app.domain  # noqa

    tables = {t.name for t in Base.metadata.tables.values()}
    expected = {
        "tej_accounts", "tej_nav_snapshots", "tej_cash_flows", "tej_playbook_setups",
        "tej_trades", "tej_journal_entries", "tej_policy_limits",
        "tej_policy_amendments", "tej_limit_breaches", "tej_policy_document",
        "tej_corrections_ledger", "tej_metric_snapshots",
        "tej_broker_reconciliations", "tej_settings", "tej_targets",
        "tej_allocator_tokens",
    }
    missing = expected - tables
    assert not missing, f"missing ORM models for: {missing}"
