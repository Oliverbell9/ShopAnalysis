"""Synthetic-only ADR-001 tests: no cloud access or deletion."""
import json
from pathlib import Path

import pytest

from ingestion.object_store.protected_batch_governance import (
    AuthorizationError, append_audit_event, validate_owner_deletion_approval,
)


def approval():
    return {"approval_ref": "TICKET-42", "approver_id": "owner-1",
            "environment": "prod", "bucket": "example", "key": "prod/raw/batch",
            "reason": "approved exception"}


def test_matching_owner_approval_is_structurally_valid():
    assert validate_owner_deletion_approval(approval(), owner_id="owner-1",
        environment="prod", bucket="example", key="prod/raw/batch") == "TICKET-42"


@pytest.mark.parametrize("change", [
    {"approver_id": "other"}, {"environment": "ci"}, {"bucket": "other"},
    {"key": "prod/raw/other"}, {"reason": ""}, {"approval_ref": ""},
    {"version_id": "wrong"},
])
def test_approval_rejects_wrong_scope_or_missing_fields(change):
    a = approval() | change
    with pytest.raises(AuthorizationError):
        validate_owner_deletion_approval(a, owner_id="owner-1",
            environment="prod", bucket="example", key="prod/raw/batch")


def test_audit_event_is_durable_jsonl(tmp_path: Path):
    log = tmp_path / "audit.jsonl"
    for outcome in ("ATTEMPTED", "CREATED"):
        append_audit_event(log, operation="PROTECTED_UPLOAD", outcome=outcome,
            bucket="example", key="prod/raw/batch", batch_id="b1", sha256="a" * 64)
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert [row["outcome"] for row in rows] == ["ATTEMPTED", "CREATED"]
    assert all(row["timestamp_utc"] and row["sha256"] == "a" * 64 for row in rows)


def test_audit_missing_directory_fails_closed(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        append_audit_event(tmp_path / "missing" / "audit.jsonl",
            operation="PROTECTED_UPLOAD", outcome="ATTEMPTED",
            bucket="example", key="key", batch_id="b1", sha256="a" * 64)
