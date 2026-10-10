"""Load governed Olist Parquet landing files into DuckDB RAW.

The loader creates the permanent local RAW warehouse representation of the
validated Olist Parquet landing.

Design:
- Source: data/parquet/olist/*.parquet
- Target database: DUCKDB_PATH from .env
- Target schema: raw
- Target tables: raw.olist_<entity>
- Load semantics: deterministic CREATE OR REPLACE
- Lineage columns are preserved unchanged
- Source and target row counts are reconciled after every load
- All tables in one run must contain one common deterministic batch ID
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pyarrow.parquet as pq
from dotenv import load_dotenv
from observability.ingestion_result import RawIngestionResult

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARQUET_ROOT = PROJECT_ROOT / "data" / "parquet" / "olist"

EXPECTED_ENTITIES = {
    "olist_customers_dataset": "customers",
    "olist_geolocation_dataset": "geolocation",
    "olist_order_items_dataset": "order_items",
    "olist_order_payments_dataset": "payments",
    "olist_order_reviews_dataset": "reviews",
    "olist_orders_dataset": "orders",
    "olist_products_dataset": "products",
    "olist_sellers_dataset": "sellers",
    "product_category_name_translation": "translation",
}

LINEAGE_COLUMNS = {
    "_source_file",
    "_file_row_number",
    "_loaded_at",
    "_batch_id",
}


def required_env(name: str) -> str:
    """Return a required environment variable."""
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")

    return value


def resolve_database_path() -> Path:
    """Resolve DUCKDB_PATH relative to the project root when necessary."""
    configured = Path(required_env("DUCKDB_PATH"))

    if configured.is_absolute():
        return configured

    return PROJECT_ROOT / configured


def discover_files(parquet_root: Path | None = None) -> list[tuple[str, Path]]:
    """Discover exactly one Parquet file for every expected Olist entity."""
    root = PARQUET_ROOT if parquet_root is None else Path(parquet_root)

    if not root.is_dir():
        raise RuntimeError(f"Parquet landing directory not found: {root}")

    discovered = sorted(root.glob("*.parquet"))

    if len(discovered) != len(EXPECTED_ENTITIES):
        raise RuntimeError(
            f"Expected {len(EXPECTED_ENTITIES)} Olist Parquet files, "
            f"found {len(discovered)}"
        )

    result: list[tuple[str, Path]] = []
    seen_stems: set[str] = set()

    for path in discovered:
        stem = path.stem

        if stem not in EXPECTED_ENTITIES:
            raise RuntimeError(f"Unexpected Parquet file: {path.name}")

        if stem in seen_stems:
            raise RuntimeError(f"Duplicate Parquet entity: {stem}")

        seen_stems.add(stem)
        result.append((EXPECTED_ENTITIES[stem], path))

    missing = set(EXPECTED_ENTITIES) - seen_stems

    if missing:
        raise RuntimeError(
            "Missing expected Parquet entities: " + ", ".join(sorted(missing))
        )

    return result


def validate_parquet(path: Path) -> tuple[int, str]:
    """Validate required lineage and return source row count and batch ID."""
    parquet_file = pq.ParquetFile(path)
    columns = set(parquet_file.schema_arrow.names)

    missing_lineage = LINEAGE_COLUMNS - columns

    if missing_lineage:
        raise RuntimeError(
            f"{path.name}: missing lineage columns: "
            + ", ".join(sorted(missing_lineage))
        )

    source_rows = parquet_file.metadata.num_rows

    batch_table = pq.read_table(path, columns=["_batch_id"])
    batch_ids = set(batch_table.column("_batch_id").to_pylist())
    batch_ids.discard(None)

    if len(batch_ids) != 1:
        raise RuntimeError(
            f"{path.name}: expected exactly one non-null _batch_id, "
            f"found {len(batch_ids)}"
        )

    batch_id = next(iter(batch_ids))

    if not isinstance(batch_id, str) or not batch_id.strip():
        raise RuntimeError(f"{path.name}: invalid _batch_id")

    return source_rows, batch_id


def quote_sql_string(value: str) -> str:
    """Escape a string for use as a DuckDB SQL string literal."""
    return value.replace("'", "''")


def main(
    database_path: Path | None = None,
    parquet_root: Path | None = None,
    commit_tracker: "CommitTracker | None" = None,
) -> RawIngestionResult:
    """Load and reconcile Olist entities and return committed-load metadata."""
    if commit_tracker is not None:
        from observability.commit_state import CommitTracker

        if not isinstance(commit_tracker, CommitTracker):
            raise TypeError("commit_tracker must be a CommitTracker instance")

    load_dotenv(PROJECT_ROOT / ".env")

    database_path = (
        resolve_database_path()
        if database_path is None
        else Path(database_path).resolve()
    )
    database_path.parent.mkdir(parents=True, exist_ok=True)

    files = discover_files(parquet_root)

    validated: list[tuple[str, Path, int, str]] = []

    for entity, path in files:
        source_rows, batch_id = validate_parquet(path)
        validated.append((entity, path, source_rows, batch_id))

    batch_ids = {batch_id for _, _, _, batch_id in validated}

    if len(batch_ids) != 1:
        raise RuntimeError(
            f"Expected one batch ID across all entities, found {len(batch_ids)}"
        )

    common_batch_id = next(iter(batch_ids))

    connection = duckdb.connect(str(database_path))

    results: list[tuple[str, int, int]] = []

    try:
        connection.execute("CREATE SCHEMA IF NOT EXISTS raw")

        connection.execute("BEGIN TRANSACTION")

        try:
            for entity, path, source_rows, _ in validated:
                table_name = f"olist_{entity}"
                parquet_path = quote_sql_string(path.resolve().as_posix())

                connection.execute(
                    f"""
                    CREATE OR REPLACE TABLE raw.{table_name} AS
                    SELECT *
                    FROM read_parquet('{parquet_path}')
                    """
                )

                target_rows = connection.execute(
                    f"SELECT COUNT(*) FROM raw.{table_name}"
                ).fetchone()[0]

                if target_rows != source_rows:
                    raise RuntimeError(
                        f"{entity}: row-count reconciliation failed "
                        f"(source={source_rows}, target={target_rows})"
                    )

                target_batch_ids = connection.execute(
                    f"""
                    SELECT DISTINCT _batch_id
                    FROM raw.{table_name}
                    WHERE _batch_id IS NOT NULL
                    """
                ).fetchall()

                if target_batch_ids != [(common_batch_id,)]:
                    raise RuntimeError(
                        f"{entity}: DuckDB batch-ID reconciliation failed"
                    )

                results.append((entity, source_rows, target_rows))

            if commit_tracker is not None:
                commit_tracker.uncertain()

            connection.execute("COMMIT")

            if commit_tracker is not None:
                commit_tracker.committed()

        except Exception:
            if commit_tracker is None or (
                commit_tracker.state.value != "COMMITTED"
            ):
                try:
                    connection.execute("ROLLBACK")
                except Exception:
                    pass
                else:
                    if commit_tracker is not None:
                        commit_tracker.rolled_back()
            raise

    finally:
        connection.close()

    print("DUCKDB OLIST RAW LOAD: PASS")
    print(f"Database:       {database_path}")
    print("Schema:         raw")
    print(f"Batch ID:       {common_batch_id}")
    print(f"Tables loaded:  {len(results)}")
    print(f"Source rows:    {sum(x[1] for x in results):,}")
    print(f"Target rows:    {sum(x[2] for x in results):,}")
    print()
    print("RECONCILIATION")

    for entity, source_rows, target_rows in results:
        status = "PASS" if source_rows == target_rows else "FAIL"
        print(
            f"{entity:15} "
            f"source={source_rows:>10,} "
            f"target={target_rows:>10,} "
            f"{status}"
        )

    return RawIngestionResult(
        database_path=database_path,
        batch_id=common_batch_id,
        source_rows={
            f"olist_{entity}": source_rows
            for entity, source_rows, _ in results
        },
    )

if __name__ == "__main__":
    main()