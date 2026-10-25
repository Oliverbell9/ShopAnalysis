"""Offline ADR-001 evidence verification. No object deletion or cloud operations.

Approval verification uses a separately trusted Ed25519 public key. The signing
private key must remain outside the repository and the running uploader.
Audit sealing uses an externally managed HMAC key and an append-only sequence;
without independently retained checkpoints, truncation remains undetectable.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ingestion.object_store.protected_batch_governance import (
    AuthorizationError, validate_owner_deletion_approval,
)


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def verify_signed_owner_approval(envelope: dict, *, trusted_public_key: bytes,
                                 owner_id: str, environment: str, bucket: str,
                                 key: str, version_id: str | None = None) -> str:
    """Verify a pinned owner's signature AND the exact object scope. Never delete."""
    if not isinstance(envelope, dict) or set(envelope) != {"approval", "signature_b64"}:
        raise AuthorizationError("Invalid signed approval envelope")
    approval = envelope["approval"]
    if not isinstance(approval, dict) or not isinstance(envelope["signature_b64"], str):
        raise AuthorizationError("Invalid signed approval content")
    try:
        signature = base64.b64decode(envelope["signature_b64"], validate=True)
        Ed25519PublicKey.from_public_bytes(trusted_public_key).verify(signature, _canonical(approval))
    except (ValueError, TypeError, InvalidSignature) as exc:
        raise AuthorizationError("Owner approval signature verification failed") from exc
    return validate_owner_deletion_approval(approval, owner_id=owner_id,
        environment=environment, bucket=bucket, key=key, version_id=version_id)


def seal_audit_file(source: Path, destination: Path, *, hmac_key: bytes) -> dict:
    """Seal a stable snapshot of JSONL events; destination must not already exist."""
    if not isinstance(hmac_key, bytes) or len(hmac_key) < 32:
        raise ValueError("Audit HMAC key must contain at least 32 bytes")
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError("Audit source and seal destination must differ")
    raw = source.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise ValueError("Audit JSONL must be nonempty and newline-terminated")
    events = raw.splitlines()
    for event in events:
        if not isinstance(json.loads(event), dict):
            raise ValueError("Audit event must be a JSON object")
    record = {"schema": 1, "event_count": len(events),
              "sha256": hashlib.sha256(raw).hexdigest()}
    record["hmac_sha256"] = hmac.new(hmac_key, _canonical(record), hashlib.sha256).hexdigest()
    with destination.open("x", encoding="utf-8", newline="\n") as output:
        output.write(_canonical(record).decode("utf-8") + "\n")
    return record


def verify_audit_seal(source: Path, seal: Path, *, hmac_key: bytes) -> bool:
    """Verify a sealed snapshot. An independently retained seal is required."""
    if not isinstance(hmac_key, bytes) or len(hmac_key) < 32:
        raise ValueError("Audit HMAC key must contain at least 32 bytes")
    record = json.loads(Path(seal).read_text(encoding="utf-8"))
    if not isinstance(record, dict) or set(record) != {"schema", "event_count", "sha256", "hmac_sha256"}:
        raise ValueError("Invalid audit seal")
    signature = record["hmac_sha256"]
    payload = {k: v for k, v in record.items() if k != "hmac_sha256"}
    if not isinstance(signature, str) or not hmac.compare_digest(
        signature, hmac.new(hmac_key, _canonical(payload), hashlib.sha256).hexdigest()):
        raise ValueError("Audit seal authentication failed")
    raw = Path(source).read_bytes()
    if not hmac.compare_digest(record["sha256"], hashlib.sha256(raw).hexdigest()):
        raise ValueError("Audit content changed after sealing")
    if not raw.endswith(b"\n") or len(raw.splitlines()) != record["event_count"]:
        raise ValueError("Audit record count or termination changed")
    for line in raw.splitlines():
        if not isinstance(json.loads(line), dict):
            raise ValueError("Invalid audit event")
    return True
