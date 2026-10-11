"""Isolated governed RAW ingestion preflight regression tests."""

from pathlib import Path

import pytest

from ingestion.duckdb import load_olist_raw as loader


def test_preflight_rejects_missing_parquet_directory(
    tmp_path: Path,
) -> None:
    """Missing sources must not create RAW or audit databases."""

    from observability.raw_ingestion_preflight import (
        validate_raw_ingestion_preflight,
    )

    raw_database = tmp_path / "raw" / "warehouse.duckdb"
    audit_database = tmp_path / "audit" / "observability.duckdb"

    with pytest.raises(
        (FileNotFoundError, RuntimeError, ValueError),
    ):
        validate_raw_ingestion_preflight(
            raw_database=raw_database,
            audit_database=audit_database,
            parquet_root=tmp_path / "missing_parquet",
            environment="test",
        )

    assert not raw_database.exists()
    assert not audit_database.exists()
    assert not raw_database.parent.exists()
    assert not audit_database.parent.exists()


def test_preflight_rejects_blank_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid execution identity must fail before source discovery."""

    from observability.raw_ingestion_preflight import (
        validate_raw_ingestion_preflight,
    )

    def forbidden_discovery(*args, **kwargs):
        pytest.fail("Blank environment reached source discovery")

    monkeypatch.setattr(loader, "discover_files", forbidden_discovery)

    with pytest.raises(
        ValueError,
        match="(?i)environment",
    ):
        validate_raw_ingestion_preflight(
            raw_database=tmp_path / "raw.duckdb",
            audit_database=tmp_path / "audit.duckdb",
            parquet_root=tmp_path / "parquet",
            environment="   ",
        )


def test_preflight_rejects_identical_database_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RAW and audit databases must remain isolated."""

    from observability.raw_ingestion_preflight import (
        validate_raw_ingestion_preflight,
    )

    def forbidden_discovery(*args, **kwargs):
        pytest.fail("Identical database paths reached source discovery")

    monkeypatch.setattr(loader, "discover_files", forbidden_discovery)

    database = tmp_path / "shared.duckdb"

    with pytest.raises(
        ValueError,
        match="(?i)(database|path|same|identical)",
    ):
        validate_raw_ingestion_preflight(
            raw_database=database,
            audit_database=database,
            parquet_root=tmp_path / "parquet",
            environment="test",
        )

    assert not database.exists()
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from ingestion.duckdb import load_olist_raw as loader
from observability.raw_ingestion_preflight import (
    validate_raw_ingestion_preflight,
)


def create_entity_files(
    root: Path,
    *,
    inconsistent_batch: bool = False,
) -> None:
    root.mkdir(parents=True, exist_ok=True)

    for index, entity in enumerate(sorted(loader.EXPECTED_ENTITIES)):
        batch_id = (
            "test_batch_other"
            if inconsistent_batch and index == 0
            else "test_batch_001"
        )

        table = pa.table(
            {
                "_batch_id": [batch_id],
                "_source_file": [f"{entity}.csv"],
                "_file_row_number": [1],
                "_loaded_at": ["2026-10-10T00:00:00Z"],
            }
        )

        pq.write_table(table, root / f"{entity}.parquet")


def create_audit_database(path: Path) -> None:
    import duckdb

    from observability.init_observability_db import DDL

    connection = duckdb.connect(str(path))
    try:
        connection.execute("BEGIN TRANSACTION")
        try:
            for statement in DDL:
                connection.execute(statement)
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
    finally:
        connection.close()


def test_preflight_rejects_incomplete_entity_set(
    tmp_path: Path,
) -> None:
    parquet_root = tmp_path / "parquet"
    parquet_root.mkdir()

    audit_database = tmp_path / "observability.duckdb"
    create_audit_database(audit_database)

    with pytest.raises(RuntimeError, match="(?i)(entity|files|expected)"):
        validate_raw_ingestion_preflight(
            raw_database=tmp_path / "raw.duckdb",
            audit_database=audit_database,
            parquet_root=parquet_root,
            environment="test",
        )

    assert not (tmp_path / "raw.duckdb").exists()


def test_preflight_rejects_inconsistent_entity_batches(
    tmp_path: Path,
) -> None:
    parquet_root = tmp_path / "parquet"
    create_entity_files(parquet_root, inconsistent_batch=True)

    audit_database = tmp_path / "observability.duckdb"
    create_audit_database(audit_database)

    with pytest.raises(RuntimeError, match="(?i)batch"):
        validate_raw_ingestion_preflight(
            raw_database=tmp_path / "raw.duckdb",
            audit_database=audit_database,
            parquet_root=parquet_root,
            environment="test",
        )

    assert not (tmp_path / "raw.duckdb").exists()


def test_preflight_accepts_consistent_nine_entity_batch(
    tmp_path: Path,
) -> None:
    parquet_root = tmp_path / "parquet"
    create_entity_files(parquet_root)

    audit_database = tmp_path / "observability.duckdb"
    create_audit_database(audit_database)

    validate_raw_ingestion_preflight(
        raw_database=tmp_path / "raw.duckdb",
        audit_database=audit_database,
        parquet_root=parquet_root,
        environment="test",
    )

    assert not (tmp_path / "raw.duckdb").exists()
import duckdb
import pytest
from pathlib import Path

