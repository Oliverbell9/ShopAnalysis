"""Isolated tests for the read-only remaining marts evidence gate."""
import pytest

from analytics.validate_olist_remaining_marts import QUERIES, assess, inspect


def test_all_checks_pass():
    assert assess({name: 0 for name in QUERIES}) == []


def test_mismatch_fails():
    assert assess({"seller_revenue.mismatched_groups": 3}) == [
        "seller_revenue.mismatched_groups: 3 exceptions"
    ]


def test_missing_database_does_not_create_file(tmp_path):
    path = tmp_path / "missing.duckdb"
    with pytest.raises(FileNotFoundError):
        inspect(path)
    assert not path.exists()


def test_query_coverage():
    assert len(QUERIES) == 14
    assert all(query.strip().lower().startswith("select") or
               query.strip().lower().startswith("with")
               for query in QUERIES.values())
