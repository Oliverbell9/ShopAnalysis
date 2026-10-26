"""AWS S3 protected upload adapter. No CLI or implicit network activity.

The caller must supply an authenticated S3 client, bucket, files and audit path.
Only invoke against AWS after separate authorization for cloud writes.
"""

from __future__ import annotations

from pathlib import Path

from ingestion.object_store.upload_olist_to_garage import (
    discover_files,
    parquet_batch_id,
)
from ingestion.object_store.aws_legal_hold import upload_aws_legal_hold


def upload_olist_batch_to_aws(
    s3,
    *,
    bucket: str,
    ingest_date: str,
    audit_path: Path,
    files: list[tuple[str, Path]] | None = None,
    environment: str,
) -> list[tuple[str, str]]:
    """Upload one validated batch using the shared conditional-write contract.

    Object layout includes the environment prefix required by AWS IAM.
    This is a callable adapter, not a deployable or automatically executed job.
    """
    if environment not in {"dev", "ci", "prod"}:
        raise ValueError("environment must be dev, ci, or prod")
    if not bucket or not bucket.strip():
        raise ValueError("bucket must be nonempty")
    from datetime import date

    if date.fromisoformat(ingest_date).isoformat() != ingest_date:
        raise ValueError("ingest_date must be YYYY-MM-DD")
    if audit_path is None:
        raise ValueError("audit_path is mandatory")
    if files is None:
        files = discover_files()
    if not files:
        raise ValueError("no files provided")
    batch_ids = {parquet_batch_id(path) for _, path in files}
    if len(batch_ids) != 1:
        raise RuntimeError("Expected exactly one batch ID across entities")
    batch_id = next(iter(batch_ids))
    outcomes = []
    for entity, path in files:
        if not entity or "/" in entity or ".." in entity:
            raise ValueError("invalid entity")
        key = (
            f"{environment}/raw/olist/{entity}/ingest_date={ingest_date}/"
            f"batch_id={batch_id}/part-00000.parquet"
        )
        outcome = upload_aws_legal_hold(
            s3, bucket, key, path,
            {"source": "olist", "entity": entity,
             "batch-id": batch_id, "ingest-date": ingest_date,
             "environment": environment},
            audit_path=audit_path,
        )
        outcomes.append((key, outcome))
    return outcomes
