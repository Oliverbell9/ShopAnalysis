"""Governed ingestion execution coordinator.

Coordinates audit lifecycle operations around an ingestion action.
Does not claim cross-database transaction atomicity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar

from observability.audit_collector import AuditCollector
from observability.commit_state import CommitState, CommitTracker
from observability.ingestion_config import (
    EXPECTED_RAW_TABLES,
    PIPELINE_NAME,
    STAGE_NAME,
)
from observability.ingestion_evidence import validate_ingestion_evidence
from observability.ingestion_result import RawIngestionResult
from observability.raw_reconciliation import measure_verified_raw_batch

T = TypeVar("T")


class GovernedIngestionError(RuntimeError):
    """Governed execution failed or could not be audited reliably."""


class PostCommitAuditError(GovernedIngestionError):
    """RAW committed, but audit finalization was unsuccessful."""


def execute_governed_ingestion(
    action: Callable[[CommitTracker], T],
    audit_database: Path,
    pipeline_name: str,
    environment: str,
    stage_name: str,
    batch_id: str | None = None,
) -> T:
    """Execute one ingestion action with mandatory lifecycle auditing.

    The action must return only after its RAW transaction commits.
    """

    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError(
            "Governed Olist RAW ingestion requires a nonempty batch ID"
        )

    collector = AuditCollector(audit_database)

    # Verify audit write access before executing the RAW action.
    run_id = collector.start_pipeline(
        pipeline_name=pipeline_name,
        environment=environment,
        batch_id=batch_id,
    )

    stage_id = None
    tracker = CommitTracker()

    try:
        stage_id = collector.start_stage(run_id, stage_name)

        result = action(tracker)

        if tracker.state != CommitState.COMMITTED:
            raise GovernedIngestionError(
                "RAW action returned without a confirmed COMMIT. "
                f"Observed state: {tracker.state.value}. "
                "Audit remains pending investigation."
            )

        if pipeline_name != PIPELINE_NAME or stage_name != STAGE_NAME:
            raise GovernedIngestionError(
                "Governed Olist RAW ingestion identity mismatch"
            )

        if not isinstance(result, RawIngestionResult):
            raise GovernedIngestionError(
                "Committed RAW action did not return RawIngestionResult"
            )

        if result.batch_id != batch_id:
            raise GovernedIngestionError(
                "Committed RAW batch does not match pipeline batch identity"
            )

        observed_rows = measure_verified_raw_batch(
            database=result.database_path,
            expected_batch_id=batch_id,
            expected_rows=result.source_rows,
        )

        for table in EXPECTED_RAW_TABLES:
            collector.record_reconciliation_result(
                run_id=run_id,
                stage_attempt_id=stage_id,
                entity_name=table,
                source_rows=result.source_rows[table],
                target_rows=observed_rows[table],
                batch_id=batch_id,
            )

        collector.record_quality_result(
            run_id=run_id,
            stage_attempt_id=stage_id,
            test_name="raw_batch_integrity",
            status="PASS",
            entity_name=None,
            observed_value="RAW_BATCH_VERIFIED",
            expected_value="RAW_BATCH_VERIFIED",
        )

        evidence_verified, evidence_reason = validate_ingestion_evidence(
            audit_database=audit_database,
            run_id=run_id,
            stage_attempt_id=stage_id,
            batch_id=batch_id,
            expected_rows=dict(result.source_rows),
        )

        if not evidence_verified:
            raise GovernedIngestionError(
                f"Ingestion evidence validation failed: {evidence_reason}"
            )

        collector.finish_stage(stage_id, "SUCCESS")
        collector.finish_pipeline(run_id, "SUCCESS")

        return result

    except BaseException as original_error:
        if tracker.state == CommitState.COMMITTED:
            raise PostCommitAuditError(
                "RAW COMMIT was confirmed, but governed execution "
                "did not complete successfully. Do not automatically "
                "rerun ingestion. Inspect and recover the audit."
            ) from original_error

        if tracker.state != CommitState.ROLLED_BACK:
            raise GovernedIngestionError(
                "RAW transaction outcome is not confirmed rolled back. "
                f"Observed state: {tracker.state.value}. "
                "Audit remains RUNNING pending investigation. "
                "Do not automatically rerun ingestion."
            ) from original_error

        cleanup_errors = []

        if stage_id is not None:
            try:
                collector.finish_stage(
                    stage_id,
                    "FAILED",
                    type(original_error).__name__,
                    str(original_error),
                )
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)

        try:
            collector.finish_pipeline(
                run_id,
                "FAILED",
                type(original_error).__name__,
                str(original_error),
            )
        except Exception as cleanup_error:
            cleanup_errors.append(cleanup_error)

        if cleanup_errors:
            raise GovernedIngestionError(
                "RAW rollback was confirmed, but audit failure "
                "recording was incomplete. Original error: "
                f"{type(original_error).__name__}: {original_error}. "
                "Audit cleanup errors: "
                + "; ".join(str(e) for e in cleanup_errors)
            ) from original_error

        raise
