from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import duckdb
import pytest

from observability.audit_collector import AuditCollector
from observability.ingestion_config import (
    EXPECTED_RAW_TABLES,
    PIPELINE_NAME,
    STAGE_NAME,
)
from observability.init_observability_db import DDL
from observability.pipeline_recovery_executor import (
    RECOVERY_AUTHORIZATION,
    PipelineRecoveryError,
    recover_committed_pipeline,
)

BATCH = "isolated_recovery_regression"
EXPECTED = {table: 1 for table in EXPECTED_RAW_TABLES}


@pytest.fixture
def recovery_fixture():
    with TemporaryDirectory(
        prefix="shopanalysis_recovery_pytest_"
    ) as directory:
        root = Path(directory)
        raw = root / "isolated_raw.duckdb"
        audit = root / "isolated_audit.duckdb"

        con = duckdb.connect(str(raw))
        try:
            con.execute("CREATE SCHEMA raw")
            for table in EXPECTED_RAW_TABLES:
                con.execute(
                    f'CREATE TABLE raw."{table}" AS '
                    "SELECT ?::VARCHAR AS _batch_id",
                    [BATCH],
                )
        finally:
            con.close()

        con = duckdb.connect(str(audit))
        try:
            for statement in DDL:
                con.execute(statement)
        finally:
            con.close()

        collector = AuditCollector(audit)

        run_id = collector.start_pipeline(
            pipeline_name=PIPELINE_NAME,
            environment="isolated_test",
            batch_id=BATCH,
        )
        stage_id = collector.start_stage(run_id, STAGE_NAME)

        for table in EXPECTED_RAW_TABLES:
            collector.record_reconciliation_result(
                run_id=run_id,
                stage_attempt_id=stage_id,
                entity_name=table,
                source_rows=1,
                target_rows=1,
                batch_id=BATCH,
            )

        collector.record_quality_result(
            run_id=run_id,
            stage_attempt_id=stage_id,
            test_name="raw_batch_integrity",
            status="PASS",
        )

        collector.finish_stage(stage_id, "SUCCESS")

        yield {
            "raw": raw,
            "audit": audit,
            "run_id": run_id,
            "stage_id": stage_id,
            "arguments": {
                "raw_database": raw,
                "audit_database": audit,
                "run_id": run_id,
                "stage_attempt_id": stage_id,
                "batch_id": BATCH,
                "expected_rows": EXPECTED,
                "authorization": RECOVERY_AUTHORIZATION,
            },
        }


def audit_snapshot(fixture):
    con = duckdb.connect(
        str(fixture["audit"]),
        read_only=True,
    )
    try:
        run_id = fixture["run_id"]
        return (
            con.execute(
                """
                SELECT status, ended_at, error_type, error_message
                FROM audit.pipeline_runs
                WHERE run_id = ?
                """,
                [run_id],
            ).fetchone(),
            con.execute(
                """
                SELECT stage_attempt_id, stage_name, status
                FROM audit.stage_runs
                WHERE run_id = ?
                ORDER BY stage_attempt_id
                """,
                [run_id],
            ).fetchall(),
            con.execute(
                """
                SELECT entity_name, source_rows, target_rows,
                       difference_rows, status, batch_id
                FROM audit.reconciliation_results
                WHERE run_id = ?
                ORDER BY entity_name
                """,
                [run_id],
            ).fetchall(),
            con.execute(
                """
                SELECT test_name, status, entity_name
                FROM audit.data_quality_results
                WHERE run_id = ?
                ORDER BY test_name
                """,
                [run_id],
            ).fetchall(),
        )
    finally:
        con.close()


def mutate_audit(fixture, statement, parameters):
    con = duckdb.connect(str(fixture["audit"]))
    try:
        con.execute(statement, parameters)
    finally:
        con.close()


def assert_rejected_without_change(
    fixture,
    expected_message,
    arguments=None,
):
    before = audit_snapshot(fixture)

    with pytest.raises(
        PipelineRecoveryError,
        match="^" + expected_message + "$",
    ):
        recover_committed_pipeline(
            **(
                arguments
                if arguments is not None
                else fixture["arguments"]
            )
        )

    assert audit_snapshot(fixture) == before
    assert before[0][0] == "RUNNING"


def test_missing_authorization_rejected(recovery_fixture):
    fixture = recovery_fixture
    arguments = {
        **fixture["arguments"],
        "authorization": "",
    }

    assert_rejected_without_change(
        fixture,
        "RECOVERY_NOT_AUTHORIZED",
        arguments,
    )


