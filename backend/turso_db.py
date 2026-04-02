"""Thin wrapper around Turso HTTP API for raw SQL execution."""
import requests
import json
import os
from datetime import datetime

TURSO_URL = os.environ.get("TURSO_DB_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

# Convert libsql:// to https://
HTTP_URL = TURSO_URL.replace("libsql://", "https://")


def _execute(sql: str, args=None):
    """Execute SQL against Turso HTTP API and return results."""
    url = f"{HTTP_URL}/v2/pipeline"
    headers = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}

    stmt = {"type": "execute", "stmt": {"sql": sql}}
    if args:
        stmt["stmt"]["args"] = [{"type": _type_of(v), "value": str(v) if v is not None else None} for v in args]

    body = {"requests": [stmt, {"type": "close"}]}
    resp = requests.post(url, headers=headers, json=body)
    resp.raise_for_status()
    data = resp.json()

    result = data["results"][0]
    if result["type"] == "error":
        raise Exception(result["error"]["message"])
    return result["response"]["result"]


def _type_of(v):
    if v is None:
        return "null"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "float"
    return "text"


def execute(sql: str, args=None):
    return _execute(sql, args)


def _cell_value(cell):
    """Extract value from a Turso cell, handling null and different formats."""
    if isinstance(cell, dict):
        if cell.get("type") == "null":
            return None
        return cell.get("value")
    return cell


def fetch_all(sql: str, args=None):
    """Execute SQL and return list of dicts."""
    result = _execute(sql, args)
    cols = [c["name"] for c in result["cols"]]
    rows = []
    for row in result["rows"]:
        rows.append({col: _cell_value(cell) for col, cell in zip(cols, row)})
    return rows


def fetch_one(sql: str, args=None):
    rows = fetch_all(sql, args)
    return rows[0] if rows else None


def init_tables():
    execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair TEXT NOT NULL,
            direction TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            setup_score INTEGER NOT NULL,
            verdict TEXT NOT NULL,
            criteria_checked TEXT NOT NULL,
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'open',
            entry_price REAL,
            exit_price REAL,
            stop_loss REAL,
            take_profit REAL,
            pnl REAL,
            pnl_percent REAL,
            rr_achieved REAL,
            lessons TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            closed_at TEXT
        )
    """)
