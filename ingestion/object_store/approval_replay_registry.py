"""Offline, fail-closed approval replay registry; NEVER deletes objects.

The SQLite registry must be held on a durable, access-controlled volume. It is
not a substitute for centrally enforced replay protection across machines.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from ingestion.object_store.governance_evidence import verify_signed_owner_approval
from ingestion.object_store.protected_batch_governance import AuthorizationError


def consume_signed_approval(envelope: dict, *, trusted_public_key: bytes,
                            owner_id: str, environment: str, bucket: str,
                            key: str, registry_path: Path,
                            version_id: str | None = None) -> str:
    """Verify signed exact-scope approval and atomically mark it consumed.

    Call only as an offline authorization exercise. Consumption does not
    authorize, initiate, or guarantee an object deletion.
    """
    approval_ref = verify_signed_owner_approval(
        envelope, trusted_public_key=trusted_public_key, owner_id=owner_id,
        environment=environment, bucket=bucket, key=key, version_id=version_id)
    registry_path = Path(registry_path)
    if not registry_path.parent.is_dir():
        raise FileNotFoundError('Registry parent directory does not exist')
    # An existing registry must not be a symlink or an unexpected directory.
    if registry_path.is_symlink() or (registry_path.exists() and not registry_path.is_file()):
        raise AuthorizationError('Unsafe replay registry path')
    digest = hashlib.sha256(json.dumps(envelope['approval'], sort_keys=True,
        separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()
    try:
        with sqlite3.connect(registry_path, timeout=10, isolation_level=None) as db:
            db.execute('PRAGMA busy_timeout=10000')
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS consumed_approvals ('
                       'approval_ref TEXT PRIMARY KEY, approval_sha256 TEXT NOT NULL)')
            try:
                db.execute('INSERT INTO consumed_approvals (approval_ref, approval_sha256) VALUES (?, ?)',
                           (approval_ref, digest))
            except sqlite3.IntegrityError as exc:
                raise AuthorizationError('Approval reference has already been consumed') from exc
            db.execute('COMMIT')
    except sqlite3.Error as exc:
        raise AuthorizationError('Replay registry unavailable') from exc
    return approval_ref
