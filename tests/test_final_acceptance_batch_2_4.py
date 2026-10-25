"""Synthetic offline acceptance tests; never open a real project database."""
import base64
import json
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from analytics.final_acceptance_batch_2_4 import evaluate
from ingestion.object_store.governance_evidence import _canonical, seal_audit_file


REVENUE = {"status": "PASS", "orders": 2, "delivered_orders": 1,
           "mart_totals": {}, "discrepancies": []}


def run(**kwargs):
    with patch("analytics.acceptance_batch_2_4.inspect", return_value=REVENUE):
        return evaluate(database=Path("synthetic.duckdb"), **kwargs)


def test_missing_security_evidence_is_explicitly_unverified():
    report = run()
    assert report["status"] == "PASS_WITH_LIMITATIONS"
    assert report["milestone_2"]["owner_approval"] == "NOT_VERIFIED"
    assert report["milestone_2"]["audit_integrity"] == "NOT_VERIFIED"
    assert report["milestone_3"]["delivered_gross_value"] == "PASS"
    assert report["milestone_4"]["cross_mart_parity"] == "PASS"


def test_reconciliation_discrepancy_fails_gate():
    with patch("analytics.acceptance_batch_2_4.inspect", return_value={"status": "FAIL"}):
        report = evaluate(database=Path("synthetic.duckdb"))
    assert report["status"] == "FAIL"


def test_missing_database_fails_gate():
    with patch("analytics.acceptance_batch_2_4.inspect", side_effect=FileNotFoundError("missing")):
        report = evaluate(database=Path("synthetic.duckdb"))
    assert report["status"] == "FAIL"


def test_partial_audit_evidence_fails_gate(tmp_path):
    report = run(audit_file=tmp_path / "audit")
    assert report["status"] == "FAIL"


def test_valid_and_tampered_audit_evidence(tmp_path):
    source, seal = tmp_path / "events.jsonl", tmp_path / "seal.json"
    source.write_text('{"event":"upload"}\n', encoding="utf-8")
    key = b"z" * 32
    seal_audit_file(source, seal, hmac_key=key)
    assert run(audit_file=source, audit_seal=seal, hmac_key=key)["milestone_2"]["audit_integrity"] == "PASS"
    source.write_text('{"event":"delete"}\n', encoding="utf-8")
    assert run(audit_file=source, audit_seal=seal, hmac_key=key)["status"] == "FAIL"


def test_valid_and_forged_owner_approval(tmp_path):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    pub = tmp_path / "trusted.pub"
    pub.write_bytes(public)
    approval = {"approval_ref": "TEST", "approver_id": "owner", "environment": "dev",
                "bucket": "bucket", "key": "dev/raw/obj", "reason": "test"}
    envelope = {"approval": approval, "signature_b64": base64.b64encode(
        private.sign(_canonical(approval))).decode()}
    path = tmp_path / "approval.json"
    path.write_text(json.dumps(envelope), encoding="utf-8")
    opts = dict(approval_envelope=path, trusted_public_key=pub, owner_id="owner",
                environment="dev", bucket="bucket", object_key="dev/raw/obj")
    assert run(**opts)["milestone_2"]["owner_approval"] == "PASS"
    envelope["approval"]["key"] = "dev/raw/other"
    path.write_text(json.dumps(envelope), encoding="utf-8")
    assert run(**opts)["status"] == "FAIL"
