import os
import sqlite3
import pytest

# Use a temp SQLite DB and the same SQL migrations the production code runs.
from migrations import V2_ALTERS, ZONE_FAILURE_CRITERIA, ZONE_FAILURE_CORE


@pytest.fixture
def conn(tmp_path):
    db = tmp_path / "test.db"
    c = sqlite3.connect(db)
    # Seed with v1 schema
    c.executescript("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair TEXT NOT NULL, direction TEXT NOT NULL, timeframe TEXT NOT NULL,
            setup_score INTEGER NOT NULL, verdict TEXT NOT NULL,
            criteria_checked TEXT NOT NULL, notes TEXT DEFAULT '',
            status TEXT DEFAULT 'open',
            entry_price REAL, exit_price REAL, stop_loss REAL, take_profit REAL,
            pnl REAL, pnl_percent REAL, rr_achieved REAL,
            lessons TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            closed_at TEXT
        );
    """)
    c.commit()
    yield c
    c.close()


def _apply_alters(conn):
    for sql in V2_ALTERS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                raise
    conn.commit()


def test_alters_add_all_v2_columns(conn):
    _apply_alters(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(trades)").fetchall()}
    expected_new = {
        "strategy", "planned_entry", "planned_stop", "planned_target", "planned_rr",
        "retroactive", "position_size", "account_size", "risk_dollars", "risk_percent",
        "entry_timing", "emotions_entry", "feelings_entry", "skip_reason",
        "partial_exits", "rules_followed", "mistake_tags", "emotions_exit",
        "feelings_exit", "chart_url",
    }
    assert expected_new.issubset(cols)


def test_alters_are_idempotent(conn):
    _apply_alters(conn)
    _apply_alters(conn)  # second run must not raise


def test_zone_failure_criteria_has_11_items():
    assert len(ZONE_FAILURE_CRITERIA) == 11
    assert ZONE_FAILURE_CORE == ["trend", "zone", "signal", "failure"]
