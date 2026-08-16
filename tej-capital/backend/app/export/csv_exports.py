"""CSV export functions for returns, trades, and audit data."""
import io
import pandas as pd


def returns_csv(returns: pd.Series) -> bytes:
    """Convert a pandas Series of returns to CSV format as bytes.

    Args:
        returns: A pandas Series indexed by date with float return values

    Returns:
        UTF-8 encoded CSV bytes with columns: date, return
    """
    df = pd.DataFrame({
        "date": returns.index.strftime("%Y-%m-%d"),
        "return": returns.values,
    })
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode("utf-8")


def trades_csv(trades_df: pd.DataFrame) -> bytes:
    """Convert a trades DataFrame to CSV format as bytes.

    Args:
        trades_df: A DataFrame with trade records

    Returns:
        UTF-8 encoded CSV bytes
    """
    csv_buffer = io.StringIO()
    trades_df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode("utf-8")


def audit_csv(audit_records: list[dict]) -> bytes:
    """Convert audit records to CSV format as bytes.

    Args:
        audit_records: A list of audit record dictionaries

    Returns:
        UTF-8 encoded CSV bytes
    """
    df = pd.DataFrame(audit_records)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode("utf-8")
