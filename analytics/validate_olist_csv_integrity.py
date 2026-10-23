"""Read-only SHA-256 and size verification for nine original Olist CSV files.

A match confirms equality with the recorded manifest fingerprints, not the
authenticity or provenance of the manifest itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from analytics.validate_raw_olist import ENTITY_TABLES, expected_rows

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def validate_manifest(manifest):
    expected_rows(manifest)
    files = manifest["files"]
    for entry in files:
        if not isinstance(entry.get("size_bytes"), int) or isinstance(entry["size_bytes"], bool) or entry["size_bytes"] <= 0:
            raise ValueError(f"Invalid manifest size: {entry['file_name']}")
        if not isinstance(entry.get("sha256"), str) or not _SHA256.fullmatch(entry["sha256"]):
            raise ValueError(f"Invalid manifest SHA-256: {entry['file_name']}")
    return files


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect(raw_root, manifest_path):
    if not raw_root.is_dir():
        raise FileNotFoundError(f"Original CSV directory not found: {raw_root}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = validate_manifest(manifest)
    actual_names = {p.name for p in raw_root.iterdir() if p.is_file() and p.suffix.lower() == ".csv"}
    expected_names = set(ENTITY_TABLES)
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        raise ValueError(f"CSV inventory differs: missing={missing}, extra={extra}")
    results = {}
    for entry in entries:
        name = entry["file_name"]
        path = raw_root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Expected regular CSV file: {name}")
        size = path.stat().st_size
        digest = sha256_file(path)
        results[name] = {
            "size_ok": size == entry["size_bytes"],
            "sha256_ok": digest == entry["sha256"],
        }
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path,
                        default=Path("data/manifests/olist_manifest.json"))
    args = parser.parse_args()
    results = inspect(args.raw_root, args.manifest)
    failed = False
    for name, result in results.items():
        passed = result["size_ok"] and result["sha256_ok"]
        print(f"{'PASS' if passed else 'FAIL'}: {name} "
              f"size_match={result['size_ok']} sha256_match={result['sha256_ok']}")
        failed |= not passed
    if failed:
        raise SystemExit(1)
    print("PASS: nine original CSV files match recorded manifest sizes and SHA-256")
    print("NOT CERTIFIED: manifest authenticity, acquisition provenance, "
          "RAW-to-mart transformation lineage, RBAC or cloud controls")


if __name__ == "__main__":
    main()
