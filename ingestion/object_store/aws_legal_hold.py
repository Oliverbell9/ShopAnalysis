
"""Version-aware AWS S3 protected upload with legal hold on creation.

This module does not construct clients or initiate network activity on import.
The caller must provide an authenticated AWS S3 client and authorized target.

Protected upload behavior:
- Create objects with legal hold ON.
- Prevent overwriting an existing current object using IfNoneMatch='*'.
- Verify the exact S3 version returned by the upload.
- Verify legal hold and SHA-256 content integrity.
- Accept replay only for identical, legally held current versions.
- Record upload, verification, replay, and conflict audit outcomes.
- Fail closed when protection or content cannot be verified.

IMPORTANT:
A failed verification or audit operation after put_object succeeds may
leave an object in S3. Such failures require reconciliation before retry.
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from botocore.exceptions import ClientError

from ingestion.object_store.protected_batch_governance import (
    append_audit_event,
)


def _digests(path: Path) -> tuple[str, str, int]:
    """Calculate SHA-256, base64 MD5, and file size."""

    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    size = 0

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            sha256.update(chunk)
            md5.update(chunk)
            size += len(chunk)

    return (
        sha256.hexdigest(),
        base64.b64encode(md5.digest()).decode("ascii"),
        size,
    )


def _remote_sha256(
    s3,
    bucket: str,
    key: str,
    version_id: str,
) -> str:
    """Calculate SHA-256 for one specific S3 object version."""

    response = s3.get_object(
        Bucket=bucket,
        Key=key,
        VersionId=version_id,
    )

    stream = response["Body"]
    digest = hashlib.sha256()

    try:
        for chunk in stream.iter_chunks(
            chunk_size=1024 * 1024,
        ):
            if chunk:
                digest.update(chunk)
    finally:
        stream.close()

    return digest.hexdigest()


def _verify_hold(
    s3,
    bucket: str,
    key: str,
    version_id: str,
) -> None:
    """Require legal hold ON for the specified S3 version."""

    response = s3.get_object_legal_hold(
        Bucket=bucket,
        Key=key,
        VersionId=version_id,
    )

    status = response.get(
        "LegalHold",
        {},
    ).get("Status")

    if status != "ON":
        raise RuntimeError(
            f"LEGAL_HOLD_NOT_VERIFIED: "
            f"{key} version={version_id}"
        )


def _verify_version(
    s3,
    bucket: str,
    key: str,
    version_id: str,
    expected_sha: str,
) -> None:
    """Verify legal hold and content for one exact object version."""

    _verify_hold(
        s3,
        bucket,
        key,
        version_id,
    )

    actual_sha = _remote_sha256(
        s3,
        bucket,
        key,
        version_id,
    )

    if actual_sha != expected_sha:
        raise RuntimeError(
            f"REMOTE_CONTENT_MISMATCH: "
            f"{key} version={version_id}"
        )


def _current_version(
    s3,
    bucket: str,
    key: str,
) -> str:
    """Resolve the current object version without modifying it."""

    response = s3.head_object(
        Bucket=bucket,
        Key=key,
    )

    version = response.get("VersionId")

    if not version or version == "null":
        raise RuntimeError(
            f"MISSING_VERSION_ID: {key}"
        )

    return version


def _is_conditional_conflict(exc: ClientError) -> bool:
    """Recognize S3 conditional-write conflicts."""

    error = exc.response.get("Error", {})
    code = error.get("Code")

    status = exc.response.get(
        "ResponseMetadata",
        {},
    ).get("HTTPStatusCode")

    return (
        code in (
            "PreconditionFailed",
            "ConditionalRequestConflict",
        )
        or status in (409, 412)
    )


def upload_aws_legal_hold(
    s3,
    bucket: str,
    key: str,
    path: Path,
    metadata: dict[str, str],
    *,
    audit_path: Path,
) -> str:
    """Create a protected S3 object or verify an identical protected replay.

    Returns:
        CREATED:
            A new object version was created, its legal hold was verified,
            its content matched, and the success audit event was written.

        IDENTICAL_REPLAY:
            An existing current version was verified as legally held
            and byte-identical, and the replay audit event was written.

    Raises:
        ValueError:
            Required inputs are missing.

        RuntimeError:
            Legal hold, object version, or content verification failed.

        ClientError:
            An unexpected S3 operation failed.

        OSError:
            A required audit operation failed.

    Important:
        Failure after an S3 write does not imply that the object was
        rolled back or deleted.
    """

    if not bucket or not key or audit_path is None:
        raise ValueError(
            "bucket, key, and audit_path are required"
        )

    path = Path(path)

    sha, md5, size = _digests(path)

    def audit(outcome: str) -> None:
        """Append one durable audit event."""

        append_audit_event(
            audit_path,
            operation="PROTECTED_AWS_UPLOAD",
            outcome=outcome,
            bucket=bucket,
            key=key,
            batch_id=metadata.get(
                "batch-id",
                "unknown",
            ),
            sha256=sha,
        )

    def audit_failure(outcome: str) -> None:
        """Best-effort failure audit without masking the original error.

        The original operation has already failed when this is called.
        Failure to append the additional audit record must not replace
        the primary exception.
        """

        try:
            audit(outcome)
        except Exception:
            pass

    # Audit must succeed before any S3 write is attempted.
    audit("ATTEMPTED")

    # -------------------------------------------------------------
    # STEP 1: Conditional S3 creation with legal hold ON.
    # -------------------------------------------------------------

    try:
        with path.open("rb") as stream:
            response = s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=stream,
                ContentLength=size,
                ContentType="application/vnd.apache.parquet",
                ContentMD5=md5,
                Metadata={
                    **metadata,
                    "sha256": sha,
                },
                IfNoneMatch="*",
                ObjectLockLegalHoldStatus="ON",
            )

    except ClientError as exc:

        if not _is_conditional_conflict(exc):
            audit_failure("UPLOAD_FAILED")
            raise

        # ---------------------------------------------------------
        # STEP 2: Conditional-write conflict / protected replay.
        # ---------------------------------------------------------

        try:
            version = _current_version(
                s3,
                bucket,
                key,
            )

            _verify_hold(
                s3,
                bucket,
                key,
                version,
            )

            actual_sha = _remote_sha256(
                s3,
                bucket,
                key,
                version,
            )

        except (ClientError, RuntimeError):
            audit_failure("REPLAY_VERIFICATION_FAILED")
            raise

        if actual_sha != sha:
            audit("PROTECTED_BATCH_CONFLICT")
            raise RuntimeError(
                f"PROTECTED_BATCH_CONFLICT: {key}"
            )

        audit("IDENTICAL_REPLAY")
        return "IDENTICAL_REPLAY"

    except Exception:
        audit_failure("UPLOAD_FAILED")
        raise

    # -------------------------------------------------------------
    # STEP 3: Verify the newly created object version.
    # -------------------------------------------------------------

    try:
        version = response.get("VersionId")

        if not version or version == "null":
            raise RuntimeError(
                f"MISSING_VERSION_ID_AFTER_CREATE: {key}"
            )

        _verify_version(
            s3,
            bucket,
            key,
            version,
            sha,
        )

    except Exception:
        audit_failure("VERIFICATION_FAILED")
        raise

    # -------------------------------------------------------------
    # STEP 4: Record successful protected creation.
    # -------------------------------------------------------------

    audit("CREATED")

    return "CREATED"