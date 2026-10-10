"""Operator-authorized recovery of a committed RAW ingestion pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from observability.audit_collector import AuditCollector
from observability.ingestion_config import EXPECTED_RAW_TABLES
from observability.pipeline_recovery_evidence import (
    validate_pipeline_recovery_evidence_in_transaction,
)
from observability.raw_batch_verifier import inspect_raw_batch


RECOVERY_AUTHORIZATION = "AUTHORIZE_PIPELINE_RECOVERY"


class PipelineRecoveryError(RuntimeError):
    """Recovery was rejected or could not be safely completed."""


def recover_committed_pipeline(
    *,
    raw_database: Path,
    audit_database: Path,
    run_id: str,
    stage_attempt_id: str,
    batch_id: str,
    expected_rows: Mapping[str, int],
    authorization: str,
) -> str:
    """Finalize a verified pipeline without rerunning RAW ingestion."""

    if authorization != RECOVERY_AUTHORIZATION:
        raise PipelineRecoveryError(
            "RECOVERY_NOT_AUTHORIZED"
        )

    if not all(
        isinstance(value, str) and value.strip()
        for value in (run_id, stage_attempt_id, batch_id)
    ):
        raise PipelineRecoveryError(
            "INVALID_RECOVERY_IDENTIFIERS"
        )

    try:
        expected = dict(expected_rows)
    except (TypeError, ValueError) as exc:
        raise PipelineRecoveryError(
            "INVALID_EXPECTED_ROWS"
        ) from exc

    if set(expected) != set(EXPECTED_RAW_TABLES):
        raise PipelineRecoveryError(
            "INVALID_EXPECTED_TABLE_SET"
        )

    if any(
        type(value) is not int or value < 0
        for value in expected.values()
    ):
        raise PipelineRecoveryError(
            "INVALID_EXPECTED_ROW_COUNT"
        )

    raw_path = Path(raw_database).resolve()
    audit_path = Path(audit_database).resolve()

    if not raw_path.is_file():
        raise PipelineRecoveryError(
            "RAW_DATABASE_MISSING"
        )

    if not audit_path.is_file():
        raise PipelineRecoveryError(
            "AUDIT_DATABASE_MISSING"
        )

    if raw_path == audit_path:
        raise PipelineRecoveryError(
            "RAW_AND_AUDIT_DATABASES_MUST_DIFFER"
        )

    # Independent read-only RAW verification.
    valid_raw, raw_reason, measured = inspect_raw_batch(
        database=raw_path,
        expected_batch_id=batch_id,
        expected_rows=expected,
    )

    if not valid_raw:
        raise PipelineRecoveryError(
            f"RAW_VERIFICATION_FAILED:{raw_reason}"
        )

    if measured is None or dict(measured) != expected:
        raise PipelineRecoveryError(
            "RAW_MEASURED_COUNTS_MISMATCH"
        )

    collector = AuditCollector(audit_path)

    # Evidence validation and finalization share one audit transaction.
    with collector.transaction() as connection:
        valid_evidence, evidence_reason = (
            validate_pipeline_recovery_evidence_in_transaction(
                connection=connection,
                run_id=run_id,
                stage_attempt_id=stage_attempt_id,
                batch_id=batch_id,
                expected_rows=expected,
            )
        )

        if not valid_evidence:
            raise PipelineRecoveryError(
                f"AUDIT_EVIDENCE_REJECTED:{evidence_reason}"
            )

        # Recheck the expected lifecycle immediately before updating.
        current = connection.execute(
            """
            SELECT status
            FROM audit.pipeline_runs
            WHERE run_id = ?
            """,
            [run_id],
        ).fetchone()

        if current != ("RUNNING",):
            raise PipelineRecoveryError(
                "PIPELINE_NOT_RUNNING"
            )

        active = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit.stage_runs
            WHERE run_id = ?
              AND status = 'RUNNING'
            """,
            [run_id],
        ).fetchone()[0]

        if active != 0:
            raise PipelineRecoveryError(
                "ACTIVE_STAGE_ATTEMPTS_PRESENT"
            )

        # Conditional update prevents finalizing a different lifecycle state.
        connection.execute(
            """
            UPDATE audit.pipeline_runs
            SET status = 'SUCCESS',
                ended_at = CURRENT_TIMESTAMP,
                error_type = NULL,
                error_message = NULL
            WHERE run_id = ?
              AND status = 'RUNNING'
            """,
            [run_id],
        )

        finalized = connection.execute(
            """
            SELECT status, ended_at, error_type, error_message
            FROM audit.pipeline_runs
            WHERE run_id = ?
            """,
            [run_id],
        ).fetchone()

        if (
            finalized is None
            or finalized[0] != "SUCCESS"
            or finalized[1] is None
            or finalized[2] is not None
            or finalized[3] is not None
        ):
            raise PipelineRecoveryError(
                "PIPELINE_FINALIZATION_CONFLICT"
            )

    return "PIPELINE_RECOVERY_FINALIZED"
