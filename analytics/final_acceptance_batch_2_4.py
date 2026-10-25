"""Offline acceptance gate for milestones 2–4; never changes protected data.

A PASS means only the locally executed checks passed. Unprovided security evidence
is explicitly NOT_VERIFIED, not silently treated as passing.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def evaluate(*, database: Path, audit_file: Path | None = None,
             audit_seal: Path | None = None, hmac_key: bytes | None = None,
             approval_envelope: Path | None = None, trusted_public_key: Path | None = None,
             owner_id: str | None = None, environment: str | None = None,
             bucket: str | None = None, object_key: str | None = None,
             version_id: str | None = None) -> dict:
    from analytics.acceptance_batch_2_4 import inspect

    report = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "milestone_2": {"audit_integrity": "NOT_VERIFIED", "owner_approval": "NOT_VERIFIED",
                        "cloud_enforcement": "NOT_VERIFIED", "deletion_replay_prevention": "NOT_VERIFIED"},
        "milestone_3": {"delivered_gross_value": "NOT_VERIFIED",
                        "payment_settlement": "NOT_VERIFIED", "net_revenue": "NOT_VERIFIED"},
        "milestone_4": {"cross_mart_parity": "NOT_VERIFIED",
                        "live_alerting": "NOT_VERIFIED", "scheduled_recovery": "NOT_VERIFIED"},
        "errors": [],
    }
    try:
        revenue = inspect(database)
        report["reconciliation"] = revenue
        if revenue["status"] == "PASS":
            report["milestone_3"]["delivered_gross_value"] = "PASS"
            report["milestone_4"]["cross_mart_parity"] = "PASS"
        else:
            report["milestone_3"]["delivered_gross_value"] = "FAIL"
            report["milestone_4"]["cross_mart_parity"] = "FAIL"
            report["errors"].append("Cross-mart reconciliation failed")
    except Exception as exc:
        report["milestone_3"]["delivered_gross_value"] = "FAIL"
        report["milestone_4"]["cross_mart_parity"] = "FAIL"
        report["errors"].append(f"Revenue inspection failed: {type(exc).__name__}: {exc}")

    audit_args = (audit_file, audit_seal, hmac_key)
    if any(value is not None for value in audit_args):
        if not all(value is not None for value in audit_args):
            report["errors"].append("Audit verification requires file, seal and HMAC key")
            report["milestone_2"]["audit_integrity"] = "FAIL"
        else:
            try:
                from ingestion.object_store.governance_evidence import verify_audit_seal
                verify_audit_seal(audit_file, audit_seal, hmac_key=hmac_key)
                report["milestone_2"]["audit_integrity"] = "PASS"
            except Exception as exc:
                report["milestone_2"]["audit_integrity"] = "FAIL"
                report["errors"].append(f"Audit verification failed: {type(exc).__name__}: {exc}")

    approval_args = (approval_envelope, trusted_public_key, owner_id,
                     environment, bucket, object_key)
    if any(value is not None for value in approval_args):
        if not all(value is not None for value in approval_args):
            report["milestone_2"]["owner_approval"] = "FAIL"
            report["errors"].append("Approval verification requires all scope and trust arguments")
        else:
            try:
                from ingestion.object_store.governance_evidence import verify_signed_owner_approval
                ref = verify_signed_owner_approval(
                    json.loads(approval_envelope.read_text(encoding="utf-8")),
                    trusted_public_key=trusted_public_key.read_bytes(),
                    owner_id=owner_id, environment=environment, bucket=bucket,
                    key=object_key, version_id=version_id)
                report["milestone_2"]["owner_approval"] = "PASS"
                report["approval_ref"] = ref
            except Exception as exc:
                report["milestone_2"]["owner_approval"] = "FAIL"
                report["errors"].append(f"Approval verification failed: {type(exc).__name__}: {exc}")

    report["status"] = "FAIL" if report["errors"] else "PASS_WITH_LIMITATIONS"
    report["limitations"] = [
        "PASS_WITH_LIMITATIONS is not production certification or full milestone closure.",
        "No deletion is performed or enabled; owner approval verification does not prevent replay.",
        "Audit seals require independently protected keys and checkpoints for durable tamper evidence.",
        "Cloud retention, live alert delivery and scheduled recovery are not checked by this gate.",
        "Gross delivered order value excludes payment settlement and net-revenue validation.",
    ]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="Optional new report path (never overwrites)")
    parser.add_argument("--audit-file", type=Path)
    parser.add_argument("--audit-seal", type=Path)
    parser.add_argument("--audit-hmac-env", help="Name of environment variable containing hex HMAC key")
    parser.add_argument("--approval-envelope", type=Path)
    parser.add_argument("--trusted-public-key", type=Path)
    parser.add_argument("--owner-id")
    parser.add_argument("--environment", choices=("dev", "ci", "prod"))
    parser.add_argument("--bucket")
    parser.add_argument("--object-key")
    parser.add_argument("--version-id")
    args = parser.parse_args()
    hmac_key = None
    if args.audit_hmac_env:
        value = os.environ.get(args.audit_hmac_env)
        if value is None:
            parser.error("Audit HMAC environment variable is unset")
        try:
            hmac_key = bytes.fromhex(value)
        except ValueError:
            parser.error("Audit HMAC environment variable must contain hex bytes")
    report = evaluate(database=args.db, audit_file=args.audit_file,
                      audit_seal=args.audit_seal, hmac_key=hmac_key,
                      approval_envelope=args.approval_envelope,
                      trusted_public_key=args.trusted_public_key,
                      owner_id=args.owner_id, environment=args.environment,
                      bucket=args.bucket, object_key=args.object_key,
                      version_id=args.version_id)
    content = json.dumps(report, indent=2) + "\n"
    print(content, end="")
    if args.output:
        if not args.output.parent.is_dir():
            parser.error("Report output directory does not exist")
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(content)
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
