"""Idempotent schema migrations. Run at startup."""
import json

ZONE_FAILURE_CRITERIA = [
    {"id": "trend",   "label": "Trade is in direction of the overall trend", "points": 20, "category": "Core",    "description": "Downtrend = only short setups, Uptrend = only long setups"},
    {"id": "zone",    "label": "Pattern formed at a KEY zone (S/R, trendline, EMA)", "points": 15, "category": "Core",    "description": "Not in mid-range / no man's land"},
    {"id": "signal",  "label": "Signal candle present (Hammer / Hanging Man)", "points": 15, "category": "Core",    "description": "The trap candle that baits traders the wrong way"},
    {"id": "failure", "label": "Next candle is solid body AGAINST the signal candle", "points": 20, "category": "Core",    "description": "Solid red after hammer = SHORT | Solid green after hanging man = LONG"},
    {"id": "body",    "label": "Failure candle has large real body (>60% of total range)", "points": 5, "category": "Quality", "description": "Shows conviction, not a weak doji"},
    {"id": "wick",    "label": "Signal candle wick is 2x+ the body", "points": 5, "category": "Quality", "description": "Shows deep rejection that trapped more traders"},
    {"id": "stop",    "label": "Stop placed beyond signal candle wick (clear invalidation)", "points": 5, "category": "Risk",    "description": "If price goes past the trap wick, thesis is wrong"},
    {"id": "rr",      "label": "R:R is at least 1:2 to next zone", "points": 5, "category": "Risk",    "description": "Target must be at least 2x your stop distance"},
    {"id": "htf",     "label": "Higher timeframe structure agrees", "points": 5, "category": "Quality", "description": "4H setup confirmed by Daily trend direction"},
    {"id": "macro",   "label": "No major news in next 4 hours", "points": 3, "category": "Timing",  "description": "Avoid FOMC, NFP, BOJ etc within 4 hours"},
    {"id": "volume",  "label": "Failure candle shows increased volume/momentum", "points": 2, "category": "Quality", "description": "Trapped traders exiting = visible momentum"},
]
ZONE_FAILURE_CORE = ["trend", "zone", "signal", "failure"]

V2_ALTERS = [
    "ALTER TABLE trades ADD COLUMN strategy TEXT NOT NULL DEFAULT 'Zone Failure'",
    "ALTER TABLE trades ADD COLUMN planned_entry REAL",
    "ALTER TABLE trades ADD COLUMN planned_stop REAL",
    "ALTER TABLE trades ADD COLUMN planned_target REAL",
    "ALTER TABLE trades ADD COLUMN planned_rr REAL",
    "ALTER TABLE trades ADD COLUMN retroactive INTEGER DEFAULT 0",
    "ALTER TABLE trades ADD COLUMN position_size REAL",
    "ALTER TABLE trades ADD COLUMN account_size REAL",
    "ALTER TABLE trades ADD COLUMN risk_dollars REAL",
    "ALTER TABLE trades ADD COLUMN risk_percent REAL",
    "ALTER TABLE trades ADD COLUMN entry_timing TEXT",
    "ALTER TABLE trades ADD COLUMN emotions_entry TEXT DEFAULT ','",
    "ALTER TABLE trades ADD COLUMN feelings_entry TEXT DEFAULT ''",
    "ALTER TABLE trades ADD COLUMN skip_reason TEXT DEFAULT ''",
    "ALTER TABLE trades ADD COLUMN partial_exits TEXT DEFAULT '[]'",
    "ALTER TABLE trades ADD COLUMN rules_followed INTEGER",
    "ALTER TABLE trades ADD COLUMN mistake_tags TEXT DEFAULT ','",
    "ALTER TABLE trades ADD COLUMN emotions_exit TEXT DEFAULT ','",
    "ALTER TABLE trades ADD COLUMN feelings_exit TEXT DEFAULT ''",
    "ALTER TABLE trades ADD COLUMN chart_url TEXT DEFAULT ''",
    "ALTER TABLE trades ADD COLUMN confluences TEXT DEFAULT ','",
    "ALTER TABLE trades ADD COLUMN mfe_r REAL",
    "ALTER TABLE trades ADD COLUMN mae_r REAL",
    "ALTER TABLE trades ADD COLUMN trailed_stops TEXT DEFAULT '[]'",
    "ALTER TABLE trades ADD COLUMN updated_at TEXT",
]

