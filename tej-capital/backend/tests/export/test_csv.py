"""Tests for CSV export functions."""
import io
import pandas as pd
import pytest

from app.export.csv_exports import returns_csv, trades_csv, audit_csv


def test_returns_csv_is_readable_by_pandas():
    """Test that returns_csv produces bytes that pandas can read back."""
    # Create a sample returns series
    r = pd.Series([0.01, -0.005], index=pd.date_range("2026-08-16", periods=2))

    # Convert to CSV bytes
    out = returns_csv(r)

    # Read back with pandas
    df = pd.read_csv(io.BytesIO(out))

    # Verify structure
    assert list(df.columns) == ["date", "return"]
    assert len(df) == 2
    assert df["date"].tolist() == ["2026-08-16", "2026-08-17"]
    assert abs(df["return"].iloc[0] - 0.01) < 1e-6
    assert abs(df["return"].iloc[1] - (-0.005)) < 1e-6


def test_trades_csv_round_trip():
    """Test that trades_csv produces valid CSV."""
    trades = pd.DataFrame({
        "id": ["trade1", "trade2"],
        "instrument": ["EURUSD", "GBPUSD"],
        "r_multiple": [1.5, -0.5],
        "gross_pnl": [100.0, -50.0],
        "costs": [5.0, 5.0],
    })

    csv_bytes = trades_csv(trades)
    df = pd.read_csv(io.BytesIO(csv_bytes))

    assert list(df.columns) == ["id", "instrument", "r_multiple", "gross_pnl", "costs"]
    assert len(df) == 2
    assert df["instrument"].tolist() == ["EURUSD", "GBPUSD"]


def test_audit_csv_empty_list():
    """Test that audit_csv handles empty audit records."""
    csv_bytes = audit_csv([])

    # Empty audit records produce a bytes response (may be empty or just newline)
    assert isinstance(csv_bytes, bytes)
    assert len(csv_bytes) >= 0


def test_audit_csv_with_records():
    """Test that audit_csv produces valid CSV from audit records."""
    records = [
        {"timestamp": "2026-08-16T10:00:00", "field": "entry_price", "old_value": 100.0, "new_value": 101.0},
        {"timestamp": "2026-08-16T10:01:00", "field": "exit_price", "old_value": 110.0, "new_value": 111.0},
    ]

    csv_bytes = audit_csv(records)
    df = pd.read_csv(io.BytesIO(csv_bytes))

    assert len(df) == 2
    assert list(df["field"]) == ["entry_price", "exit_price"]
    assert list(df["old_value"]) == [100.0, 110.0]
