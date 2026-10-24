"""Pure regression checks for customer SCD2 evidence validation."""
import pytest

from analytics.validate_customer_scd2 import QUERIES, assess, inspect


def test_zero_exceptions_pass():
    assert assess({key: 0 for key in QUERIES}) == []


def test_nonzero_exceptions_fail():
    assert assess({"dimension.invalid_intervals": 2}) == [
        "dimension.invalid_intervals: 2 exceptions"
    ]


def test_missing_database_is_not_created(tmp_path):
    path = tmp_path / "missing.duckdb"
    with pytest.raises(FileNotFoundError):
        inspect(path)
    assert not path.exists()


def test_expected_coverage():
    assert len(QUERIES) == 12
    assert all(sql.strip().lower().startswith(("select", "with")) for sql in QUERIES.values())
