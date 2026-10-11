"""Mandatory governed entry point for Olist RAW ingestion."""

from __future__ import annotations

from pathlib import Path

from ingestion.duckdb import load_olist_raw as loader
from observability.governed_ingestion import (
    execute_governed_ingestion,
)
from observability.ingestion_config import (
    PIPELINE_NAME,
    STAGE_NAME,
)
from observability.ingestion_result import RawIngestionResult
from observability.raw_ingestion_preflight import (
    validate_raw_ingestion_preflight,
)


def run_governed_raw_ingestion(
    *,
    raw_database: Path,
    audit_database: Path,
    parquet_root: Path,
    environment: str,
) -> RawIngestionResult:
    """Validate inputs before executing governed RAW ingestion."""

    batch_id = validate_raw_ingestion_preflight(
        raw_database=raw_database,
        audit_database=audit_database,
        parquet_root=parquet_root,
        environment=environment,
    )

    def load_with_governance(commit_tracker):
        return loader.main(
            database_path=raw_database,
            parquet_root=parquet_root,
            commit_tracker=commit_tracker,
            _governance_token=loader._GOVERNANCE_TOKEN,
        )

    return execute_governed_ingestion(
        action=load_with_governance,
        audit_database=audit_database,
        pipeline_name=PIPELINE_NAME,
        environment=environment,
        stage_name=STAGE_NAME,
        batch_id=batch_id,
    )
