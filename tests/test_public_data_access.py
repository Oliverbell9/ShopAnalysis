"""Isolated tests for the public aggregate CSV loader."""

import csv
import shutil
from pathlib import Path

import pytest

from dashboards.public_data_access import (
    PublicDataValidationError,
    load_public_aggregates,
)

EXPORT_NAME = "export_20261012T141941Z_5e2149187ff6"


@pytest.fixture
def export_copy(tmp_path):
    source = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "public_aggregate_exports"
        / EXPORT_NAME
    )

    if not source.is_dir():
        pytest.skip("Verified local aggregate export is unavailable")

    destination = tmp_path / "export"
    shutil.copytree(source, destination)
    return destination


def modify_csv(path, callback):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames
        rows = list(reader)

    callback(rows)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_valid_export(export_copy):
    data = load_public_aggregates(export_copy)

    assert len(data) == 6
    assert data["executive_kpis"][0]["delivered_orders"] == 96478


def test_missing_file_rejected(export_copy):
    (export_copy / "customer_states.csv").unlink()

    with pytest.raises(PublicDataValidationError):
        load_public_aggregates(export_copy)


def test_unexpected_csv_rejected(export_copy):
    (export_copy / "unexpected.csv").write_text(
        "value\n1\n", encoding="utf-8"
    )

    with pytest.raises(PublicDataValidationError):
        load_public_aggregates(export_copy)


def test_invalid_schema_rejected(export_copy):
    path = export_copy / "executive_kpis.csv"

    content = path.read_text(encoding="utf-8-sig")
    path.write_text(
        content.replace("delivered_orders", "order_identifier", 1),
        encoding="utf-8",
    )

    with pytest.raises(PublicDataValidationError):
        load_public_aggregates(export_copy)


def test_altered_totals_rejected(export_copy):
    path = export_copy / "executive_kpis.csv"

    modify_csv(
        path,
        lambda rows: rows[0].update({"gross": "1.00"}),
    )

    with pytest.raises(PublicDataValidationError):
        load_public_aggregates(export_copy)


def test_invalid_payment_classification_rejected(export_copy):
    path = export_copy / "payment_reconciliation.csv"

    modify_csv(
        path,
        lambda rows: rows[0].update({"orders": "1"}),
    )

    with pytest.raises(PublicDataValidationError):
        load_public_aggregates(export_copy)


def test_symlink_file_rejected(export_copy, tmp_path):
    path = export_copy / "customer_states.csv"
    target = tmp_path / "customer_states.csv"

    shutil.copy2(path, target)
    path.unlink()

    try:
        path.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation unavailable")

    with pytest.raises(PublicDataValidationError):
        load_public_aggregates(export_copy)


def test_excess_rows_rejected(export_copy):
    path = export_copy / "executive_kpis.csv"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("96478,13221498.11,2198275.64,15419773.75\\n")
    with pytest.raises(PublicDataValidationError):
        load_public_aggregates(export_copy)


def test_oversized_file_rejected(export_copy):
    path = export_copy / "executive_kpis.csv"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("x" * 1_048_577)
    with pytest.raises(PublicDataValidationError):
        load_public_aggregates(export_copy)


def test_invalid_utf8_rejected(export_copy):
    path = export_copy / "executive_kpis.csv"
    with path.open("ab") as handle:
        handle.write(b"\\xff")
    with pytest.raises(PublicDataValidationError):
        load_public_aggregates(export_copy)


def test_malformed_csv_rejected(export_copy):
    path = export_copy / "executive_kpis.csv"
    path.write_text(
        'delivered_orders,merchandise,freight,gross\\n'
        '"96478,13221498.11,2198275.64,15419773.75\\n',
        encoding="utf-8",
    )
    with pytest.raises(PublicDataValidationError):
        load_public_aggregates(export_copy)


def test_ancestor_symlink_rejected(export_copy, tmp_path):
    link = tmp_path / "linked_export"
    try:
        link.symlink_to(export_copy, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Directory symlink creation unavailable")

    with pytest.raises(PublicDataValidationError):
        load_public_aggregates(link)


def test_windows_junction_rejected(export_copy, tmp_path):
    import os
    import subprocess

    if os.name != "nt":
        pytest.skip("Windows junction test")

    junction = tmp_path / "junction_export"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(export_copy)],
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.skip("Windows junction creation unavailable")

    try:
        assert junction.is_junction()
        with pytest.raises(PublicDataValidationError):
            load_public_aggregates(junction)
    finally:
        junction.rmdir()