def test_incorrect_raw_batch_rejected(recovery_fixture):
    fixture = recovery_fixture
    arguments = {
        **fixture["arguments"],
        "batch_id": "incorrect_batch",
    }

    assert_rejected_without_change(
        fixture,
        "RAW_VERIFICATION_FAILED:BATCH_MISMATCH:olist_customers",
        arguments,
    )


def test_verified_recovery_finalizes_pipeline(recovery_fixture):
    fixture = recovery_fixture

    result = recover_committed_pipeline(
        **fixture["arguments"]
    )

    assert result == "PIPELINE_RECOVERY_FINALIZED"

    state = audit_snapshot(fixture)

    assert state[0][0] == "SUCCESS"
    assert state[0][1] is not None
    assert state[0][2:] == (None, None)
    assert len(state[1]) == 1
    assert state[1][0][2] == "SUCCESS"
    assert len(state[2]) == len(EXPECTED_RAW_TABLES)
    assert len(state[3]) == 1


def test_second_finalization_rejected(recovery_fixture):
    fixture = recovery_fixture

    recover_committed_pipeline(**fixture["arguments"])
    finalized = audit_snapshot(fixture)

    with pytest.raises(
        PipelineRecoveryError,
        match="^AUDIT_EVIDENCE_REJECTED:RECOVERY_LIFECYCLE_MISMATCH$",
    ):
        recover_committed_pipeline(**fixture["arguments"])

    assert audit_snapshot(fixture) == finalized


def test_missing_reconciliation_rejected(recovery_fixture):
    fixture = recovery_fixture

    mutate_audit(
        fixture,
        """
        DELETE FROM audit.reconciliation_results
        WHERE run_id = ?
          AND stage_attempt_id = ?
          AND entity_name = ?
        """,
        [
            fixture["run_id"],
            fixture["stage_id"],
            EXPECTED_RAW_TABLES[0],
        ],
    )

    assert_rejected_without_change(
        fixture,
        "AUDIT_EVIDENCE_REJECTED:RECONCILIATION_COUNT_MISMATCH",
    )


def test_failed_quality_rejected(recovery_fixture):
    fixture = recovery_fixture

    mutate_audit(
        fixture,
        """
        UPDATE audit.data_quality_results
        SET status = 'FAIL'
        WHERE run_id = ?
          AND stage_attempt_id = ?
          AND test_name = 'raw_batch_integrity'
        """,
        [fixture["run_id"], fixture["stage_id"]],
    )

    assert_rejected_without_change(
        fixture,
        "AUDIT_EVIDENCE_REJECTED:RAW_BATCH_QUALITY_NOT_PASSING",
    )


def test_unexpected_stage_rejected(recovery_fixture):
    fixture = recovery_fixture

    mutate_audit(
        fixture,
        """
        INSERT INTO audit.stage_runs (
            stage_attempt_id,
            run_id,
            stage_name,
            attempt_number,
            started_at,
            status
        )
        VALUES (
            'unexpected-stage',
            ?,
            'unexpected_stage',
            1,
            CURRENT_TIMESTAMP,
            'RUNNING'
        )
        """,
        [fixture["run_id"]],
    )

    assert_rejected_without_change(
        fixture,
        "AUDIT_EVIDENCE_REJECTED:UNEXPECTED_STAGE_ATTEMPTS",
    )


def test_precommit_failure_rolls_back(recovery_fixture):
    fixture = recovery_fixture
    before = audit_snapshot(fixture)

    original_transaction = AuditCollector.transaction

    def injected_transaction(self):
        from contextlib import contextmanager

        @contextmanager
        def wrapper():
            with original_transaction(self) as connection:
                yield connection

                updated = connection.execute(
                    """
                    SELECT status
                    FROM audit.pipeline_runs
                    WHERE run_id = ?
                    """,
                    [fixture["run_id"]],
                ).fetchone()

                assert updated == ("SUCCESS",)

                raise RuntimeError(
                    "INJECTED_PRECOMMIT_FAILURE"
                )

        return wrapper()

    with patch.object(
        AuditCollector,
        "transaction",
        injected_transaction,
    ):
        with pytest.raises(
            RuntimeError,
            match="^INJECTED_PRECOMMIT_FAILURE$",
        ):
            recover_committed_pipeline(
                **fixture["arguments"]
            )

    assert audit_snapshot(fixture) == before
    assert before[0][0] == "RUNNING"
    assert len(before[2]) == len(EXPECTED_RAW_TABLES)
    assert len(before[3]) == 1