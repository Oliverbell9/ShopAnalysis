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
5. Enforces conditional object creation and SHA-256 content verification.
6. Reports a concise PASS summary without exposing credentials.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pyarrow.parquet as pq
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from ingestion.object_store.protected_batch_governance import append_audit_event

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
    values = batch_table.column("_batch_id")
    if len(values) == 0 or values.null_count:
        raise RuntimeError(f"{path.name}: _batch_id contains null values or no rows")
    batch_ids = set(values.to_pylist())

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



def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_remote(s3, bucket: str, key: str) -> str:
    response = s3.get_object(Bucket=bucket, Key=key)
    digest = hashlib.sha256()
    stream = response["Body"]
    try:
        for chunk in stream.iter_chunks(chunk_size=1024 * 1024):
            if chunk:
                digest.update(chunk)
    finally:
        stream.close()
    return digest.hexdigest()


def upload_protected(s3, bucket: str, key: str, path: Path, metadata: dict[str, str],
                     *, audit_path: Path | None = None) -> str:
    """Conditional create only. Unsupported conditional writes fail closed."""
    local_hash = sha256_path(path)
    local_size = path.stat().st_size
    def audit(outcome: str) -> None:
        if audit_path is not None:
            append_audit_event(audit_path, operation="PROTECTED_UPLOAD", outcome=outcome,
                               bucket=bucket, key=key,
                               batch_id=metadata.get("batch-id", "unknown"), sha256=local_hash)
    # Record intent before network activity; if the ledger is unavailable, do not write.
    audit("ATTEMPTED")
    try:
        with path.open("rb") as stream:
            s3.put_object(
                Bucket=bucket, Key=key, Body=stream,
                ContentLength=local_size,
                ContentType="application/vnd.apache.parquet",
                Metadata={**metadata, "sha256": local_hash},
                IfNoneMatch="*",
            )
        outcome = "CREATED"
    except ClientError as exc:
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        code = exc.response.get("Error", {}).get("Code")
        if status not in (409, 412) and code not in ("PreconditionFailed", "ConditionalRequestConflict"):
            raise
        try:
            existing_hash = sha256_remote(s3, bucket, key)
        except ClientError as read_exc:
            raise RuntimeError(f"Cannot verify existing object: {key}") from read_exc
        if existing_hash != local_hash:
            audit("PROTECTED_BATCH_CONFLICT")
            raise RuntimeError(f"PROTECTED_BATCH_CONFLICT: {key}")
        outcome = "IDENTICAL_REPLAY"
    if sha256_remote(s3, bucket, key) != local_hash:
        audit("REMOTE_CONTENT_MISMATCH")
        raise RuntimeError(f"REMOTE_CONTENT_MISMATCH: {key}")
    audit(outcome)
    return outcome


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

    # A writable local ledger is required for this CLI. Set a protected,
    # backed-up directory; this is not a tamper-resistant production audit store.
    audit_dir = PROJECT_ROOT / "data" / "protected_batch_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / "garage_upload.jsonl"

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

        outcome = upload_protected(
            s3, bucket, object_key, path,
            {"source": "olist", "entity": entity,
             "batch-id": batch_id, "ingest-date": ingest_date},
            audit_path=audit_path,
        )
        remote_size = local_size
        print(f"{outcome}: {entity} {object_key}")

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