"""Mandatory governance enforcement regression tests."""

from pathlib import Path

import pytest

from ingestion.duckdb import load_olist_raw as loader


def test_direct_raw_loader_call_is_rejected_before_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct calls must not reach source discovery or database creation."""

    database = tmp_path / "must_not_exist" / "raw.duckdb"
    parquet_root = tmp_path / "must_not_be_read"

    def forbidden_discovery(*args, **kwargs):
        pytest.fail("Unauthorized call reached Parquet discovery")

    def forbidden_connect(*args, **kwargs):
        pytest.fail("Unauthorized call reached DuckDB connection")

    monkeypatch.setattr(loader, "discover_files", forbidden_discovery)
    monkeypatch.setattr(loader.duckdb, "connect", forbidden_connect)

    with pytest.raises(
        PermissionError,
        match="govern",
    ):
        loader.main(
            database_path=database,
            parquet_root=parquet_root,
        )

    assert not database.exists()
    assert not database.parent.exists()



def test_internal_token_without_commit_tracker_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authorization without commit tracking must not reach RAW operations."""

    database = tmp_path / "must_not_exist" / "raw.duckdb"

    def forbidden_discovery(*args, **kwargs):
        pytest.fail("Missing CommitTracker reached source discovery")

    monkeypatch.setattr(loader, "discover_files", forbidden_discovery)

    with pytest.raises(
        (PermissionError, TypeError, ValueError),
        match="(?i)(govern|commit.tracker|commit tracker)",
    ):
        loader.main(
            database_path=database,
            parquet_root=tmp_path / "parquet",
            _governance_token=loader._GOVERNANCE_TOKEN,
        )

    assert not database.exists()
    assert not database.parent.exists()


def test_invalid_commit_tracker_is_rejected_before_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An arbitrary object must not substitute for CommitTracker."""

    database = tmp_path / "must_not_exist" / "raw.duckdb"

    def forbidden_discovery(*args, **kwargs):
        pytest.fail("Invalid CommitTracker reached source discovery")

    monkeypatch.setattr(loader, "discover_files", forbidden_discovery)

    with pytest.raises(
        (PermissionError, TypeError, ValueError),
        match="(?i)(govern|commit.tracker|commit tracker)",
    ):
        loader.main(
            database_path=database,
            parquet_root=tmp_path / "parquet",
            commit_tracker=object(),
            _governance_token=loader._GOVERNANCE_TOKEN,
        )

    assert not database.exists()
    assert not database.parent.exists()
