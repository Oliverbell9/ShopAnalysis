"""Isolated conditional object-upload regression tests; no cloud or Garage calls."""
from pathlib import Path
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from ingestion.object_store.upload_olist_to_garage import (
    parquet_batch_id, upload_protected,
)

import pyarrow as pa
import pyarrow.parquet as pq


def conflict(status=412, code="PreconditionFailed"):
    return ClientError(
        {"Error": {"Code": code, "Message": "conditional write failed"},
         "ResponseMetadata": {"HTTPStatusCode": status}},
        "PutObject",
    )


def fake_client(existing=None, error=None):
    s3 = Mock()
    if error:
        s3.put_object.side_effect = error

    def get_object(**kwargs):
        data = existing if existing is not None else b"example payload"
        body = Mock()
        body.iter_chunks.return_value = [data]
        return {"Body": body}

    s3.get_object.side_effect = get_object
    return s3


def test_new_object_conditional_create(tmp_path: Path):
    path = tmp_path / "batch.parquet"
    path.write_bytes(b"example payload")
    s3 = fake_client()
    assert upload_protected(s3, "bucket", "key", path, {}) == "CREATED"
    assert s3.put_object.call_args.kwargs["IfNoneMatch"] == "*"


def test_identical_replay_is_noop(tmp_path: Path):
    path = tmp_path / "batch.parquet"
    path.write_bytes(b"example payload")
    s3 = fake_client(error=conflict())
    assert upload_protected(s3, "bucket", "key", path, {}) == "IDENTICAL_REPLAY"
    assert s3.put_object.call_count == 1


def test_conflicting_replay_rejected(tmp_path: Path):
    path = tmp_path / "batch.parquet"
    path.write_bytes(b"new payload")
    s3 = fake_client(existing=b"old payload", error=conflict())
    with pytest.raises(RuntimeError, match="PROTECTED_BATCH_CONFLICT"):
        upload_protected(s3, "bucket", "key", path, {})


def test_unsupported_conditional_write_fails_closed(tmp_path: Path):
    path = tmp_path / "batch.parquet"
    path.write_bytes(b"example payload")
    s3 = fake_client(error=conflict(501, "NotImplemented"))
    with pytest.raises(ClientError):
        upload_protected(s3, "bucket", "key", path, {})
    s3.get_object.assert_not_called()


def test_post_write_content_mismatch_fails(tmp_path: Path):
    path = tmp_path / "batch.parquet"
    path.write_bytes(b"example payload")
    s3 = fake_client(existing=b"incorrect")
    with pytest.raises(RuntimeError, match="REMOTE_CONTENT_MISMATCH"):
        upload_protected(s3, "bucket", "key", path, {})


@pytest.mark.parametrize("values", [["batch-1", None], [None, None], []])
def test_parquet_batch_id_rejects_null_or_empty(tmp_path: Path, values):
    path = tmp_path / "batch.parquet"
    pq.write_table(pa.table({"_batch_id": pa.array(values, type=pa.string())}), path)
    with pytest.raises(RuntimeError, match="_batch_id"):
        parquet_batch_id(path)


def test_parquet_batch_id_accepts_single_nonnull_batch(tmp_path: Path):
    path = tmp_path / "batch.parquet"
    pq.write_table(pa.table({"_batch_id": ["batch-1", "batch-1"]}), path)
    assert parquet_batch_id(path) == "batch-1"


def test_upload_writes_audit_intent_and_outcome(tmp_path: Path):
    import json
    path = tmp_path / "batch.parquet"
    path.write_bytes(b"example payload")
    log = tmp_path / "audit.jsonl"
    s3 = fake_client()
    assert upload_protected(s3, "bucket", "key", path, {"batch-id": "batch-1"},
                            audit_path=log) == "CREATED"
    events = [json.loads(x) for x in log.read_text().splitlines()]
    assert [x["outcome"] for x in events] == ["ATTEMPTED", "CREATED"]


def test_upload_does_not_write_if_audit_unavailable(tmp_path: Path):
    path = tmp_path / "batch.parquet"
    path.write_bytes(b"example payload")
    s3 = fake_client()
    with pytest.raises(FileNotFoundError):
        upload_protected(s3, "bucket", "key", path, {},
                         audit_path=tmp_path / "missing" / "audit.jsonl")
    s3.put_object.assert_not_called()