from observability.raw_ingestion_preflight import (
    validate_raw_ingestion_preflight,
)


def test_preflight_rejects_missing_audit_tables(
    tmp_path: Path,
) -> None:
    parquet_root = tmp_path / "parquet"
    create_entity_files(parquet_root)

    audit_database = tmp_path / "observability.duckdb"

    connection = duckdb.connect(str(audit_database))
    connection.close()

    raw_database = tmp_path / "raw.duckdb"

    with pytest.raises(
        RuntimeError,
        match="(?i)(audit|schema|table)",
    ):
        validate_raw_ingestion_preflight(
            raw_database=raw_database,
            audit_database=audit_database,
            parquet_root=parquet_root,
            environment="test",
        )

    assert not raw_database.exists()


def test_preflight_rejects_missing_audit_column(
    tmp_path: Path,
) -> None:
    parquet_root = tmp_path / "parquet"
    create_entity_files(parquet_root)

    audit_database = tmp_path / "observability.duckdb"

    connection = duckdb.connect(str(audit_database))
    try:
        connection.execute("CREATE SCHEMA audit")
        connection.execute(
            "CREATE TABLE audit.pipeline_runs ("
            "run_id VARCHAR PRIMARY KEY, "
            "pipeline_name VARCHAR NOT NULL, "
            "started_at TIMESTAMPTZ NOT NULL, "
            "status VARCHAR NOT NULL)"
        )
    finally:
        connection.close()

    raw_database = tmp_path / "raw.duckdb"

    with pytest.raises(
        RuntimeError,
        match="(?i)(audit|schema|column|environment)",
    ):
        validate_raw_ingestion_preflight(
            raw_database=raw_database,
            audit_database=audit_database,
            parquet_root=parquet_root,
            environment="test",
        )

    assert not raw_database.exists()


def _create_modified_audit_database(
    path: Path,
    *,
    original: str,
    replacement: str,
) -> None:
    from observability.init_observability_db import DDL

    statements = list(DDL)
    matches = sum(statement.count(original) for statement in statements)

    if matches != 1:
        raise RuntimeError(
            f"Expected exactly one DDL replacement; found {matches}"
        )

    connection = duckdb.connect(str(path))
    try:
        for statement in statements:
            connection.execute(
                statement.replace(original, replacement, 1)
            )
    finally:
        connection.close()


def test_preflight_rejects_audit_column_type(
    tmp_path: Path,
) -> None:
    parquet_root = tmp_path / "parquet"
    create_entity_files(parquet_root)

    audit_database = tmp_path / "observability.duckdb"

    _create_modified_audit_database(
        audit_database,
        original="batch_id VARCHAR,\n        started_at TIMESTAMPTZ NOT NULL,",
        replacement="batch_id VARCHAR,\n        started_at TIMESTAMP NOT NULL,",
    )

    raw_database = tmp_path / "raw.duckdb"

    with pytest.raises(
        RuntimeError,
        match="(?i)(audit|schema|type|source_rows)",
    ):
        validate_raw_ingestion_preflight(
            raw_database=raw_database,
            audit_database=audit_database,
            parquet_root=parquet_root,
            environment="test",
        )

    assert not raw_database.exists()


def test_preflight_rejects_audit_nullability(
    tmp_path: Path,
) -> None:
    parquet_root = tmp_path / "parquet"
    create_entity_files(parquet_root)

    audit_database = tmp_path / "observability.duckdb"

    _create_modified_audit_database(
        audit_database,
        original="environment VARCHAR NOT NULL,",
        replacement="environment VARCHAR,",
    )

    raw_database = tmp_path / "raw.duckdb"

    with pytest.raises(
        RuntimeError,
        match="(?i)(audit|schema|null|environment)",
    ):
        validate_raw_ingestion_preflight(
            raw_database=raw_database,
            audit_database=audit_database,
            parquet_root=parquet_root,
            environment="test",
        )

    assert not raw_database.exists()


def test_preflight_rejects_missing_audit_primary_key(
    tmp_path: Path,
) -> None:
    parquet_root = tmp_path / "parquet"
    create_entity_files(parquet_root)

    audit_database = tmp_path / "observability.duckdb"

    _create_modified_audit_database(
        audit_database,
        original="fault_result_id VARCHAR PRIMARY KEY,",
        replacement="fault_result_id VARCHAR NOT NULL,",
    )

    raw_database = tmp_path / "raw.duckdb"

    with pytest.raises(
        RuntimeError,
        match="(?i)(audit|schema|constraint|primary)",
    ):
        validate_raw_ingestion_preflight(
            raw_database=raw_database,
            audit_database=audit_database,
            parquet_root=parquet_root,
            environment="test",
        )

    assert not raw_database.exists()



def test_preflight_returns_validated_batch_id(
    tmp_path: Path,
) -> None:
    parquet_root = tmp_path / "parquet"
    create_entity_files(parquet_root)

    audit_database = tmp_path / "observability.duckdb"
    create_audit_database(audit_database)

    raw_database = tmp_path / "raw.duckdb"

    batch_id = validate_raw_ingestion_preflight(
        raw_database=raw_database,
        audit_database=audit_database,
        parquet_root=parquet_root,
        environment="test",
    )

    assert batch_id == "test_batch_001"
    assert not raw_database.exists()
