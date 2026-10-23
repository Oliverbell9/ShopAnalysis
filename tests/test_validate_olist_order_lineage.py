"""Pure lineage assessment tests; no full Olist data required."""
import pytest

from analytics.validate_olist_order_lineage import assess, inspect


def test_all_zero_metrics_pass():
    assert assess({"missing": 0, "mismatch": 0}) == []


def test_nonzero_missing_or_mismatch_fails():
    assert assess({"missing": 2, "mismatch": 1}) == [
        "missing: 2 mismatched rows/keys",
        "mismatch: 1 mismatched rows/keys",
    ]


def test_missing_database_fails_without_creation(tmp_path):
    path = tmp_path / "absent.duckdb"
    with pytest.raises(FileNotFoundError):
        inspect(path)
    assert not path.exists()
