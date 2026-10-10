"""Read-only evidence validation for governed Olist RAW ingestion."""

from __future__ import annotations

from pathlib import Path

import duckdb

from observability.ingestion_config import EXPECTED_RAW_TABLES


def validate_ingestion_evidence(
    audit_database: Path,
    run_id: str,
    stage_attempt_id: str,
    batch_id: str,
    expected_rows: dict[str, int],
) -> tuple[bool, str]:
    """Validate recorded evidence for one specific RAW ingestion attempt."""

    if not all(
        isinstance(value, str) and value.strip()
        for value in (run_id, stage_attempt_id, batch_id)
    ):
        raise ValueError(
            "Run ID, stage attempt ID, and batch ID are required"
        )

    if set(expected_rows) != set(EXPECTED_RAW_TABLES):
        raise ValueError(
            "Expected counts must cover exactly nine RAW tables"
        )

    if any(
        type(count) is not int or count < 0
        for count in expected_rows.values()
    ):
        raise ValueError(
            "Expected row counts must be nonnegative integers"
        )

    database = Path(audit_database).resolve()

    if not database.is_file():
        return False, "AUDIT_DATABASE_MISSING"

    con = duckdb.connect(str(database), read_only=True)

    try:
        identity = con.execute(
            """
            SELECT p.status, s.status, p.batch_id
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

        pipeline_status, stage_status, recorded_batch = identity[0]

        if (pipeline_status, stage_status) != (
            "RUNNING",
            "RUNNING",
        ):
            return False, "AUDIT_STAGE_NOT_ACTIVE"

        if recorded_batch != batch_id:
            return False, "PIPELINE_BATCH_MISMATCH"

        reconciliation = con.execute(
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

            if entity not in expected_rows:
                return False, "UNEXPECTED_RECONCILIATION_ENTITY"

            if entity in observed_entities:
                return False, "DUPLICATE_RECONCILIATION_ENTITY"

            observed_entities.add(entity)

            if recorded_batch != batch_id:
                return False, f"RECONCILIATION_BATCH_MISMATCH:{entity}"

            expected = expected_rows[entity]

            if (
                source_rows != expected
                or target_rows != expected
                or difference != 0
                or status != "PASS"
            ):
                return False, f"RECONCILIATION_FAILED:{entity}"

        if observed_entities != set(EXPECTED_RAW_TABLES):
            return False, "RECONCILIATION_COVERAGE_INCOMPLETE"

        quality = con.execute(
            """
            SELECT status, entity_name
            FROM audit.data_quality_results
            WHERE run_id = ?
              AND stage_attempt_id = ?
              AND test_name = 'raw_batch_integrity'
            """,
            [run_id, stage_attempt_id],
        ).fetchall()

        if len(quality) != 1:
            return False, "RAW_BATCH_QUALITY_COUNT_MISMATCH"

        quality_status, quality_entity = quality[0]

        if quality_status != "PASS" or quality_entity is not None:
            return False, "RAW_BATCH_QUALITY_NOT_PASSING"

        return True, "INGESTION_EVIDENCE_VERIFIED"

    finally:
        con.close()
