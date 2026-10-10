"""Controlled execution-history writer for ShopAnalysis observability."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import uuid4

import duckdb

from observability.init_observability_db import DEFAULT_DATABASE


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditCollector:
    def __init__(self, database: Path = DEFAULT_DATABASE):
        self.database = Path(database).resolve()

        if not self.database.is_file():
            raise FileNotFoundError(
                f"Observability database not initialized: {self.database}"
            )

    @contextmanager
    def transaction(self) -> Iterator[duckdb.DuckDBPyConnection]:
        connection = duckdb.connect(str(self.database))

        try:
            connection.execute("BEGIN TRANSACTION")

            try:
                yield connection
                connection.execute("COMMIT")
            except BaseException:
                connection.execute("ROLLBACK")
                raise
        finally:
            connection.close()

    def start_pipeline(
        self,
        pipeline_name: str,
        environment: str,
        batch_id: str | None = None,
    ) -> str:
        if not pipeline_name.strip() or not environment.strip():
            raise ValueError("Pipeline name and environment are required")

        run_id = str(uuid4())

        with self.transaction() as con:
            con.execute(
                """
                INSERT INTO audit.pipeline_runs (
                    run_id, pipeline_name, environment,
                    batch_id, started_at, status
                )
                VALUES (?, ?, ?, ?, ?, 'RUNNING')
                """,
                [
                    run_id,
                    pipeline_name,
                    environment,
                    batch_id,
                    utc_now(),
                ],
            )

        return run_id

    def finish_pipeline(
        self,
        run_id: str,
        status: str,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> None:
        if status not in {"SUCCESS", "FAILED"}:
            raise ValueError("Terminal status must be SUCCESS or FAILED")

        if status == "SUCCESS" and (error_type or error_message):
            raise ValueError("Successful runs cannot contain failure details")

        with self.transaction() as con:
            current = con.execute(
                """
                SELECT status
                FROM audit.pipeline_runs
                WHERE run_id = ?
                """,
                [run_id],
            ).fetchone()

            if current != ("RUNNING",):
                raise ValueError("Pipeline run is missing or already completed")

            active = con.execute(
                """
                SELECT COUNT(*)
                FROM audit.stage_runs
                WHERE run_id = ?
                  AND status = 'RUNNING'
                """,
                [run_id],
            ).fetchone()[0]

            if active:
                raise ValueError(
                    "Cannot finalize pipeline with active stage attempts"
                )

            con.execute(
                """
                UPDATE audit.pipeline_runs
                SET status = ?,
                    ended_at = ?,
                    error_type = ?,
                    error_message = ?
                WHERE run_id = ?
                  AND status = 'RUNNING'
                """,
                [status, utc_now(), error_type, error_message, run_id],
            )

    def start_stage(self, run_id: str, stage_name: str) -> str:
        if not stage_name.strip():
            raise ValueError("Stage name is required")

        stage_attempt_id = str(uuid4())

        with self.transaction() as con:
            pipeline = con.execute(
                """
                SELECT status
                FROM audit.pipeline_runs
                WHERE run_id = ?
                """,
                [run_id],
            ).fetchone()

            if pipeline != ("RUNNING",):
                raise ValueError("Pipeline must be RUNNING")

            previous = con.execute(
                """
                SELECT attempt_number, status
                FROM audit.stage_runs
                WHERE run_id = ?
                  AND stage_name = ?
                ORDER BY attempt_number DESC
                LIMIT 1
                """,
                [run_id, stage_name],
            ).fetchone()

            if previous and previous[1] != "FAILED":
                raise ValueError(
                    "A stage can be retried only after a failed attempt"
                )

            attempt_number = previous[0] + 1 if previous else 1

            con.execute(
                """
                INSERT INTO audit.stage_runs (
                    stage_attempt_id, run_id, stage_name,
                    attempt_number, started_at, status
                )
                VALUES (?, ?, ?, ?, ?, 'RUNNING')
                """,
                [
                    stage_attempt_id,
                    run_id,
                    stage_name,
                    attempt_number,
                    utc_now(),
                ],
            )

        return stage_attempt_id

    def finish_stage(
        self,
        stage_attempt_id: str,
        status: str,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> None:
        if status not in {"SUCCESS", "FAILED"}:
            raise ValueError("Terminal status must be SUCCESS or FAILED")

        if status == "SUCCESS" and (error_type or error_message):
            raise ValueError(
                "Successful stage attempts cannot contain failure details"
            )

        with self.transaction() as con:
            current = con.execute(
                """
                SELECT s.status, p.status
                FROM audit.stage_runs AS s
                JOIN audit.pipeline_runs AS p
                  ON p.run_id = s.run_id
                WHERE s.stage_attempt_id = ?
                """,
                [stage_attempt_id],
            ).fetchone()

            if current != ("RUNNING", "RUNNING"):
                raise ValueError(
                    "Stage or parent pipeline is not RUNNING"
                )

            con.execute(
                """
                UPDATE audit.stage_runs
                SET status = ?,
                    ended_at = ?,
                    error_type = ?,
                    error_message = ?
                WHERE stage_attempt_id = ?
                  AND status = 'RUNNING'
                """,
                [
                    status,
                    utc_now(),
                    error_type,
                    error_message,
                    stage_attempt_id,
                ],
            )
    def record_quality_result(
        self,
        run_id: str,
        stage_attempt_id: str,
        test_name: str,
        status: str,
        entity_name: str | None = None,
        observed_value: str | None = None,
        expected_value: str | None = None,
        details: str | None = None,
    ) -> str:
        if status not in {"PASS", "WARN", "FAIL", "SKIP"}:
            raise ValueError("Invalid quality-result status")

        if not test_name.strip():
            raise ValueError("Test name is required")

        result_id = str(uuid4())

        with self.transaction() as con:
            self._require_active_stage(
                con, run_id, stage_attempt_id
            )

            con.execute(
                """
                INSERT INTO audit.data_quality_results (
                    quality_result_id, run_id, stage_attempt_id,
                    test_name, entity_name, status,
                    observed_value, expected_value,
                    executed_at, details
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    result_id, run_id, stage_attempt_id,
                    test_name, entity_name, status,
                    observed_value, expected_value,
                    utc_now(), details,
                ],
            )

        return result_id

    def record_reconciliation_result(
        self,
        run_id: str,
        stage_attempt_id: str,
        entity_name: str,
        source_rows: int,
        target_rows: int,
        batch_id: str | None = None,
        details: str | None = None,
    ) -> str:
        if not entity_name.strip():
            raise ValueError("Entity name is required")

        if (
            type(source_rows) is not int
            or type(target_rows) is not int
            or source_rows < 0
            or target_rows < 0
        ):
            raise ValueError(
                "Row counts must be nonnegative integers"
            )

        difference = target_rows - source_rows
        status = "PASS" if difference == 0 else "FAIL"
        result_id = str(uuid4())

        with self.transaction() as con:
            self._require_active_stage(
                con, run_id, stage_attempt_id
            )

            con.execute(
                """
                INSERT INTO audit.reconciliation_results (
                    reconciliation_result_id, run_id,
                    stage_attempt_id, entity_name, batch_id,
                    source_rows, target_rows, difference_rows,
                    status, executed_at, details
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    result_id, run_id, stage_attempt_id,
                    entity_name, batch_id,
                    source_rows, target_rows, difference,
                    status, utc_now(), details,
                ],
            )

        return result_id

    @staticmethod
    def _require_active_stage(
        con: duckdb.DuckDBPyConnection,
        run_id: str,
        stage_attempt_id: str,
    ) -> None:
        state = con.execute(
            """
            SELECT s.status, p.status
            FROM audit.stage_runs AS s
            JOIN audit.pipeline_runs AS p
              ON p.run_id = s.run_id
            WHERE s.stage_attempt_id = ?
              AND s.run_id = ?
            """,
            [stage_attempt_id, run_id],
        ).fetchone()

        if state != ("RUNNING", "RUNNING"):
            raise ValueError(
                "Evidence requires an active stage in an active pipeline"
            )
    def record_fault_injection_result(
        self,
        run_id: str,
        stage_attempt_id: str,
        fault_type: str,
        injection_stage: str,
        expected_control: str,
        detected: bool,
        detection_stage: str | None = None,
        detection_time: datetime | None = None,
        blast_radius: str | None = None,
        remediation: str | None = None,
        coverage_gap: str | None = None,
    ) -> str:
        for name, value in (
            ("fault_type", fault_type),
            ("injection_stage", injection_stage),
            ("expected_control", expected_control),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")

        if type(detected) is not bool:
            raise ValueError("detected must be a boolean")

        if detection_time is not None:
            if (
                not isinstance(detection_time, datetime)
                or detection_time.tzinfo is None
                or detection_time.utcoffset() is None
            ):
                raise ValueError(
                    "detection_time must be timezone-aware"
                )

            detection_time = detection_time.astimezone(timezone.utc)

        if not detected and (
            detection_stage is not None
            or detection_time is not None
        ):
            raise ValueError(
                "Undetected faults cannot have detection details"
            )

        result_id = str(uuid4())

        with self.transaction() as con:
            self._require_active_stage(
                con, run_id, stage_attempt_id
            )

            con.execute(
                """
                INSERT INTO audit.fault_injection_results (
                    fault_result_id,
                    run_id,
                    stage_attempt_id,
                    fault_type,
                    injection_stage,
                    expected_control,
                    detected,
                    detection_stage,
                    detection_time,
                    blast_radius,
                    remediation,
                    coverage_gap,
                    executed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    result_id,
                    run_id,
                    stage_attempt_id,
                    fault_type,
                    injection_stage,
                    expected_control,
                    detected,
                    detection_stage,
                    detection_time,
                    blast_radius,
                    remediation,
                    coverage_gap,
                    utc_now(),
                ],
            )

        return result_id
