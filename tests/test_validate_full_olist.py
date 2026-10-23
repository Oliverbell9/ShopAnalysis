"""Isolated pure-function tests for the full-data evidence gate."""
from decimal import Decimal

from analytics.validate_full_olist import DOCUMENTED_CONTROLS, assess


def valid_metrics():
    return {
        "total_orders": 2,
        "distinct_order_ids": 2,
        "null_order_ids": 0,
        "delivered_orders": 1,
        "non_delivered_orders": 1,
        "delivered_null_money": 0,
        "unclassified_missing_payments": 0,
        "inconsistent_missing_payment_status": 0,
        "classified_missing_payments": 0,
        "delivered_row_mismatches": 0,
        "merchandise": Decimal("10.00"),
        "freight": Decimal("2.00"),
        "gross": Decimal("12.00"),
        "payment": Decimal("12.00"),
        "delivery_timestamp_exceptions": 0,
    }


def test_synthetic_control_without_historical_comparison():
    assert assess(valid_metrics()) == []


def test_duplicate_and_null_order_ids_rejected():
    m = valid_metrics()
    m["distinct_order_ids"] = 1
    m["null_order_ids"] = 1
    assert len(assess(m)) == 2


def test_null_money_and_row_mismatch_rejected():
    m = valid_metrics()
    m["delivered_null_money"] = 1
    m["delivered_row_mismatches"] = 1
    assert len(assess(m)) == 2


def test_aggregate_parity_rejected():
    m = valid_metrics()
    m["gross"] = Decimal("13.00")
    assert "Delivered aggregate merchandise + freight != gross" in assess(m)


def test_documented_comparison_requires_opt_in():
    assert assess(valid_metrics()) == []
    assert any("Documented full-Olist" in issue
               for issue in assess(valid_metrics(), compare_documented=True))


def test_documented_controls_can_match():
    m = valid_metrics()
    m.update(DOCUMENTED_CONTROLS)
    m["total_orders"] = m["distinct_order_ids"] = m["delivered_orders"]
    m["non_delivered_orders"] = 0
    assert assess(m, compare_documented=True) == []


def test_classified_missing_payment_is_reported_not_failed():
    m = valid_metrics()
    m["classified_missing_payments"] = 1
    assert assess(m) == []


def test_unclassified_missing_payment_fails():
    m = valid_metrics()
    m["unclassified_missing_payments"] = 1
    assert "Delivered missing payments without missing_payment classification" in assess(m)


def test_inconsistent_missing_payment_status_fails():
    m = valid_metrics()
    m["inconsistent_missing_payment_status"] = 1
    assert "Delivered missing_payment status has non-NULL payment or payment counts" in assess(m)
