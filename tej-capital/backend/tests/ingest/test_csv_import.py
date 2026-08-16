from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient, ASGITransport

from app.ingest.csv_import import CsvAdapter
from app.main import app

CSV = (
    b"OrderID,Symbol,Side,Open,Close,Qty,Opened,Closed\n"
    b"1,XAUUSD,long,2400,2430,0.1,2026-08-16T10:00,2026-08-16T15:00\n"
)

MAPPING = (
    '{"external_id":"OrderID","instrument":"Symbol","direction":"Side",'
    '"entry_price":"Open","exit_price":"Close","position_size":"Qty",'
    '"opened_at":"Opened","closed_at":"Closed"}'
)

MAPPING_DICT = {
    "external_id": "OrderID", "instrument": "Symbol", "direction": "Side",
    "entry_price": "Open", "exit_price": "Close", "position_size": "Qty",
    "opened_at": "Opened", "closed_at": "Closed",
}


async def _acct(ac):
    r = await ac.post("/api/accounts", json={"name": "M", "broker": "IBKR", "currency": "USD", "account_type": "live"})
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Adapter unit tests (no DB / HTTP involved)
# ---------------------------------------------------------------------------

def test_adapter_maps_columns_to_canonical_trade():
    adapter = CsvAdapter(CSV, MAPPING_DICT)
    trades = adapter.fetch_closed_trades(date(1900, 1, 1))
    assert len(trades) == 1
    t = trades[0]
    assert t.external_id == "1"
    assert t.instrument == "XAUUSD"
    assert t.direction == "long"
    assert t.entry_price == 2400
    assert t.exit_price == 2430
    assert t.position_size == Decimal("0.1")
    # Fields not present in the mapping fall back to None/0 rather than
    # raising — they're picked up later by the enrichment queue.
    assert t.gross_pnl is None
    assert t.costs == 0


def test_adapter_skips_rows_before_since():
    csv_bytes = (
        b"OrderID,Symbol,Side,Open,Close,Qty,Opened,Closed\n"
        b"1,XAUUSD,long,2400,2430,0.1,2020-01-01T10:00,2020-01-01T15:00\n"
        b"2,XAUUSD,long,2400,2430,0.1,2026-08-16T10:00,2026-08-16T15:00\n"
    )
    adapter = CsvAdapter(csv_bytes, MAPPING_DICT)
    trades = adapter.fetch_closed_trades(date(2026, 1, 1))
    assert [t.external_id for t in trades] == ["2"]


def test_adapter_fetch_equity_and_flows_are_empty_for_trades_only_mapping():
    adapter = CsvAdapter(CSV, MAPPING_DICT)
    assert adapter.fetch_equity(date(1900, 1, 1)).empty
    assert adapter.fetch_flows(date(1900, 1, 1)) == []


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_csv_import_idempotent_by_external_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        for _ in range(2):
            r = await ac.post(f"/api/ingest/csv?account_id={aid}",
                              files={"file": ("t.csv", CSV, "text/csv")},
                              data={"mapping": MAPPING})
            assert r.status_code == 200
        listing = await ac.get(f"/api/trades?since=2026-08-16&account_id={aid}")
        assert len(listing.json()) == 1  # not 2 — idempotent


@pytest.mark.asyncio
async def test_csv_import_first_call_imports_second_call_skips():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        first = await ac.post(f"/api/ingest/csv?account_id={aid}",
                              files={"file": ("t.csv", CSV, "text/csv")},
                              data={"mapping": MAPPING})
        assert first.json()["trades_imported"] == 1
        assert first.json()["trades_skipped"] == 0

        second = await ac.post(f"/api/ingest/csv?account_id={aid}",
                               files={"file": ("t.csv", CSV, "text/csv")},
                               data={"mapping": MAPPING})
        assert second.json()["trades_imported"] == 0
        assert second.json()["trades_skipped"] == 1


@pytest.mark.asyncio
async def test_csv_import_populates_enrichment_queue():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        r = await ac.post(f"/api/ingest/csv?account_id={aid}",
                          files={"file": ("t2.csv", CSV, "text/csv")},
                          data={"mapping": MAPPING})
        assert r.status_code == 200

        queue = await ac.get("/api/trades/enrichment")
        own = [row for row in queue.json() if row["account_id"] == aid]
        assert len(own) == 1
        assert own[0]["risk_amount"] is None
        assert own[0]["setup_id"] is None
        assert own[0]["enrichment_needed"] is True
        assert own[0]["external_id"] == "1"


@pytest.mark.asyncio
async def test_csv_import_respects_since_query_param():
    old_csv = (
        b"OrderID,Symbol,Side,Open,Close,Qty,Opened,Closed\n"
        b"9,XAUUSD,long,2400,2430,0.1,2020-01-01T10:00,2020-01-01T15:00\n"
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        r = await ac.post(f"/api/ingest/csv?account_id={aid}&since=2025-01-01",
                          files={"file": ("old.csv", old_csv, "text/csv")},
                          data={"mapping": MAPPING})
        assert r.status_code == 200
        assert r.json()["trades_imported"] == 0
        assert r.json()["trades_skipped"] == 0  # skipped by `since`, not by conflict


@pytest.mark.asyncio
async def test_correcting_an_imported_trade_does_not_violate_external_id_uniqueness():
    """Regression test for the bug fixed by migration 0002: a correction
    supersedes the old row but carries external_id forward onto the new
    row. With the old plain unique constraint this 500'd; with the
    partial index (WHERE superseded_by IS NULL) it succeeds because the
    old row no longer matches the partial predicate once superseded.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        aid = await _acct(ac)
        r = await ac.post(f"/api/ingest/csv?account_id={aid}",
                          files={"file": ("t3.csv", CSV, "text/csv")},
                          data={"mapping": MAPPING})
        assert r.status_code == 200

        listing = await ac.get(f"/api/trades?account_id={aid}")
        trade_id = listing.json()[0]["id"]

        corrected = await ac.post(f"/api/trades/{trade_id}/correct", json={
            "entry_price": "2401.00",
            "reason": "fixed a fat-fingered entry price from the CSV export",
        })
        assert corrected.status_code == 200
        assert corrected.json()["external_id"] == "1"
        assert corrected.json()["entry_price"] == "2401.00000000" or float(corrected.json()["entry_price"]) == 2401.0
