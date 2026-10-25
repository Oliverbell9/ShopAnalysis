"""Synthetic-only signature and audit snapshot integrity tests."""
import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from ingestion.object_store.governance_evidence import (
    _canonical, seal_audit_file, verify_audit_seal, verify_signed_owner_approval,
)
from ingestion.object_store.protected_batch_governance import AuthorizationError


def sample():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    approval = {"approval_ref": "T-1", "approver_id": "owner", "environment": "prod",
                "bucket": "bucket", "key": "prod/raw/item", "reason": "exception"}
    envelope = {"approval": approval, "signature_b64": base64.b64encode(
        private.sign(_canonical(approval))).decode()}
    return public, envelope


def verify(envelope, public):
    return verify_signed_owner_approval(envelope, trusted_public_key=public,
        owner_id="owner", environment="prod", bucket="bucket", key="prod/raw/item")


def test_valid_owner_signature():
    public, envelope = sample()
    assert verify(envelope, public) == "T-1"


def test_tampered_approval_rejected():
    public, envelope = sample()
    envelope["approval"]["key"] = "prod/raw/other"
    with pytest.raises(AuthorizationError):
        verify(envelope, public)


def test_untrusted_signer_rejected():
    _, envelope = sample()
    other_public, _ = sample()
    with pytest.raises(AuthorizationError):
        verify(envelope, other_public)


def test_signed_wrong_scope_rejected():
    public, envelope = sample()
    with pytest.raises(AuthorizationError):
        verify_signed_owner_approval(envelope, trusted_public_key=public,
            owner_id="owner", environment="ci", bucket="bucket", key="prod/raw/item")


def test_invalid_signature_encoding_rejected():
    public, envelope = sample()
    envelope["signature_b64"] = "not base64!"
    with pytest.raises(AuthorizationError):
        verify(envelope, public)


def test_audit_seal_roundtrip_and_tamper(tmp_path):
    source = tmp_path / "audit.jsonl"
    seal = tmp_path / "audit.seal.json"
    key = b"k" * 32
    source.write_text('{"outcome":"ATTEMPTED"}\n', encoding="utf-8")
    assert seal_audit_file(source, seal, hmac_key=key)["event_count"] == 1
    assert verify_audit_seal(source, seal, hmac_key=key)
    source.write_text('{"outcome":"CREATED"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        verify_audit_seal(source, seal, hmac_key=key)


def test_audit_wrong_key_rejected(tmp_path):
    source, seal = tmp_path / "events", tmp_path / "seal"
    source.write_text('{"x":1}\n')
    seal_audit_file(source, seal, hmac_key=b"a" * 32)
    with pytest.raises(ValueError, match="authentication"):
        verify_audit_seal(source, seal, hmac_key=b"b" * 32)


def test_audit_truncated_or_unterminated_rejected(tmp_path):
    source, seal = tmp_path / "events", tmp_path / "seal"
    source.write_text('{"x":1}')
    with pytest.raises(ValueError, match="newline"):
        seal_audit_file(source, seal, hmac_key=b"a" * 32)


def test_audit_seal_never_overwrites(tmp_path):
    source, seal = tmp_path / "events", tmp_path / "seal"
    source.write_text('{"x":1}\n')
    seal_audit_file(source, seal, hmac_key=b"a" * 32)
    with pytest.raises(FileExistsError):
        seal_audit_file(source, seal, hmac_key=b"a" * 32)
