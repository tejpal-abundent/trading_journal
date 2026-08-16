"""Temporal activities for nightly close: thin wrappers around production code or stubs for external I/O."""
from datetime import date
from temporalio import activity

from app.db import SessionLocal
from app.services.snapshot import freeze_snapshot


@activity.defn
async def fetch_all_marks(as_of: str) -> int:
    """Fetch mark-to-market prices from external data sources (broker APIs, data feeds).

    v1: No adapters configured → returns 0 marks fetched.
    Future: Integrate with real mark providers (IB, Stripe, etc.).

    Args:
        as_of: ISO date string (YYYY-MM-DD).

    Returns:
        Count of marks fetched.
    """
    return 0


@activity.defn
async def reconcile_ledger(as_of: str) -> int:
    """Reconcile cash flows, trades, and nav against ledger state.

    v1: Stub implementation → returns 0 discrepancies.
    Future: Query database and validate ledger integrity.

    Args:
        as_of: ISO date string (YYYY-MM-DD).

    Returns:
        Count of discrepancies found and corrected.
    """
    return 0


@activity.defn
async def detect_anomalies_activity(as_of: str) -> int:
    """Detect anomalies (outlier trades, missing marks, malformed records).

    v1: Stub implementation → returns 0 anomalies.
    Future: Implement statistical anomaly detection.

    Args:
        as_of: ISO date string (YYYY-MM-DD).

    Returns:
        Count of anomalies detected.
    """
    return 0


@activity.defn
async def evaluate_policy_limits(as_of: str) -> int:
    """Evaluate risk policy compliance (position limits, drawdown stops, etc.).

    v1: Stub implementation → returns 0 violations.
    Future: Query risk policies and evaluate against positions.

    Args:
        as_of: ISO date string (YYYY-MM-DD).

    Returns:
        Count of policy violations detected.
    """
    return 0


@activity.defn
async def freeze_snapshot_activity(as_of: str) -> str:
    """Compute and freeze a metric snapshot with a SHA256 ledger hash for point-in-time audit trail.

    Delegates to app.services.snapshot.freeze_snapshot, which is idempotent per date.

    Args:
        as_of: ISO date string (YYYY-MM-DD).

    Returns:
        Hex-encoded SHA256 ledger hash (proof of ledger state at as_of_date).
    """
    async with SessionLocal() as db:
        snap, _ = await freeze_snapshot(db, as_of_date=date.fromisoformat(as_of))
        return snap.ledger_hash


@activity.defn
async def send_nightly_alert(as_of: str) -> bool:
    """Send nightly summary alert (Telegram, email, Slack, etc.).

    Lazily imports from app.alerts.telegram to allow Task 24 to provide the full implementation.
    Returns False if send_nightly does not exist yet.

    Args:
        as_of: ISO date string (YYYY-MM-DD).

    Returns:
        True if alert sent successfully, False otherwise.
    """
    try:
        from app.alerts.telegram import send_nightly
        return await send_nightly(as_of)
    except (ImportError, AttributeError):
        # send_nightly not yet implemented (Task 24); silently return False for now.
        return False
