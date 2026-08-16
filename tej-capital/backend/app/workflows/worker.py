"""Temporal worker for nightly_close workflow.

Runs as: python -m app.workflows.worker

Requires: TEJ_TEMPORAL_HOST environment variable (e.g. localhost:7233).
If unset, worker exits gracefully — this is expected in v1 when no Temporal server is running.
"""
import asyncio
import os
import sys

from temporalio.client import Client
from temporalio.worker import Worker

from app.workflows.nightly_close import NightlyCloseWorkflow
from app.workflows import activities


async def main():
    """Initialize Temporal worker and begin polling for tasks.

    Exits gracefully (code 0) if TEJ_TEMPORAL_HOST is unset.
    """
    host = os.environ.get("TEJ_TEMPORAL_HOST")
    if not host:
        print(
            "TEJ_TEMPORAL_HOST is unset — worker will not start. "
            "This is expected in v1 unless you have a Temporal server running. "
            "See README §Integrations.",
            file=sys.stderr,
        )
        sys.exit(0)

    client = await Client.connect(host)
    worker = Worker(
        client,
        task_queue="tej-capital-nightly",
        workflows=[NightlyCloseWorkflow],
        activities=[
            activities.fetch_all_marks,
            activities.reconcile_ledger,
            activities.detect_anomalies_activity,
            activities.evaluate_policy_limits,
            activities.freeze_snapshot_activity,
            activities.send_nightly_alert,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
