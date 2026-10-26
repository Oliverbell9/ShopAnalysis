"""Offline adapter tests: no AWS calls."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ingestion.object_store.upload_olist_to_aws import upload_olist_batch_to_aws


@pytest.fixture
def fixture_args(tmp_path):
    f = tmp_path / "sample.parquet"
    f.write_bytes(b"synthetic")
    return dict(s3=Mock(), bucket="test-bucket", ingest_date="2026-10-24",
                audit_path=tmp_path / "audit.jsonl", files=[("orders", f)],
                environment="ci")


def test_aws_adapter_uses_shared_protected_upload(fixture_args):
    with patch("ingestion.object_store.upload_olist_to_aws.parquet_batch_id", return_value="batch123"), \
         patch("ingestion.object_store.upload_olist_to_aws.upload_aws_legal_hold", return_value="CREATED") as uploader:
        result = upload_olist_batch_to_aws(**fixture_args)
    key = "ci/raw/olist/orders/ingest_date=2026-10-24/batch_id=batch123/part-00000.parquet"
    assert result == [(key, "CREATED")]
    assert uploader.call_args.args[:3] == (fixture_args["s3"], "test-bucket", key)
    assert uploader.call_args.kwargs["audit_path"] == fixture_args["audit_path"]


@pytest.mark.parametrize("environment", ["dev", "ci", "prod"])
def test_environment_prefix(fixture_args, environment):
    fixture_args["environment"] = environment
    with patch("ingestion.object_store.upload_olist_to_aws.parquet_batch_id", return_value="batch123"), \
         patch("ingestion.object_store.upload_olist_to_aws.upload_aws_legal_hold", return_value="IDENTICAL_REPLAY") as uploader:
        result = upload_olist_batch_to_aws(**fixture_args)
    assert result[0][0].startswith(environment + "/raw/")
    assert result[0][1] == "IDENTICAL_REPLAY"
    assert uploader.called


@pytest.mark.parametrize("invalid", ["production", "", "DEV"])
def test_reject_unknown_environment(fixture_args, invalid):
    fixture_args["environment"] = invalid
    with pytest.raises(ValueError, match="environment"):
        upload_olist_batch_to_aws(**fixture_args)


def test_reject_cross_file_batch_mismatch(fixture_args, tmp_path):
    f = tmp_path / "second.parquet"
    f.write_bytes(b"synthetic2")
    fixture_args["files"].append(("payments", f))
    with patch("ingestion.object_store.upload_olist_to_aws.parquet_batch_id", side_effect=["one", "two"]), \
         patch("ingestion.object_store.upload_olist_to_aws.upload_aws_legal_hold") as uploader:
        with pytest.raises(RuntimeError, match="one batch ID"):
            upload_olist_batch_to_aws(**fixture_args)
    uploader.assert_not_called()


def test_reject_missing_audit_path(fixture_args):
    fixture_args["audit_path"] = None
    with pytest.raises(ValueError, match="audit_path"):
        upload_olist_batch_to_aws(**fixture_args)


def test_propagates_protected_conflict(fixture_args):
    with patch("ingestion.object_store.upload_olist_to_aws.parquet_batch_id", return_value="batch123"), \
         patch("ingestion.object_store.upload_olist_to_aws.upload_aws_legal_hold", side_effect=RuntimeError("PROTECTED_BATCH_CONFLICT")):
        with pytest.raises(RuntimeError, match="PROTECTED_BATCH_CONFLICT"):
            upload_olist_batch_to_aws(**fixture_args)
