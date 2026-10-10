"""Initialize the isolated ShopAnalysis observability database."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = (
    PROJECT_ROOT / "data" / "shopanalysis_observability.duckdb"
)

DDL = [
    """
    CREATE SCHEMA IF NOT EXISTS audit
    """,
    """
    CREATE TABLE IF NOT EXISTS audit.pipeline_runs (
        run_id VARCHAR PRIMARY KEY,
        pipeline_name VARCHAR NOT NULL,
        environment VARCHAR NOT NULL,
        batch_id VARCHAR,
        started_at TIMESTAMPTZ NOT NULL,
        ended_at TIMESTAMPTZ,
        status VARCHAR NOT NULL
            CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED')),
        error_type VARCHAR,
        error_message VARCHAR,
        CHECK (ended_at IS NULL OR ended_at >= started_at),
        CHECK (
            (status = 'RUNNING' AND ended_at IS NULL)
            OR
            (status IN ('SUCCESS', 'FAILED') AND ended_at IS NOT NULL)
        )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit.stage_runs (
        stage_attempt_id VARCHAR PRIMARY KEY,
        run_id VARCHAR NOT NULL
            REFERENCES audit.pipeline_runs(run_id),
        stage_name VARCHAR NOT NULL,
        attempt_number INTEGER NOT NULL
            CHECK (attempt_number >= 1),
        started_at TIMESTAMPTZ NOT NULL,
        ended_at TIMESTAMPTZ,
        status VARCHAR NOT NULL
            CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED')),
        error_type VARCHAR,
        error_message VARCHAR,
        UNIQUE (run_id, stage_name, attempt_number),
        CHECK (ended_at IS NULL OR ended_at >= started_at),
        CHECK (
            (status = 'RUNNING' AND ended_at IS NULL)
            OR
            (status IN ('SUCCESS', 'FAILED') AND ended_at IS NOT NULL)
        )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit.data_quality_results (
        quality_result_id VARCHAR PRIMARY KEY,
        run_id VARCHAR NOT NULL
            REFERENCES audit.pipeline_runs(run_id),
        stage_attempt_id VARCHAR
            REFERENCES audit.stage_runs(stage_attempt_id),
        test_name VARCHAR NOT NULL,
        entity_name VARCHAR,
        status VARCHAR NOT NULL
            CHECK (status IN ('PASS', 'WARN', 'FAIL', 'SKIP')),
        observed_value VARCHAR,
        expected_value VARCHAR,
        executed_at TIMESTAMPTZ NOT NULL,
        details VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit.reconciliation_results (
        reconciliation_result_id VARCHAR PRIMARY KEY,
        run_id VARCHAR NOT NULL
            REFERENCES audit.pipeline_runs(run_id),
        stage_attempt_id VARCHAR
            REFERENCES audit.stage_runs(stage_attempt_id),
        entity_name VARCHAR NOT NULL,
        batch_id VARCHAR,
        source_rows BIGINT,
        target_rows BIGINT,
        difference_rows BIGINT,
        status VARCHAR NOT NULL
            CHECK (status IN ('PASS', 'FAIL')),
        executed_at TIMESTAMPTZ NOT NULL,
        details VARCHAR,
        CHECK (source_rows IS NULL OR source_rows >= 0),
        CHECK (target_rows IS NULL OR target_rows >= 0)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit.fault_injection_results (
        fault_result_id VARCHAR PRIMARY KEY,
        run_id VARCHAR NOT NULL
            REFERENCES audit.pipeline_runs(run_id),
        stage_attempt_id VARCHAR
            REFERENCES audit.stage_runs(stage_attempt_id),
        fault_type VARCHAR NOT NULL,
        injection_stage VARCHAR NOT NULL,
        expected_control VARCHAR NOT NULL,
        detected BOOLEAN NOT NULL,
        detection_stage VARCHAR,
        detection_time TIMESTAMPTZ,
        blast_radius VARCHAR,
        remediation VARCHAR,
        coverage_gap VARCHAR,
        executed_at TIMESTAMPTZ NOT NULL
    )
    """,
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
    )
    args = parser.parse_args()

    database = args.database.resolve()
    database.parent.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect(str(database))

    try:
        connection.execute("BEGIN TRANSACTION")

        try:
            for statement in DDL:
                connection.execute(statement)

            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise

        tables = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'audit'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        ).fetchall()

        expected = {
            "pipeline_runs",
            "stage_runs",
            "data_quality_results",
            "reconciliation_results",
            "fault_injection_results",
        }

        actual = {row[0] for row in tables}

        if not expected.issubset(actual):
            raise RuntimeError(
                f"Missing audit tables: {sorted(expected - actual)}"
            )

        print("OBSERVABILITY SCHEMA: PASS")
        print(f"Database: {database}")
        print(f"Schema: audit")
        print(f"Required tables verified: {len(expected)}")

        for table_name in sorted(expected):
            print(f"  audit.{table_name}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()
