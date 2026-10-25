"""Synthetic-only acceptance regression tests; no protected database access."""
from decimal import Decimal

import pytest

from analytics.acceptance_batch_2_4 import compare_totals, decimal_value


def test_matching_marts():
    values = {'gross_merchandise_revenue': Decimal('10.10'),
              'freight_value': Decimal('2.20'),
              'gross_order_value': Decimal('12.30')}
    assert compare_totals(values, values.copy(), 'monthly') == []


def test_mismatch_reports_metric_and_values():
    baseline = {'gross_merchandise_revenue': Decimal('10.10'),
                'freight_value': Decimal('2.20'),
                'gross_order_value': Decimal('12.30')}
    candidate = dict(baseline, gross_order_value=Decimal('12.29'))
    assert compare_totals(baseline, candidate, 'seller') == [
        {'mart': 'seller', 'metric': 'gross_order_value',
         'expected': '12.30', 'observed': '12.29'}]


def test_reject_float_money():
    with pytest.raises(ValueError, match='floating-point'):
        decimal_value(1.5)


def test_none_aggregates_to_zero():
    assert decimal_value(None) == Decimal('0')
