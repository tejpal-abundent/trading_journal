"""Test that workflow and activities are importable without a running Temporal server."""


def test_workflow_definitions_importable():
    """Verify that the nightly close workflow and activities can be imported."""
    from app.workflows.nightly_close import NightlyCloseWorkflow
    from app.workflows import activities

    assert NightlyCloseWorkflow is not None
    assert hasattr(activities, "fetch_all_marks")
    assert hasattr(activities, "reconcile_ledger")
    assert hasattr(activities, "detect_anomalies_activity")
    assert hasattr(activities, "evaluate_policy_limits")
    assert hasattr(activities, "freeze_snapshot_activity")
    assert hasattr(activities, "send_nightly_alert")
