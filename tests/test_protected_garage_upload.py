"""Isolated conditional object-upload regression tests; no cloud or Garage calls."""
from pathlib import Path
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from ingestion.object_store.upload_olist_to_garage import upload_protected


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
