"""Upload validated Olist Parquet files to Garage S3-compatible storage.

Object layout:

raw/olist/<entity>/ingest_date=YYYY-MM-DD/
    batch_id=<deterministic_batch_id>/part-00000.parquet

The ingest date is derived at runtime in UTC. The batch ID is read from the
validated _batch_id lineage column embedded in each Parquet file.

The script:
1. Loads Garage configuration from the local .env file.
2. Discovers the Olist Parquet landing files.
3. Validates lineage and batch consistency before uploading.
4. Uploads each entity using deterministic S3 object keys.
5. Verifies uploaded object metadata and size.
6. Reports a concise PASS summary without exposing credentials.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pyarrow.parquet as pq
from dotenv import load_dotenv

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


def required_env(name: str) -> str:
    """Return a required environment variable without logging its value."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


def parquet_batch_id(path: Path) -> str:
    """Read and validate the single deterministic batch ID in a Parquet file."""
    parquet_file = pq.ParquetFile(path)

    if "_batch_id" not in parquet_file.schema_arrow.names:
        raise RuntimeError(f"{path.name}: _batch_id lineage column is missing")

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

    return batch_id


def discover_files() -> list[tuple[str, Path]]:
    """Discover exactly one expected Parquet file for each Olist entity."""
    if not PARQUET_ROOT.is_dir():
        raise RuntimeError(f"Parquet landing directory not found: {PARQUET_ROOT}")

    discovered = sorted(PARQUET_ROOT.glob("*.parquet"))

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


def main() -> None:
    """Validate and upload the Olist Parquet landing to Garage."""
    load_dotenv(PROJECT_ROOT / ".env")

    endpoint = required_env("GARAGE_ENDPOINT")
    region = required_env("GARAGE_REGION")
    bucket = required_env("GARAGE_BUCKET")
    access_key = required_env("GARAGE_ACCESS_KEY_ID")
    secret_key = required_env("GARAGE_SECRET_ACCESS_KEY")

    files = discover_files()

    batch_ids = {parquet_batch_id(path) for _, path in files}

    if len(batch_ids) != 1:
        raise RuntimeError(
            f"Expected one batch ID across all entities, found {len(batch_ids)}"
        )

    batch_id = next(iter(batch_ids))

    # Physical ingestion partition: runtime UTC date.
    ingest_date = datetime.now(timezone.utc).date().isoformat()

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    uploaded: list[tuple[str, str, int]] = []

    for entity, path in files:
        object_key = (
            f"raw/olist/{entity}/"
            f"ingest_date={ingest_date}/"
            f"batch_id={batch_id}/"
            "part-00000.parquet"
        )

        local_size = path.stat().st_size

        s3.upload_file(
            str(path),
            bucket,
            object_key,
            ExtraArgs={
                "ContentType": "application/vnd.apache.parquet",
                "Metadata": {
                    "source": "olist",
                    "entity": entity,
                    "batch-id": batch_id,
                    "ingest-date": ingest_date,
                },
            },
        )

        head = s3.head_object(Bucket=bucket, Key=object_key)
        remote_size = head["ContentLength"]

        if remote_size != local_size:
            raise RuntimeError(
                f"{entity}: uploaded size mismatch "
                f"(local={local_size}, remote={remote_size})"
            )

        uploaded.append((entity, object_key, remote_size))

    print("GARAGE OLIST UPLOAD: PASS")
    print(f"Bucket:           {bucket}")
    print(f"Ingest date UTC:  {ingest_date}")
    print(f"Batch ID:         {batch_id}")
    print(f"Objects uploaded: {len(uploaded)}")
    print(f"Bytes uploaded:   {sum(size for _, _, size in uploaded):,}")
    print()
    print("OBJECTS")

    for entity, object_key, size in uploaded:
        print(f"{entity:15} {size:>12,}  {object_key}")


if __name__ == "__main__":
    main()