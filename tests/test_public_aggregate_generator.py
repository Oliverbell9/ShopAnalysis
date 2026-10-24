"""Unit tests use synthetic rows; no ShopAnalysis database required."""
from decimal import Decimal

import pytest

from dashboards.public_aggregate_generator import (
    ALLOWED,
    EXPECTED,
    as_decimal,
    validate,
)


def test_decimal_rejects_float_and_null():
    assert as_decimal(Decimal("2.10")) == Decimal("2.10")
    with pytest.raises(ValueError):
        as_decimal(2.1)
    with pytest.raises(ValueError):
        as_decimal(None)


def test_validation_rejects_missing_datasets():
    with pytest.raises(ValueError, match="Unexpected dataset"):
        validate({})


def test_validation_rejects_identifier_columns():
    data = {name: [{key: 0 for key in ALLOWED[name]} for _ in range(n)]
            for name, n in EXPECTED.items()}
    data["executive_kpis"][0]["order_id"] = "private"
    with pytest.raises(ValueError, match="unexpected or missing column"):
        validate(data)


def test_validation_rejects_incorrect_group_count():
    data = {name: [] for name in EXPECTED}
    with pytest.raises(ValueError, match="expected 1 rows"):
        validate(data)


def test_duplicate_grouping_key_rejected():
    from copy import deepcopy
    from pathlib import Path

    from dashboards.public_aggregate_generator import build_in_memory

    db = Path("data/airflow_dev/shopanalysis_airflow.duckdb")
    if not db.is_file():
        import pytest
        pytest.skip("Integration DuckDB database unavailable")

    data = deepcopy(build_in_memory(db))

    rows = data["revenue_periods"]
    assert len(rows) >= 2

    rows[1]["reporting_period"] = rows[0]["reporting_period"]

    import pytest
    with pytest.raises(
        ValueError,
        match="revenue_periods: duplicate grouping keys"
    ):
        validate(data)



def test_export_csv_roundtrip(tmp_path, monkeypatch):
    """Synthetic CSV export preserves approved headers and exact decimals."""
    import csv
    from decimal import Decimal

    from dashboards import public_aggregate_generator as generator

    synthetic = {
        "sample": [
            {
                "group": "Example",
                "amount": Decimal("123.40"),
            }
        ]
    }

    monkeypatch.setattr(generator, "EXPECTED", {"sample": 1})
    monkeypatch.setattr(
        generator,
        "ALLOWED",
        {"sample": ("group", "amount")},
    )
    monkeypatch.setattr(generator, "validate", lambda data: True)

    destination = tmp_path / "synthetic_export"

    files = generator.export_csv(synthetic, destination)

    assert len(files) == 1
    assert files[0].name == "sample.csv"

    with files[0].open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["group", "amount"]
        assert list(reader) == [
            {"group": "Example", "amount": "123.40"}
        ]


def test_export_csv_rejects_existing_destination(tmp_path, monkeypatch):
    """Existing directories must never be overwritten."""
    from dashboards import public_aggregate_generator as generator

    monkeypatch.setattr(generator, "EXPECTED", {"sample": 1})
    monkeypatch.setattr(
        generator,
        "ALLOWED",
        {"sample": ("group",)},
    )
    monkeypatch.setattr(generator, "validate", lambda data: True)

    destination = tmp_path / "existing"
    destination.mkdir()

    sentinel = destination / "keep.txt"
    sentinel.write_text("preserve", encoding="utf-8")

    with pytest.raises(FileExistsError):
        generator.export_csv(
            {"sample": [{"group": "Example"}]},
            destination,
        )

    assert sentinel.read_text(encoding="utf-8") == "preserve"


def test_export_csv_rejects_invalid_data_before_writing(
    tmp_path, monkeypatch
):
    """Failed pre-export validation must not create a directory."""
    from dashboards import public_aggregate_generator as generator

    def reject(data):
        raise ValueError("Synthetic validation failure")

    monkeypatch.setattr(generator, "validate", reject)

    destination = tmp_path / "must_not_exist"

    with pytest.raises(ValueError, match="Synthetic validation failure"):
        generator.export_csv({}, destination)

    assert not destination.exists()



