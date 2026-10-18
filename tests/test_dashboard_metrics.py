from decimal import Decimal

import pandas as pd
import pytest

from dashboards.metrics import assert_reconciled, delivered_metrics, money_sum


def test_decimal_preservation():
    assert money_sum(['0.10', '0.20']) == Decimal('0.30')


def test_delivered_only():
    frame = pd.DataFrame({
        'is_delivered': [True, False, True],
        'merchandise_value': [Decimal('10.10'), Decimal('999.00'), Decimal('20.20')],
        'freight_value': [Decimal('1.00'), Decimal('999.00'), Decimal('2.00')],
        'gross_order_value': [Decimal('11.10'), Decimal('1998.00'), Decimal('22.20')],
    })
    actual = delivered_metrics(frame)
    assert actual == {'delivered_orders': 2, 'merchandise': Decimal('30.30'), 'freight': Decimal('3.00'), 'gross': Decimal('33.30')}
    assert_reconciled(actual)


def test_reconciliation_failure():
    with pytest.raises(ValueError):
        assert_reconciled({'merchandise': Decimal('1.00'), 'freight': Decimal('1.00'), 'gross': Decimal('3.00')})
