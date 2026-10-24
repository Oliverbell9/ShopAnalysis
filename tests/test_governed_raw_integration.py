"""Isolated end-to-end governed RAW ingestion integration test."""

from pathlib import Path

import duckdb
from test_raw_ingestion_preflight import create_entity_files

from ingestion.duckdb import load_olist_raw as loader
from observability.governed_raw_entrypoint import (
    run_governed_raw_ingestion,
)
from observability.ingestion_config import (
    PIPELINE_NAME,
    STAGE_NAME,
)
from observability.init_observability_db import DDL


def test_governed_raw_ingestion_end_to_end(
    tmp_path: Path,
) -> None:
    parquet_root = tmp_path / "parquet"
    raw_database = tmp_path / "isolated_warehouse.duckdb"
    audit_database = tmp_path / "observability.duckdb"

    create_entity_files(parquet_root)

    connection = duckdb.connect(str(audit_database))

    try:
        for statement in DDL:
            connection.execute(statement)
    finally:
        connection.close()

    result = run_governed_raw_ingestion(
        raw_database=raw_database,
        audit_database=audit_database,
        parquet_root=parquet_root,
        environment="test",
    )

    assert result.database_path == raw_database.resolve()
    assert result.batch_id == "test_batch_001"

    expected_tables = {
        f"olist_{entity}"
        for entity in loader.EXPECTED_ENTITIES.values()
    }

    assert set(result.source_rows) == expected_tables
    assert all(
        row_count == 1
        for row_count in result.source_rows.values()
    )

    connection = duckdb.connect(
        str(raw_database),
        read_only=True,
    )

    try:
        for table_name in sorted(expected_tables):
            row_count, batch_id = connection.execute(
                f"""
                SELECT COUNT(*), MIN(_batch_id)
                FROM raw.{table_name}
                """
            ).fetchone()

            assert row_count == 1
            assert batch_id == "test_batch_001"
    finally:
        connection.close()

    connection = duckdb.connect(
        str(audit_database),
        read_only=True,
    )

    try:
        pipeline_rows = connection.execute(
            """
            SELECT run_id, status
            FROM audit.pipeline_runs
            WHERE pipeline_name = ?
              AND environment = ?
              AND batch_id = ?
            """,
            [
                PIPELINE_NAME,
                "test",
                "test_batch_001",
            ],
        ).fetchall()

        assert len(pipeline_rows) == 1

        run_id, pipeline_status = pipeline_rows[0]

        assert pipeline_status == "SUCCESS"

        stage_rows = connection.execute(
            """
            SELECT stage_attempt_id, status
            FROM audit.stage_runs
            WHERE run_id = ?
              AND stage_name = ?
            """,
            [run_id, STAGE_NAME],
        ).fetchall()

        assert len(stage_rows) == 1

        stage_attempt_id, stage_status = stage_rows[0]

        assert stage_status == "SUCCESS"

    finally:
        connection.close()

    connection = duckdb.connect(
        str(audit_database),
        read_only=True,
    )

    try:
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

        assert len(reconciliation) == 9

        observed_entities = set()

        for (
            entity,
            recorded_batch,
            source_rows,
            target_rows,
            difference,
            status,
        ) in reconciliation:
            assert entity not in observed_entities
            observed_entities.add(entity)

            assert entity in result.source_rows
            assert recorded_batch == result.batch_id
            assert source_rows == result.source_rows[entity]
            assert target_rows == result.source_rows[entity]
            assert difference == 0
            assert status == "PASS"

        assert observed_entities == expected_tables

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

        assert quality == [("PASS", None)]

    finally:
        connection.close()
