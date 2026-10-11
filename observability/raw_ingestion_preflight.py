"""Read-only preflight for governed Olist RAW ingestion."""

from __future__ import annotations

from pathlib import Path

import duckdb

from ingestion.duckdb import load_olist_raw as loader
from observability.init_observability_db import DDL


def validate_raw_ingestion_preflight(
    *,
    raw_database: Path,
    audit_database: Path,
    parquet_root: Path,
    environment: str,
) -> str:
    """Validate governed ingestion inputs and return the batch ID."""

    if not isinstance(environment, str) or not environment.strip():
        raise ValueError(
            "Governed RAW ingestion requires a nonblank environment"
        )

    for name, value in (
        ("raw_database", raw_database),
        ("audit_database", audit_database),
        ("parquet_root", parquet_root),
    ):
        if not isinstance(value, Path):
            raise TypeError(f"{name} must be a pathlib.Path")

    raw_database = raw_database.resolve()
    audit_database = audit_database.resolve()
    parquet_root = parquet_root.resolve()

    if raw_database == audit_database:
        raise ValueError(
            "RAW and audit database paths must be different"
        )

    if not parquet_root.is_dir():
        raise FileNotFoundError(
            f"Parquet landing directory not found: {parquet_root}"
        )

    if not audit_database.is_file():
        raise FileNotFoundError(
            f"Audit database not initialized: {audit_database}"
        )

    expected_connection = duckdb.connect(":memory:")

    try:
        for statement in DDL:
            expected_connection.execute(statement)

        actual_connection = duckdb.connect(
            str(audit_database),
            read_only=True,
        )

        try:
            expected_tables = expected_connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'audit'
                  AND table_type = 'BASE TABLE'
                """
            ).fetchall()

            column_query = """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'audit'
                  AND table_name = ?
            """

            for (table_name,) in expected_tables:
                expected_rows = expected_connection.execute(
                    column_query, [table_name]
                ).fetchall()

                actual_rows = actual_connection.execute(
                    column_query, [table_name]
                ).fetchall()

                if not actual_rows:
                    raise RuntimeError(
                        "Audit schema validation failed: "
                        f"missing table audit.{table_name}"
                    )

                expected_metadata = {
                    name: (data_type, nullable)
                    for name, data_type, nullable in expected_rows
                }

                actual_metadata = {
                    name: (data_type, nullable)
                    for name, data_type, nullable in actual_rows
                }

                for column_name, expected_definition in (
                    expected_metadata.items()
                ):
                    actual_definition = actual_metadata.get(
                        column_name
                    )

                    if actual_definition != expected_definition:
                        raise RuntimeError(
                            "Audit schema compatibility failure: "
                            f"audit.{table_name}.{column_name} "
                            f"expected {expected_definition}, "
                            f"found {actual_definition}"
                        )

            constraint_query = """
                SELECT table_name, constraint_type, constraint_text
                FROM duckdb_constraints()
                WHERE schema_name = 'audit'
                  AND constraint_type <> 'NOT NULL'
            """

            expected_constraints = set(
                expected_connection.execute(
                    constraint_query
                ).fetchall()
            )

            actual_constraints = set(
                actual_connection.execute(
                    constraint_query
                ).fetchall()
            )

            missing_constraints = (
                expected_constraints - actual_constraints
            )

            if missing_constraints:
                raise RuntimeError(
                    "Audit schema compatibility failure: "
                    "missing required constraints "
                    f"{sorted(missing_constraints)}"
                )

        finally:
            actual_connection.close()

    finally:
        expected_connection.close()

    discovered = loader.discover_files(parquet_root)

    batch_ids: set[str] = set()

    for _table_name, parquet_path in discovered:
        _source_rows, batch_id = loader.validate_parquet(
            parquet_path
        )
        batch_ids.add(batch_id)

    if len(batch_ids) != 1:
        raise RuntimeError(
            "Governed RAW ingestion requires one consistent "
            "batch ID across all nine Parquet entities"
        )

    return next(iter(batch_ids))
