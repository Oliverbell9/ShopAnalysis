"""Contract tests for the mandatory governed RAW entry point."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from ingestion.duckdb import load_olist_raw as loader
from observability import governed_raw_entrypoint as entrypoint


def test_entrypoint_rejects_invalid_environment_before_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = Mock(
        side_effect=AssertionError("Coordinator must not run")
    )
    raw_loader = Mock(
        side_effect=AssertionError("RAW loader must not run")
    )

    monkeypatch.setattr(
        entrypoint,
        "execute_governed_ingestion",
        coordinator,
    )
    monkeypatch.setattr(loader, "main", raw_loader)

    with pytest.raises(ValueError, match="environment"):
        entrypoint.run_governed_raw_ingestion(
            raw_database=tmp_path / "raw.duckdb",
            audit_database=tmp_path / "audit.duckdb",
            parquet_root=tmp_path / "parquet",
            environment="",
        )

    coordinator.assert_not_called()
    raw_loader.assert_not_called()


def test_entrypoint_propagates_validated_batch_and_explicit_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_database = tmp_path / "raw.duckdb"
    audit_database = tmp_path / "audit.duckdb"
    parquet_root = tmp_path / "parquet"

    expected_result = object()
    tracker = object()

    preflight = Mock(return_value="test_batch_001")
    raw_loader = Mock(return_value=expected_result)

    def fake_coordinator(**kwargs):
        assert kwargs["audit_database"] == audit_database
        assert kwargs["pipeline_name"] == "olist_raw_ingestion"
        assert kwargs["stage_name"] == "load_olist_raw"
        assert kwargs["environment"] == "test"
        assert kwargs["batch_id"] == "test_batch_001"
        return kwargs["action"](tracker)

    coordinator = Mock(side_effect=fake_coordinator)

    monkeypatch.setattr(
        entrypoint,
        "validate_raw_ingestion_preflight",
        preflight,
    )
    monkeypatch.setattr(
        entrypoint,
        "execute_governed_ingestion",
        coordinator,
    )
    monkeypatch.setattr(loader, "main", raw_loader)

    result = entrypoint.run_governed_raw_ingestion(
        raw_database=raw_database,
        audit_database=audit_database,
        parquet_root=parquet_root,
        environment="test",
    )

    assert result is expected_result

    preflight.assert_called_once_with(
        raw_database=raw_database,
        audit_database=audit_database,
        parquet_root=parquet_root,
        environment="test",
    )

    raw_loader.assert_called_once_with(
        database_path=raw_database,
        parquet_root=parquet_root,
        commit_tracker=tracker,
        _governance_token=loader._GOVERNANCE_TOKEN,
    )

    coordinator.assert_called_once()



def test_entrypoint_rejects_invalid_audit_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import duckdb
    from test_raw_ingestion_preflight import create_entity_files

    parquet_root = tmp_path / "parquet"
    create_entity_files(parquet_root)

    audit_database = tmp_path / "observability.duckdb"
    connection = duckdb.connect(str(audit_database))
    connection.close()

    raw_database = tmp_path / "raw.duckdb"

    coordinator = Mock(
        side_effect=AssertionError("Coordinator must not run")
    )
    raw_loader = Mock(
        side_effect=AssertionError("RAW loader must not run")
    )

    monkeypatch.setattr(
        entrypoint,
        "execute_governed_ingestion",
        coordinator,
    )
    monkeypatch.setattr(loader, "main", raw_loader)

    with pytest.raises(RuntimeError, match="(?i)(audit|schema|table)"):
        entrypoint.run_governed_raw_ingestion(
            raw_database=raw_database,
            audit_database=audit_database,
            parquet_root=parquet_root,
            environment="test",
        )

    coordinator.assert_not_called()
    raw_loader.assert_not_called()
    assert not raw_database.exists()


def test_entrypoint_rejects_inconsistent_parquet_batches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from test_raw_ingestion_preflight import (
        create_audit_database,
        create_entity_files,
    )

    parquet_root = tmp_path / "parquet"
    create_entity_files(
        parquet_root,
        inconsistent_batch=True,
    )

    audit_database = tmp_path / "observability.duckdb"
    create_audit_database(audit_database)

    raw_database = tmp_path / "raw.duckdb"

    coordinator = Mock(
        side_effect=AssertionError("Coordinator must not run")
    )
    raw_loader = Mock(
        side_effect=AssertionError("RAW loader must not run")
    )

    monkeypatch.setattr(
        entrypoint,
        "execute_governed_ingestion",
        coordinator,
    )
    monkeypatch.setattr(loader, "main", raw_loader)

    with pytest.raises(RuntimeError, match="(?i)(batch|consistent)"):
        entrypoint.run_governed_raw_ingestion(
            raw_database=raw_database,
            audit_database=audit_database,
            parquet_root=parquet_root,
            environment="test",
        )

    coordinator.assert_not_called()
    raw_loader.assert_not_called()
    assert not raw_database.exists()
