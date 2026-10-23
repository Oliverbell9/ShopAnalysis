"""Synthetic, dependency-free revenue reconciliation regression tests."""
from decimal import Decimal

import pytest

from analytics.reconcile_revenue import summarize_rows


def row(order_id, merchandise, freight, gross, delivered=True, status="exact_match"):
    return {
        "order_id": order_id, "is_delivered": delivered,
        "merchandise_value": Decimal(merchandise),
        "freight_value": Decimal(freight),
        "gross_order_value": Decimal(gross),
        "reconciliation_status": status,
        "is_delivery_timestamp_exception": False,
    }


def test_delivered_only_and_status_counts():
    result = summarize_rows([
        row("A", "10.00", "2.00", "12.00"),
        row("B", "9.00", "1.00", "10.00", False, "missing_payment"),
    ])
    assert result["delivered_orders"] == 1
    assert result["totals"]["gross_order_value"] == Decimal("12.00")
    assert result["reconciliation_status_counts"]["missing_payment"] == 1


def test_rejects_duplicate_order_grain():
    with pytest.raises(ValueError, match="Duplicate order_id"):
        summarize_rows([row("A", "1", "1", "2"), row("A", "1", "1", "2")])


def test_rejects_financial_imbalance():
    with pytest.raises(ValueError, match="merchandise"):
        summarize_rows([row("A", "1", "1", "3")])


def test_rejects_float_money():
    bad = row("A", "1", "1", "2")
    bad["gross_order_value"] = 2.0
    with pytest.raises(ValueError, match="Floating-point"):
        summarize_rows([bad])


def test_delivery_exception_count():
    bad = row("A", "1", "1", "2")
    bad["is_delivery_timestamp_exception"] = True
    assert summarize_rows([bad])["delivery_timestamp_exceptions"] == 1
