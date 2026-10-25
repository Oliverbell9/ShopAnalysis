"""Local governance primitives; no cloud deletion capability.

The JSONL ledger is a local durability aid, NOT a tamper-proof audit store.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class AuthorizationError(ValueError):
    """An exceptional-deletion approval is absent or invalid."""


def validate_owner_deletion_approval(approval: dict, *, owner_id: str,
                                     environment: str, bucket: str,
                                     key: str, version_id: str | None = None) -> str:
    """Validate a specific owner's approval; NEVER perform deletion.

    The caller must authenticate the owner and verify approval authenticity
    independently. Matching owner_id strings alone are not authentication.
    """
    if environment not in {"dev", "ci", "prod"}:
        raise AuthorizationError("Unknown environment")
    if not isinstance(approval, dict):
        raise AuthorizationError("Approval must be a record")
    required = ("approval_ref", "approver_id", "environment", "bucket", "key", "reason")
    if any(not isinstance(approval.get(k), str) or not approval[k].strip() for k in required):
        raise AuthorizationError("Incomplete deletion approval")
    expected = {"approver_id": owner_id, "environment": environment,
                "bucket": bucket, "key": key}
    if any(approval.get(k) != v for k, v in expected.items()):
        raise AuthorizationError("Deletion approval does not match requested object or owner")
    if approval.get("version_id") != version_id:
        raise AuthorizationError("Deletion approval does not match object version")
    return approval["approval_ref"]


def append_audit_event(path: Path, *, operation: str, outcome: str,
                       bucket: str, key: str, batch_id: str,
                       sha256: str, actor: str = "garage-uploader",
                       authorization_ref: str | None = None) -> None:
    """Append and fsync one event; errors propagate (fail closed)."""
    if not all(isinstance(v, str) and v for v in
               (operation, outcome, bucket, key, batch_id, sha256, actor)):
        raise ValueError("Incomplete audit event")
    record = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "operation": operation, "outcome": outcome, "bucket": bucket,
              "key": key, "batch_id": batch_id, "sha256": sha256,
              "actor": actor, "authorization_ref": authorization_ref}
    data = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path = Path(path)
    if not path.parent.is_dir():
        raise FileNotFoundError(f"Audit directory does not exist: {path.parent}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        with os.fdopen(fd, "ab", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise
