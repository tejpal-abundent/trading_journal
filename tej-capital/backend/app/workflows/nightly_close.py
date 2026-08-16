"""Temporal workflow for nightly close process: marks, reconciliation, anomaly detection, policy evaluation, snapshot freeze, alerts."""
from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows import activities as A


@workflow.defn
class NightlyCloseWorkflow:
    """Orchestrates the complete nightly close pipeline:
    1. Fetch all marks
    2. Reconcile ledger
    3. Detect anomalies
    4. Evaluate policy limits
    5. Freeze snapshot (immutable ledger hash)
    6. Send nightly alert

    Returns a dict with as_of date and ledger_hash for audit trail.
    """

    @workflow.run
    async def run(self, as_of: str) -> dict:
        """
        Args:
            as_of: ISO date string (YYYY-MM-DD) for the nightly close date.

        Returns:
            {"as_of": as_of, "ledger_hash": sha256_hex_digest}
        """
        await workflow.execute_activity(
            A.fetch_all_marks, as_of, start_to_close_timeout=timedelta(minutes=5)
        )
        await workflow.execute_activity(
            A.reconcile_ledger, as_of, start_to_close_timeout=timedelta(minutes=2)
        )
        await workflow.execute_activity(
            A.detect_anomalies_activity, as_of, start_to_close_timeout=timedelta(minutes=1)
        )
        await workflow.execute_activity(
            A.evaluate_policy_limits, as_of, start_to_close_timeout=timedelta(minutes=1)
        )
        snap_hash = await workflow.execute_activity(
            A.freeze_snapshot_activity, as_of, start_to_close_timeout=timedelta(minutes=2)
        )
        await workflow.execute_activity(
            A.send_nightly_alert, as_of, start_to_close_timeout=timedelta(minutes=1)
        )
        return {"as_of": as_of, "ledger_hash": snap_hash}
