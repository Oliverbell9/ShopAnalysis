"""Synthetic tests for the read-only benchmark evidence wrapper."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from analytics.performance_evidence import build_evidence, main


class FakeConnection:
    def execute(self, query):
        return self

    def fetchall(self):
        return [(1,)]


def test_evidence_contains_query_fingerprints_and_method(tmp_path):
    db = tmp_path / "existing.duckdb"
    db.write_bytes(b"synthetic fixture")
    report = build_evidence(FakeConnection(), db_path=db, repetitions=2, duckdb_version="test")
    assert report["status"] == "MEASURED_LOCAL_ONLY"
    assert report["environment"]["database_bytes"] == len(b"synthetic fixture")
    assert report["method"]["warmup_runs_per_query"] == 1
    assert set(report["measurements"]) == {"delivered_kpis", "monthly_mart"}
    for item in report["measurements"].values():
        assert len(item["query_sha256"]) == 64
        assert item["repetitions"] == 2
        assert item["min_ms"] <= item["median_ms"] <= item["max_ms"]


@pytest.mark.parametrize("count", [0, -1, 101])
def test_invalid_repetitions_rejected(tmp_path, count):
    db = tmp_path / "existing.duckdb"
    db.touch()
    with pytest.raises(ValueError):
        build_evidence(FakeConnection(), db_path=db, repetitions=count, duckdb_version="test")


def test_missing_db_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_evidence(FakeConnection(), db_path=tmp_path / "missing.duckdb", repetitions=1,
                       duckdb_version="test")


def test_cli_rejects_existing_report_without_overwriting(tmp_path):
    db = tmp_path / "existing.duckdb"
    db.touch()
    output = tmp_path / "report.json"
    output.write_text("protected", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main(["--db", str(db), "--output", str(output)])
    assert error.value.code == 2
    assert output.read_text(encoding="utf-8") == "protected"


def test_cli_rejects_missing_database(tmp_path):
    with pytest.raises(SystemExit) as error:
        main(["--db", str(tmp_path / "missing.duckdb")])
    assert error.value.code == 2
