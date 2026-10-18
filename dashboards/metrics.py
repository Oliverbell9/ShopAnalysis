"""Financial measures use order-grain DECIMAL values, not float aggregates."""
from decimal import Decimal


def money_sum(values) -> Decimal:
    return sum((Decimal(str(v)) for v in values if v is not None), Decimal('0.00'))


def delivered_metrics(orders):
    subset = orders.loc[orders['is_delivered'].eq(True)]
    return {
        'delivered_orders': int(len(subset)),
        'merchandise': money_sum(subset['merchandise_value']),
        'freight': money_sum(subset['freight_value']),
        'gross': money_sum(subset['gross_order_value']),
    }


def assert_reconciled(metrics):
    if metrics['merchandise'] + metrics['freight'] != metrics['gross']:
        raise ValueError('Financial reconciliation failed: merchandise + freight != gross')
