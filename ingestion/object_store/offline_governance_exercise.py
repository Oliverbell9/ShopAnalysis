"""Offline, non-deleting governance exercise with explicit irreversible registry consumption.

Only run with synthetic approval credentials and disposable registry/audit paths.
There is deliberately no S3 client or deletion executor in this module.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ingestion.object_store.approval_replay_registry import consume_signed_approval
from ingestion.object_store.governance_evidence import seal_audit_file, verify_audit_seal
from ingestion.object_store.protected_batch_governance import append_audit_event


def exercise(*, envelope: dict, trusted_public_key: bytes, owner_id: str,
             environment: str, bucket: str, key: str, registry_path: Path,
             audit_path: Path, seal_path: Path, hmac_key: bytes,
             version_id: str | None = None) -> dict:
    """Consume a synthetic signed approval, audit it, seal it, verify it.

    Registry consumption is permanent for that registry; failure after consumption
    requires investigation, never an automatic retry. No deletion occurs.
    """
    registry_path, audit_path, seal_path = map(Path, (registry_path, audit_path, seal_path))
    if len({p.resolve() for p in (registry_path, audit_path, seal_path)}) != 3:
        raise ValueError('Registry, audit and seal paths must be distinct')
    if audit_path.exists() or seal_path.exists():
        raise FileExistsError('Exercise requires new audit and seal paths')
    if not audit_path.parent.is_dir() or not seal_path.parent.is_dir():
        raise FileNotFoundError('Exercise output directories must exist')
    if not isinstance(hmac_key, bytes) or len(hmac_key) < 32:
        raise ValueError('HMAC key must contain at least 32 bytes')
    ref = consume_signed_approval(
        envelope, trusted_public_key=trusted_public_key, owner_id=owner_id,
        environment=environment, bucket=bucket, key=key,
        registry_path=registry_path, version_id=version_id)
    digest = hashlib.sha256(json.dumps(envelope['approval'], sort_keys=True,
        separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    append_audit_event(audit_path, operation='OFFLINE_APPROVAL_EXERCISE',
                       outcome='APPROVAL_CONSUMED_NO_DELETION', bucket=bucket,
                       key=key, batch_id='NOT_APPLICABLE', sha256=digest,
                       actor='offline-governance-exercise', authorization_ref=ref)
    seal_audit_file(audit_path, seal_path, hmac_key=hmac_key)
    verify_audit_seal(audit_path, seal_path, hmac_key=hmac_key)
    return {'status': 'PASS', 'approval_ref': ref,
            'registry_consumed': True, 'audit_seal_verified': True,
            'object_deletion_performed': False}
