"""Fail-closed coordinator tests for pretransaction failures."""

from pathlib import Path
from unittest.mock import Mock

import pytest

import observability.governed_ingestion as governed
from observability.commit_state import CommitState


class InjectedPretransactionFailure(RuntimeError):
    pass


def test_pretransaction_failure_preserves_unresolved_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collector = Mock()
    collector.start_pipeline.return_value = "test_run_id"
    collector.start_stage.return_value = "test_stage_id"

    collector_factory = Mock(return_value=collector)

    monkeypatch.setattr(
        governed,
        "AuditCollector",
        collector_factory,
    )

    observed_states = []

    def failing_raw_action(tracker):
        observed_states.append(tracker.state)

        raise InjectedPretransactionFailure(
            "INJECTED_PRETRANSACTION_FAILURE"
        )

    with pytest.raises(
        governed.GovernedIngestionError,
        match="not confirmed rolled back",
    ) as captured:
        governed.execute_governed_ingestion(
            action=failing_raw_action,
            audit_database=tmp_path / "unused_audit.duckdb",
            pipeline_name="olist_raw_ingestion",
            environment="test",
            stage_name="load_olist_raw",
            batch_id="isolated_pretransaction_test",
        )

    assert observed_states == [CommitState.NOT_COMMITTED]

    assert isinstance(
        captured.value.__cause__,
        InjectedPretransactionFailure,
    )

    collector_factory.assert_called_once_with(
        tmp_path / "unused_audit.duckdb"
    )

    collector.start_pipeline.assert_called_once()
    collector.start_stage.assert_called_once()

    collector.finish_stage.assert_not_called()
    collector.finish_pipeline.assert_not_called()

    collector.record_reconciliation_result.assert_not_called()
    collector.record_quality_result.assert_not_called()
