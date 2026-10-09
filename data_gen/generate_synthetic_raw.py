"""Create an isolated, deterministic Olist-compatible DuckDB RAW fixture."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import duckdb

COLUMNS = {
    'olist_customers': [('customer_id','VARCHAR'),('customer_unique_id','VARCHAR'),('customer_zip_code_prefix','BIGINT'),('customer_city','VARCHAR'),('customer_state','VARCHAR')],
    'olist_geolocation': [('geolocation_zip_code_prefix','BIGINT'),('geolocation_lat','DOUBLE'),('geolocation_lng','DOUBLE'),('geolocation_city','VARCHAR'),('geolocation_state','VARCHAR')],
    'olist_order_items': [('order_id','VARCHAR'),('order_item_id','BIGINT'),('product_id','VARCHAR'),('seller_id','VARCHAR'),('shipping_limit_date','VARCHAR'),('price','DOUBLE'),('freight_value','DOUBLE')],
    'olist_orders': [('order_id','VARCHAR'),('customer_id','VARCHAR'),('order_status','VARCHAR'),('order_purchase_timestamp','VARCHAR'),('order_approved_at','VARCHAR'),('order_delivered_carrier_date','VARCHAR'),('order_delivered_customer_date','VARCHAR'),('order_estimated_delivery_date','VARCHAR')],
    'olist_payments': [('order_id','VARCHAR'),('payment_sequential','BIGINT'),('payment_type','VARCHAR'),('payment_installments','BIGINT'),('payment_value','DOUBLE')],
    'olist_products': [('product_id','VARCHAR'),('product_category_name','VARCHAR'),('product_name_lenght','DOUBLE'),('product_description_lenght','DOUBLE'),('product_photos_qty','DOUBLE'),('product_weight_g','DOUBLE'),('product_length_cm','DOUBLE'),('product_height_cm','DOUBLE'),('product_width_cm','DOUBLE')],
    'olist_reviews': [('review_id','VARCHAR'),('order_id','VARCHAR'),('review_score','BIGINT'),('review_comment_title','VARCHAR'),('review_comment_message','VARCHAR'),('review_creation_date','VARCHAR'),('review_answer_timestamp','VARCHAR')],
    'olist_sellers': [('seller_id','VARCHAR'),('seller_zip_code_prefix','BIGINT'),('seller_city','VARCHAR'),('seller_state','VARCHAR')],
    'olist_translation': [('product_category_name','VARCHAR'),('product_category_name_english','VARCHAR')],
}
LINEAGE = [('_source_file','VARCHAR'),('_file_row_number','BIGINT'),('_loaded_at','TIMESTAMP WITH TIME ZONE'),('_batch_id','VARCHAR')]
LOADED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

ROWS = {
    'olist_customers': [
        ('CI-CUST-001','CI-UNIQUE-A',10001,'city_a','SP'),
        ('CI-CUST-002','CI-UNIQUE-A',20002,'city_b','RJ'),
        ('CI-CUST-003','CI-UNIQUE-B',30003,'city_c','MG'),
        ('CI-CUST-004','CI-UNIQUE-C',40004,'city_d','SP'),
        ('CI-CUST-005','CI-UNIQUE-D',50005,'city_e','BA'),
        ('CI-CUST-006','CI-UNIQUE-E',60006,'city_f','SP'),
        ('CI-CUST-007','CI-UNIQUE-F',70007,'city_g','RJ'),
    ],
    'olist_geolocation': [(10001,-23.55,-46.63,'city_a','SP'),(20002,-22.91,-43.20,'city_b','RJ')],
    'olist_order_items': [
        ('CI-ORD-001',1,'CI-PROD-1','CI-SELLER-1','2025-01-05 12:00:00',100.00,10.00),
        ('CI-ORD-001',2,'CI-PROD-2','CI-SELLER-2','2025-01-05 12:00:00',50.00,5.00),
        ('CI-ORD-002',1,'CI-PROD-1','CI-SELLER-1','2025-02-05 12:00:00',20.00,2.00),
        ('CI-ORD-003',1,'CI-PROD-2','CI-SELLER-2','2025-03-05 12:00:00',30.00,3.00),
        ('CI-ORD-004',1,'CI-PROD-1','CI-SELLER-1','2025-04-05 12:00:00',40.00,4.00),
        ('CI-ORD-005',1,'CI-PROD-2','CI-SELLER-2','2025-05-05 12:00:00',50.00,5.00),
        ('CI-ORD-007',1,'CI-PROD-1','CI-SELLER-1','2025-07-05 12:00:00',70.00,7.00),
    ],
    'olist_orders': [],
    'olist_payments': [
        ('CI-ORD-001',1,'credit_card',1,165.00),
        ('CI-ORD-002',1,'credit_card',1,22.01),
        ('CI-ORD-003',1,'credit_card',1,40.00),
        ('CI-ORD-004',1,'boleto',1,40.00),
        ('CI-ORD-006',1,'voucher',1,12.00),
        ('CI-ORD-007',1,'credit_card',1,77.00),
    ],
    'olist_products': [
        ('CI-PROD-1','livros',10.0,20.0,1.0,100.0,10.0,2.0,8.0),
        ('CI-PROD-2','brinquedos',12.0,24.0,2.0,200.0,20.0,4.0,12.0),
    ],
    'olist_reviews': [('CI-REVIEW-001','CI-ORD-001',5,'good','synthetic review','2025-01-10 12:00:00','2025-01-11 12:00:00')],
    'olist_sellers': [('CI-SELLER-1',10001,'city_a','SP'),('CI-SELLER-2',20002,'city_b','RJ')],
    'olist_translation': [('livros','books'),('brinquedos','toys')],
}
for i in range(1,8):
    month = f'{i:02d}'
    delivered = i <= 4
    ROWS['olist_orders'].append((
        f'CI-ORD-{i:03d}', f'CI-CUST-{i:03d}',
        'delivered' if delivered else 'canceled',
        f'2025-{month}-01 10:00:00',f'2025-{month}-01 11:00:00',
        f'2025-{month}-06 12:00:00' if delivered else None,
        f'2025-{month}-09 12:00:00' if delivered else None,
        f'2025-{month}-15 12:00:00',
    ))

EXPECTED = {
    'CI-ORD-001':'exact_match',
    'CI-ORD-002':'within_one_cent',
    'CI-ORD-003':'payment_above_item_plus_freight',
    'CI-ORD-004':'payment_below_item_plus_freight',
    'CI-ORD-005':'missing_payment',
    'CI-ORD-006':'missing_items',
    'CI-ORD-007':'exact_match',
}

def generate(path: Path) -> None:
    path = path.resolve()
    if path.name != 'shopanalysis_ci.duckdb':
        raise ValueError('Refusing to write: database filename must be shopanalysis_ci.duckdb')
    if path.exists():
        raise FileExistsError(f'Refusing to overwrite existing CI database: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    try:
        con.execute('BEGIN TRANSACTION')
        con.execute('CREATE SCHEMA raw')
        for table, columns in COLUMNS.items():
            all_columns = columns + LINEAGE
            ddl = ', '.join(f'"{name}" {dtype}' for name, dtype in all_columns)
            con.execute(f'CREATE TABLE raw."{table}" ({ddl})')
            values = [tuple(row) + (f'synthetic/{table}.csv', i, LOADED_AT, 'CI-FIXTURE-001') for i,row in enumerate(ROWS[table],start=1)]
            if values:
                placeholders = ', '.join(['?'] * len(all_columns))
                con.executemany(f'INSERT INTO raw."{table}" VALUES ({placeholders})', values)
            count = con.execute(f'SELECT COUNT(*) FROM raw."{table}"').fetchone()[0]
            assert count == len(ROWS[table]), (table,count,len(ROWS[table]))
            print(f'PASS raw.{table}: {count} rows, {len(all_columns)} columns')
        assert len(ROWS['olist_orders']) == len(EXPECTED) == 7
        con.execute('COMMIT')
        print('PASS: isolated synthetic RAW fixture created; seven expected scenarios defined.')
    except Exception:
        con.execute('ROLLBACK')
        con.close()
        path.unlink(missing_ok=True)
        raise
    finally:
        try:
            con.close()
        except Exception:
            pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', type=Path, default=Path('data/shopanalysis_ci.duckdb'))
    args = parser.parse_args()
    generate(args.database)
