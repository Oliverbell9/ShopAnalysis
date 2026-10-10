"""Regression tests for pre-execution governed ingestion identity validation."""

from pathlib import Path

import pytest

import observability.governed_ingestion as governed
from observability.ingestion_config import PIPELINE_NAME, STAGE_NAME


@pytest.mark.parametrize(
    ("pipeline_name", "stage_name"),
    [
        ("incorrect_pipeline", STAGE_NAME),
        (PIPELINE_NAME, "incorrect_stage"),
    ],
)
def test_invalid_identity_rejected_before_audit_or_raw(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    pipeline_name: str,
    stage_name: str,
) -> None:
    events = []

    def forbidden_audit_collector(database: Path):
        events.append("audit")
        raise AssertionError("AuditCollector must not be initialized")

    def forbidden_raw_action(tracker):
        events.append("raw")
        raise AssertionError("RAW action must not execute")

    monkeypatch.setattr(
        governed,
        "AuditCollector",
        forbidden_audit_collector,
    )

    with pytest.raises(ValueError, match="Unexpected"):
        governed.execute_governed_ingestion(
            action=forbidden_raw_action,
            audit_database=tmp_path / "unused_audit.duckdb",
            pipeline_name=pipeline_name,
            environment="test",
            stage_name=stage_name,
            batch_id="isolated_identity_test",
        )

    assert events == []


def test_valid_identity_reaches_audit_initialization(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events = []

    class AuditInitializationReached(Exception):
        pass

    def intercept_audit_collector(database: Path):
        events.append("audit")
        raise AuditInitializationReached

    def forbidden_raw_action(tracker):
        events.append("raw")
        raise AssertionError("RAW action must not execute")

    monkeypatch.setattr(
        governed,
        "AuditCollector",
        intercept_audit_collector,
    )

    with pytest.raises(AuditInitializationReached):
        governed.execute_governed_ingestion(
            action=forbidden_raw_action,
            audit_database=tmp_path / "unused_audit.duckdb",
            pipeline_name=PIPELINE_NAME,
            environment="test",
            stage_name=STAGE_NAME,
            batch_id="isolated_identity_test",
        )

    assert events == ["audit"]