NEW_TABLES = [
    """CREATE TABLE IF NOT EXISTS strategies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        criteria TEXT NOT NULL,
        is_core_required TEXT DEFAULT '[]',
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS account_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        balance REAL NOT NULL,
        recorded_at TEXT DEFAULT (datetime('now')),
        note TEXT DEFAULT ''
    )""",
    """CREATE TABLE IF NOT EXISTS review_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        period_type TEXT NOT NULL,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        notes TEXT NOT NULL,
        stats_snapshot TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS _migrations (
        name TEXT PRIMARY KEY,
        applied_at TEXT DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS trading_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        body TEXT NOT NULL DEFAULT '',
        position INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""",
]


def run_migrations(execute_fn, fetch_one_fn):
    """Run all idempotent migrations. `execute_fn(sql, args=None)` and `fetch_one_fn(sql, args=None)` are passed in so this works for both Turso HTTP and SQLAlchemy."""
    # 1. Create new tables
    for sql in NEW_TABLES:
        execute_fn(sql)

    # 2. ALTERs (ignore duplicate-column errors)
    for sql in V2_ALTERS:
        try:
            execute_fn(sql)
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                raise

    # 3. Seed Zone Failure strategy if empty (no default criteria — user qualifies trades via confluences)
    row = fetch_one_fn("SELECT COUNT(*) AS c FROM strategies")
    if int(row["c"]) == 0:
        execute_fn(
            "INSERT INTO strategies (name, criteria, is_core_required) VALUES (?, ?, ?)",
            ["Zone Failure", "[]", "[]"],
        )

    # 4. One-time: drop Zone Failure default criteria (user moved to confluence-based qualification)
    already = fetch_one_fn("SELECT name FROM _migrations WHERE name = ?", ["v3_empty_zone_failure_criteria"])
    if not already:
        execute_fn(
            "UPDATE strategies SET criteria = ?, is_core_required = ? WHERE name = ?",
            ["[]", "[]", "Zone Failure"],
        )
        execute_fn("INSERT INTO _migrations (name) VALUES (?)", ["v3_empty_zone_failure_criteria"])

    # 5. One-time status backfill
    already = fetch_one_fn("SELECT name FROM _migrations WHERE name = ?", ["v2_status_backfill"])
    if not already:
        # Open trades with entry_price -> entered, retroactive=1
        execute_fn(
            "UPDATE trades SET status='entered', retroactive=1 WHERE status='open' AND entry_price IS NOT NULL"
        )
        # Open trades without entry_price -> planned
        execute_fn(
            "UPDATE trades SET status='planned' WHERE status='open' AND entry_price IS NULL"
        )
        # Closed trades flagged retroactive
        execute_fn(
            "UPDATE trades SET retroactive=1 WHERE status IN ('win','loss','breakeven')"
        )
        execute_fn("INSERT INTO _migrations (name) VALUES (?)", ["v2_status_backfill"])

    # 6. One-time: backfill updated_at = created_at where null
    already = fetch_one_fn("SELECT name FROM _migrations WHERE name = ?", ["v3_updated_at_backfill"])
    if not already:
        execute_fn("UPDATE trades SET updated_at = created_at WHERE updated_at IS NULL")
        execute_fn("INSERT INTO _migrations (name) VALUES (?)", ["v3_updated_at_backfill"])

    # 7. One-time: seed the 4 starter trading rules
    already = fetch_one_fn("SELECT name FROM _migrations WHERE name = ?", ["v4_seed_trading_rules"])
    if not already:
        seed = [
            ("Cut losses early on structure breaks",
             "If a key level or zone breaks in the opposite direction of my position, treat it as confirmation that the move is going against me. Cut the loss immediately at 30%, 50%, or 70% of the planned risk rather than waiting for the full stop loss to be hit. If price later proves me wrong by reversing back into my original direction, re-enter the trade."),
            ("Quality trades only — every trade must be fully explainable",
             "I only take trades I can justify in detail (clear setup, confluence, reasoning). The stop loss on every trade must sit between $100 and $150 until my total account reaches $12,000 (after which the range scales up). If a trade can't meet this standard, I don't take it. Think twice before entering — only sure, high-conviction setups."),
            ("Maximum 4% account risk at any time",
             "At no point may my total open risk exceed 4% of my account balance. This caps exposure across all active positions, not just per trade."),
            ("Wait for the 4H candle close",
             "No acting on intra-candle movement. Wait for confirmation, particularly on the 4H timeframe."),
        ]
        for i, (title, body) in enumerate(seed):
            execute_fn(
                "INSERT INTO trading_rules (title, body, position) VALUES (?, ?, ?)",
                [title, body, i],
            )
        execute_fn("INSERT INTO _migrations (name) VALUES (?)", ["v4_seed_trading_rules"])
