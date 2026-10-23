"""Isolated tests; never require or modify private original Olist files."""
import hashlib
import json

import pytest

from analytics.validate_olist_csv_integrity import inspect, validate_manifest
from analytics.validate_raw_olist import ENTITY_TABLES


def fixture_manifest(root, *, corrupt=None):
    entries = []
    for name in ENTITY_TABLES:
        content = ("fixture:" + name).encode()
        (root / name).write_bytes(content)
        entries.append({
            "file_name": name, "data_rows": 1, "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest()
        })
    if corrupt:
        entries[0][corrupt] = "invalid"
    return {"files": entries}


def test_matching_files_pass(tmp_path):
    manifest = fixture_manifest(tmp_path)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    result = inspect(tmp_path, path)
    assert len(result) == 9
    assert all(x["size_ok"] and x["sha256_ok"] for x in result.values())


def test_same_size_modified_content_detected(tmp_path):
    manifest = fixture_manifest(tmp_path)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    name = next(iter(ENTITY_TABLES))
    content = (tmp_path / name).read_bytes()
    (tmp_path / name).write_bytes(b"X" + content[1:])
    assert not inspect(tmp_path, path)[name]["sha256_ok"]


def test_missing_or_extra_csv_fails(tmp_path):
    manifest = fixture_manifest(tmp_path)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / next(iter(ENTITY_TABLES))).unlink()
    with pytest.raises(ValueError, match="inventory"):
        inspect(tmp_path, path)


@pytest.mark.parametrize("field", ["sha256", "size_bytes"])
def test_malformed_manifest_rejected(tmp_path, field):
    with pytest.raises(ValueError):
        validate_manifest(fixture_manifest(tmp_path, corrupt=field))


def test_direct_script_invocation_imports_without_repository_pythonpath():
    import os
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "analytics" / "validate_olist_csv_integrity.py"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-I", str(script), "--help"],
        cwd=script.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--raw-root" in result.stdout
