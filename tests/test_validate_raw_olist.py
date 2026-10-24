"""Pure regression checks for the read-only RAW evidence gate."""
import pytest

from analytics.validate_raw_olist import ENTITY_TABLES, assess, expected_rows


def test_manifest_maps_all_nine_entities():
    manifest = {"files": [
        {"file_name": name, "data_rows": 2} for name in ENTITY_TABLES
    ]}
    assert len(expected_rows(manifest)) == 9


def test_manifest_rejects_missing_and_duplicate_files():
    names = list(ENTITY_TABLES)
    with pytest.raises(ValueError):
        expected_rows({"files": [{"file_name": name, "data_rows": 1}
                                 for name in names[:-1]]})
    with pytest.raises(ValueError):
        expected_rows({"files": [{"file_name": names[0], "data_rows": 1}]
                                 * 9})


def test_manifest_rejects_invalid_counts():
    manifest = {"files": [{"file_name": name, "data_rows": 1}
                          for name in ENTITY_TABLES]}
    manifest["files"][0]["data_rows"] = True
    with pytest.raises(ValueError):
        expected_rows(manifest)


def record(**kwargs):
    return dict(expected=10, actual=10, null_lineage=0,
                distinct_batches=1, batch_id="batch-1", **kwargs)


def test_matching_raw_evidence_passes():
    assert assess({"orders": record(), "payments": record()}) == []


def test_mismatch_null_lineage_and_batch_mismatch_fail():
    rows = {
        "orders": record(),
        "payments": {"expected": 10, "actual": 9, "null_lineage": 1,
                         "distinct_batches": 1, "batch_id": "batch-2"},
    }
    assert len(assess(rows)) == 3


def test_missing_batch_fails():
    rows = {"orders": {"expected": 10, "actual": 10, "null_lineage": 0,
                           "distinct_batches": 0, "batch_id": None}}
    assert any("batch ID" in issue for issue in assess(rows))
