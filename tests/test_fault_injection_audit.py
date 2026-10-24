from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pytest

from observability.audit_collector import AuditCollector
from observability.init_observability_db import DDL


SCORECARD_SQL = (
    Path(__file__).resolve().parents[1]
    / "observability"
    / "scorecard.sql"
)


@pytest.fixture
def audit_env(tmp_path):
    database = tmp_path / "fault_audit.duckdb"

    with duckdb.connect(str(database)) as con:
        con.execute("BEGIN TRANSACTION")
        try:
            for statement in DDL:
                con.execute(statement)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

    collector = AuditCollector(database)
    run_id = collector.start_pipeline(
        "fault_test_pipeline",
        "isolated_test",
    )
    stage_id = collector.start_stage(run_id, "fault_test_stage")

    return database, collector, run_id, stage_id


def count_faults(database):
    with duckdb.connect(str(database), read_only=True) as con:
        return con.execute(
            "SELECT COUNT(*) FROM audit.fault_injection_results"
        ).fetchone()[0]


def test_detected_fault_is_persisted(audit_env):
    database, collector, run_id, stage_id = audit_env

    result_id = collector.record_fault_injection_result(
        run_id=run_id,
        stage_attempt_id=stage_id,
        fault_type="SIMULATED_FAILURE",
        injection_stage="fault_test_stage",
        expected_control="Detect simulated failure",
        detected=True,
        detection_stage="fault_test_stage",
        detection_time=datetime.now(timezone.utc),
    )

    with duckdb.connect(str(database), read_only=True) as con:
        row = con.execute(
            """
            SELECT detected, detection_stage, detection_time
            FROM audit.fault_injection_results
            WHERE fault_result_id = ?
            """,
            [result_id],
        ).fetchone()

    assert row is not None
    assert row[0] is True
    assert row[1] == "fault_test_stage"
    assert row[2] is not None


def test_undetected_fault_is_persisted(audit_env):
    database, collector, run_id, stage_id = audit_env

    collector.record_fault_injection_result(
        run_id=run_id,
        stage_attempt_id=stage_id,
        fault_type="SIMULATED_UNDETECTED",
        injection_stage="fault_test_stage",
        expected_control="Detect simulated failure",
        detected=False,
    )

    assert count_faults(database) == 1


@pytest.mark.parametrize(
    "invalid_value",
    ["true", 1, None],
)
def test_nonboolean_detection_rejected(audit_env, invalid_value):
    database, collector, run_id, stage_id = audit_env

    with pytest.raises(ValueError):
        collector.record_fault_injection_result(
            run_id=run_id,
            stage_attempt_id=stage_id,
            fault_type="SIMULATED_FAILURE",
            injection_stage="fault_test_stage",
            expected_control="Detect simulated failure",
            detected=invalid_value,
        )

    assert count_faults(database) == 0


def test_naive_detection_time_rejected(audit_env):
    database, collector, run_id, stage_id = audit_env

    with pytest.raises(ValueError):
        collector.record_fault_injection_result(
            run_id=run_id,
            stage_attempt_id=stage_id,
            fault_type="SIMULATED_FAILURE",
            injection_stage="fault_test_stage",
            expected_control="Detect simulated failure",
            detected=True,
            detection_time=datetime(2026, 1, 1),
        )

    assert count_faults(database) == 0


def test_undetected_fault_cannot_have_detection_details(audit_env):
    database, collector, run_id, stage_id = audit_env

    with pytest.raises(ValueError):
        collector.record_fault_injection_result(
            run_id=run_id,
            stage_attempt_id=stage_id,
            fault_type="SIMULATED_FAILURE",
            injection_stage="fault_test_stage",
            expected_control="Detect simulated failure",
            detected=False,
            detection_stage="fault_test_stage",
        )

    assert count_faults(database) == 0


def test_completed_stage_rejects_fault_evidence(audit_env):
    database, collector, run_id, stage_id = audit_env

    collector.finish_stage(stage_id, "SUCCESS")

    with pytest.raises(ValueError):
        collector.record_fault_injection_result(
            run_id=run_id,
            stage_attempt_id=stage_id,
            fault_type="SIMULATED_FAILURE",
            injection_stage="fault_test_stage",
            expected_control="Detect simulated failure",
            detected=True,
        )

    assert count_faults(database) == 0


def test_database_failure_rolls_back(audit_env, monkeypatch):
    database, collector, run_id, stage_id = audit_env

    original = collector._require_active_stage

    def inject_failure(con, run, stage):
        original(con, run, stage)
        con.execute(
            """
            INSERT INTO audit.fault_injection_results (
                fault_result_id, run_id, stage_attempt_id,
                fault_type, injection_stage, expected_control,
                detected, executed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                "temporary-fault",
                run,
                stage,
                "SIMULATED",
                "fault_test_stage",
                "Rollback check",
                True,
                datetime.now(timezone.utc),
            ],
        )
        raise RuntimeError("INJECTED_AUDIT_FAILURE")

    monkeypatch.setattr(
        collector,
        "_require_active_stage",
        inject_failure,
    )

    with pytest.raises(RuntimeError, match="INJECTED_AUDIT_FAILURE"):
        collector.record_fault_injection_result(
            run_id=run_id,
            stage_attempt_id=stage_id,
            fault_type="SIMULATED_FAILURE",
            injection_stage="fault_test_stage",
            expected_control="Detect simulated failure",
            detected=True,
        )

    assert count_faults(database) == 0


def test_scorecard_fault_detection_rate(audit_env):
    database, collector, run_id, stage_id = audit_env

    for detected in (True, False):
        collector.record_fault_injection_result(
            run_id=run_id,
            stage_attempt_id=stage_id,
            fault_type="SIMULATED_FAILURE",
            injection_stage="fault_test_stage",
            expected_control="Detect simulated failure",
            detected=detected,
        )

    collector.finish_stage(stage_id, "SUCCESS")
    collector.finish_pipeline(run_id, "SUCCESS")

    with duckdb.connect(str(database)) as con:
        con.execute(SCORECARD_SQL.read_text(encoding="utf-8"))

        pipeline = con.execute(
            """
            SELECT fault_injections, detected_faults
            FROM audit.v_pipeline_run_scorecard
            WHERE run_id = ?
            """,
            [run_id],
        ).fetchone()

        historical = con.execute(
            """
            SELECT fault_injections, detected_faults,
                   fault_detection_rate
            FROM audit.v_historical_scorecard
            WHERE pipeline_name = 'fault_test_pipeline'
              AND environment = 'isolated_test'
            """
        ).fetchone()

    assert pipeline == (2, 1)
    assert historical == (2, 1, 0.5)
