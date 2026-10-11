"""Regression tests for RAW Parquet batch lineage integrity."""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from ingestion.duckdb import load_olist_raw as loader


def write_synthetic_parquet(
    path: Path,
    batch_ids: list[str | None],
) -> None:
    """Write synthetic rows with the complete required lineage schema."""

    row_count = len(batch_ids)

    table = pa.table(
        {
            "_batch_id": pa.array(
                batch_ids,
                type=pa.string(),
            ),
            "_source_file": pa.array(
                ["synthetic.csv"] * row_count,
                type=pa.string(),
            ),
            "_file_row_number": pa.array(
                list(range(1, row_count + 1)),
                type=pa.int64(),
            ),
            "_loaded_at": pa.array(
                ["2026-10-10T00:00:00Z"] * row_count,
                type=pa.string(),
            ),
        }
    )

    assert loader.LINEAGE_COLUMNS.issubset(
        set(table.column_names)
    )

    pq.write_table(table, path)


def test_parquet_validation_rejects_mixed_null_batch_ids(
    tmp_path: Path,
) -> None:
    """Null batch IDs must not be hidden by a valid batch ID."""

    parquet_file = tmp_path / "mixed_batch.parquet"

    write_synthetic_parquet(
        parquet_file,
        ["test_batch_001", None],
    )

    with pytest.raises(
        RuntimeError,
        match="(?i)(null|missing batch)",
    ):
        loader.validate_parquet(parquet_file)


def test_parquet_validation_rejects_multiple_batch_ids(
    tmp_path: Path,
) -> None:
    """Different non-null batch IDs must be rejected."""

    parquet_file = tmp_path / "multiple_batches.parquet"

    write_synthetic_parquet(
        parquet_file,
        ["test_batch_001", "test_batch_002"],
    )

    with pytest.raises(
        RuntimeError,
        match="(?i)(multiple|distinct|exactly one)",
    ):
        loader.validate_parquet(parquet_file)


def test_parquet_validation_accepts_consistent_batch_id(
    tmp_path: Path,
) -> None:
    """A valid, consistent batch must remain acceptable."""

    parquet_file = tmp_path / "consistent_batch.parquet"

    write_synthetic_parquet(
        parquet_file,
        ["test_batch_001", "test_batch_001"],
    )

    source_rows, batch_id = loader.validate_parquet(
        parquet_file
    )

    assert source_rows == 2
    assert batch_id == "test_batch_001"
