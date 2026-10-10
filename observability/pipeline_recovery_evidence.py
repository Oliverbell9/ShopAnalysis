"""Recovery evidence validation for interrupted RAW pipelines."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import duckdb

from observability.ingestion_config import (
    EXPECTED_RAW_TABLES,
    PIPELINE_NAME,
    STAGE_NAME,
)


def _validate_inputs(
    run_id: str,
    stage_attempt_id: str,
    batch_id: str,
    expected_rows: Mapping[str, int],
) -> dict[str, int]:
    if not all(
        isinstance(value, str) and value.strip()
        for value in (run_id, stage_attempt_id, batch_id)
    ):
        raise ValueError("Recovery identifiers must be nonempty strings")

    expected = dict(expected_rows)

    if set(expected) != set(EXPECTED_RAW_TABLES):
        raise ValueError("Expected counts must cover exactly nine RAW tables")

    if any(
        type(value) is not int or value < 0
        for value in expected.values()
    ):
        raise ValueError("Expected counts must be nonnegative integers")

    return expected


def validate_pipeline_recovery_evidence_in_transaction(
    connection: duckdb.DuckDBPyConnection,
    run_id: str,
    stage_attempt_id: str,
    batch_id: str,
    expected_rows: Mapping[str, int],
) -> tuple[bool, str]:
    """Validate evidence within a transaction owned by the caller."""

    expected = _validate_inputs(
        run_id, stage_attempt_id, batch_id, expected_rows
    )

    identity = connection.execute(
        """
        SELECT
            p.pipeline_name,
            p.status,
            p.batch_id,
            s.stage_name,
            s.status
        FROM audit.pipeline_runs AS p
        JOIN audit.stage_runs AS s
          ON s.run_id = p.run_id
        WHERE p.run_id = ?
          AND s.stage_attempt_id = ?
        """,
        [run_id, stage_attempt_id],
    ).fetchall()

    if len(identity) != 1:
        return False, "RUN_STAGE_IDENTITY_MISMATCH"

    (
        pipeline_name,
        pipeline_status,
        recorded_batch,
        stage_name,
        stage_status,
    ) = identity[0]

    if (
        pipeline_name != PIPELINE_NAME
        or stage_name != STAGE_NAME
    ):
        return False, "INGESTION_IDENTITY_MISMATCH"

    if (
        pipeline_status != "RUNNING"
        or stage_status != "SUCCESS"
    ):
        return False, "RECOVERY_LIFECYCLE_MISMATCH"

    if recorded_batch != batch_id:
        return False, "PIPELINE_BATCH_MISMATCH"

    stages = connection.execute(
        """
        SELECT stage_attempt_id, stage_name, status
        FROM audit.stage_runs
        WHERE run_id = ?
        """,
        [run_id],
    ).fetchall()

    if stages != [
        (stage_attempt_id, STAGE_NAME, "SUCCESS")
    ]:
        return False, "UNEXPECTED_STAGE_ATTEMPTS"

    reconciliation = connection.execute(
        """
        SELECT
            entity_name,
            batch_id,
            source_rows,
            target_rows,
            difference_rows,
            status
        FROM audit.reconciliation_results
        WHERE run_id = ?
          AND stage_attempt_id = ?
        """,
        [run_id, stage_attempt_id],
    ).fetchall()

    if len(reconciliation) != len(EXPECTED_RAW_TABLES):
        return False, "RECONCILIATION_COUNT_MISMATCH"

    observed_entities = set()

    for (
        entity,
        recorded_batch,
        source_rows,
        target_rows,
        difference,
        status,
    ) in reconciliation:

        if entity not in expected:
            return False, "UNEXPECTED_RECONCILIATION_ENTITY"

        if entity in observed_entities:
            return False, "DUPLICATE_RECONCILIATION_ENTITY"

        observed_entities.add(entity)

        if recorded_batch != batch_id:
            return False, f"RECONCILIATION_BATCH_MISMATCH:{entity}"

        if (
            source_rows != expected[entity]
            or target_rows != expected[entity]
            or difference != 0
            or status != "PASS"
        ):
            return False, f"RECONCILIATION_FAILED:{entity}"

    if observed_entities != set(EXPECTED_RAW_TABLES):
        return False, "RECONCILIATION_COVERAGE_INCOMPLETE"

    quality = connection.execute(
        """
        SELECT status, entity_name
        FROM audit.data_quality_results
        WHERE run_id = ?
          AND stage_attempt_id = ?
          AND test_name = 'raw_batch_integrity'
        """,
        [run_id, stage_attempt_id],
    ).fetchall()

    if quality != [("PASS", None)]:
        return False, "RAW_BATCH_QUALITY_NOT_PASSING"


    return True, "PIPELINE_RECOVERY_EVIDENCE_VERIFIED"


def validate_pipeline_recovery_evidence(
    audit_database: Path,
    run_id: str,
    stage_attempt_id: str,
    batch_id: str,
    expected_rows: Mapping[str, int],
) -> tuple[bool, str]:
    """Validate recovery evidence using a read-only audit snapshot."""

    _validate_inputs(
        run_id, stage_attempt_id, batch_id, expected_rows
    )

    database = Path(audit_database).resolve()

    if not database.is_file():
        return False, "AUDIT_DATABASE_MISSING"

    connection = duckdb.connect(str(database), read_only=True)

    try:
        connection.execute("BEGIN TRANSACTION")

        result = validate_pipeline_recovery_evidence_in_transaction(
            connection=connection,
            run_id=run_id,
            stage_attempt_id=stage_attempt_id,
            batch_id=batch_id,
            expected_rows=expected_rows,
        )

        connection.execute("COMMIT")
        return result

    except BaseException:
        try:
            connection.execute("ROLLBACK")
        except duckdb.Error:
            pass
        raise

    finally:
        connection.close()
