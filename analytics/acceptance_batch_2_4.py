"""Read-only cross-mart acceptance for ShopAnalysis milestones 3 and 4.

Never creates or mutates a DuckDB database. Use against an existing, validated mart DB.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

MARTS = {
    'orders': 'fct_olist_orders',
    'monthly': 'mart_olist_monthly_revenue',
    'customer': 'mart_olist_customer_revenue',
    'category': 'mart_olist_category_revenue',
    'seller': 'mart_olist_seller_revenue',
}
METRICS = ('gross_merchandise_revenue', 'freight_value', 'gross_order_value')


def decimal_value(value):
    if value is None:
        return Decimal('0')
    if isinstance(value, float):
        raise ValueError('Unexpected floating-point monetary result')
    return Decimal(str(value))


def compare_totals(baseline, candidate, label):
    """Return exceptions, rather than silently assuming equality."""
    problems = []
    for metric in METRICS:
        if decimal_value(baseline[metric]) != decimal_value(candidate[metric]):
            problems.append({'mart': label, 'metric': metric,
                             'expected': str(baseline[metric]),
                             'observed': str(candidate[metric])})
    return problems


def _aggregate(con, table, columns, where=''):
    expression = ', '.join(f'coalesce(sum({column}), 0) as {alias}'
                           for alias, column in columns.items())
    cursor = con.execute(f'SELECT {expression} FROM main_marts."{table}" {where}')
    return dict(zip((col[0] for col in cursor.description), cursor.fetchone()))


def inspect(path: Path):
    import duckdb
    if not path.is_file():
        raise FileNotFoundError(path)
    con = duckdb.connect(str(path.resolve()), read_only=True)
    try:
        for table in MARTS.values():
            con.execute(f'SELECT 1 FROM main_marts."{table}" LIMIT 0')
        order_totals = _aggregate(con, MARTS['orders'], {
            'gross_merchandise_revenue': 'merchandise_value',
            'freight_value': 'freight_value',
            'gross_order_value': 'gross_order_value',
        }, 'WHERE is_delivered = true')
        checks = {}
        discrepancies = []
        for label in ('monthly', 'customer', 'category', 'seller'):
            actual = _aggregate(con, MARTS[label], {name: name for name in METRICS})
            checks[label] = {name: str(decimal_value(actual[name])) for name in METRICS}
            discrepancies.extend(compare_totals(order_totals, actual, label))
        arithmetic = (decimal_value(order_totals['gross_merchandise_revenue'])
                      + decimal_value(order_totals['freight_value'])
                      == decimal_value(order_totals['gross_order_value']))
        if not arithmetic:
            discrepancies.append({'mart': 'orders', 'metric': 'arithmetic',
                                  'detail': 'merchandise + freight != gross'})
        count = con.execute('SELECT count(*) FROM main_marts.fct_olist_orders').fetchone()[0]
        delivered = con.execute('SELECT count(*) FROM main_marts.fct_olist_orders WHERE is_delivered = true').fetchone()[0]
        duplicate = con.execute('SELECT count(*) - count(DISTINCT order_id) FROM main_marts.fct_olist_orders').fetchone()[0]
        if duplicate:
            discrepancies.append({'mart': 'orders', 'metric': 'order_id_uniqueness', 'duplicates': duplicate})
        checks['orders'] = {name: str(decimal_value(order_totals[name])) for name in METRICS}
        return {'status': 'PASS' if not discrepancies else 'FAIL',
                'orders': count, 'delivered_orders': delivered,
                'mart_totals': checks, 'discrepancies': discrepancies,
                'limitations': [
                    'This validates delivered gross-value parity, not payment settlement or net revenue.',
                    'Category and seller marts must preserve all delivered order items for parity.',
                    'This does not certify AWS/Garage retention or authenticated owner approval.',
                ]}
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--output', type=Path, help='Optional JSON report; parent directory must exist')
    args = parser.parse_args()
    result = inspect(args.db)
    report = json.dumps(result, indent=2)
    print(report)
    if args.output:
        if not args.output.parent.is_dir():
            parser.error('Report parent directory must already exist')
        args.output.write_text(report + '\n', encoding='utf-8')
    raise SystemExit(0 if result['status'] == 'PASS' else 1)

if __name__ == '__main__':
    main()