def test_export_csv_verification_failure_cleanup(tmp_path, monkeypatch):
    """Verification failure removes only the newly created export directory."""
    import csv

    from dashboards import public_aggregate_generator as generator

    synthetic = {"sample": [{"group": "Example"}]}

    monkeypatch.setattr(generator, "EXPECTED", {"sample": 1})
    monkeypatch.setattr(generator, "ALLOWED", {"sample": ("group",)})
    monkeypatch.setattr(generator, "validate", lambda data: True)

    destination = tmp_path / "failed_export"
    sentinel = tmp_path / "preserve.txt"
    sentinel.write_text("unchanged", encoding="utf-8")

    original_dict_reader = csv.DictReader

    class CorruptReader(original_dict_reader):
        @property
        def fieldnames(self):
            return ["unexpected_column"]

    monkeypatch.setattr(csv, "DictReader", CorruptReader)

    with pytest.raises(ValueError, match="exported header mismatch"):
        generator.export_csv(synthetic, destination)

    assert not destination.exists()
    assert sentinel.read_text(encoding="utf-8") == "unchanged"



def test_export_cleanup_preserves_unrelated_file(tmp_path, monkeypatch):
    """Failed export must preserve files it did not create."""
    import csv

    from dashboards import public_aggregate_generator as generator

    synthetic = {"sample": [{"group": "Example"}]}

    monkeypatch.setattr(generator, "EXPECTED", {"sample": 1})
    monkeypatch.setattr(
        generator, "ALLOWED", {"sample": ("group",)}
    )
    monkeypatch.setattr(generator, "validate", lambda data: True)

    destination = tmp_path / "failed_export"
    original_reader = csv.DictReader

    class InjectFailureReader(original_reader):
        @property
        def fieldnames(self):
            unrelated = destination / "unrelated.txt"
            unrelated.write_text("preserve", encoding="utf-8")
            return ["incorrect_header"]

    monkeypatch.setattr(csv, "DictReader", InjectFailureReader)

    with pytest.raises(ValueError, match="exported header mismatch"):
        generator.export_csv(synthetic, destination)

    assert destination.is_dir()
    assert (destination / "unrelated.txt").read_text(
        encoding="utf-8"
    ) == "preserve"
    assert not (destination / "sample.csv").exists()



@pytest.mark.parametrize("broken", [False, True])
def test_export_rejects_symbolic_link_destination(
    tmp_path, monkeypatch, broken
):
    """Existing and broken symlink destinations must be rejected."""
    from dashboards import public_aggregate_generator as generator

    monkeypatch.setattr(generator, "EXPECTED", {"sample": 1})
    monkeypatch.setattr(
        generator, "ALLOWED", {"sample": ("group",)}
    )
    monkeypatch.setattr(generator, "validate", lambda data: True)

    target = tmp_path / "target"
    if not broken:
        target.mkdir()

    link = tmp_path / "export_link"

    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symbolic-link creation unavailable: {exc}")

    assert link.is_symlink()

    with pytest.raises(FileExistsError):
        generator.export_csv(
            {"sample": [{"group": "Example"}]},
            link,
        )

    assert link.is_symlink()

    if not broken:
        assert target.is_dir()
        assert list(target.iterdir()) == []



@pytest.mark.parametrize(
    "destination_exists",
    [True, False],
)
def test_export_rejects_mocked_symlink(
    tmp_path, monkeypatch, destination_exists
):
    """Reject existing and broken symlinks before directory creation."""
    from pathlib import Path
    from unittest.mock import patch

    from dashboards import public_aggregate_generator as generator

    monkeypatch.setattr(generator, "EXPECTED", {"sample": 1})
    monkeypatch.setattr(
        generator, "ALLOWED", {"sample": ("group",)}
    )
    monkeypatch.setattr(generator, "validate", lambda data: True)

    destination = tmp_path / "simulated_link"

    original_exists = Path.exists
    original_is_symlink = Path.is_symlink

    def mocked_exists(self):
        if self == destination:
            return destination_exists
        return original_exists(self)

    def mocked_is_symlink(self):
        if self == destination:
            return True
        return original_is_symlink(self)

    with (
        patch.object(Path, "exists", mocked_exists),
        patch.object(Path, "is_symlink", mocked_is_symlink),
        patch.object(Path, "mkdir") as mkdir_mock,
    ):
        with pytest.raises(FileExistsError):
            generator.export_csv(
                {"sample": [{"group": "Example"}]},
                destination,
            )

        mkdir_mock.assert_not_called()

    assert not destination.exists()
