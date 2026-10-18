"""Read-only access to governed ShopAnalysis DuckDB marts."""
from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd

DEFAULT_DB = Path(__file__).resolve().parents[1] / 'data' / 'airflow_dev' / 'shopanalysis_airflow.duckdb'
EXPECTED = {
    'orders': 'fct_olist_orders',
    'monthly': 'mart_olist_monthly_revenue',
    'category': 'mart_olist_category_revenue',
    'seller': 'mart_olist_seller_revenue',
    'customer': 'mart_olist_customer_revenue',
}


def database_path() -> Path:
    override = os.environ.get('SHOPANALYSIS_BI_DB')
    return Path(override).expanduser().resolve() if override else DEFAULT_DB


def read_marts(path: Path | None = None) -> dict[str, pd.DataFrame]:
    db = (path or database_path()).resolve()
    if not db.is_file():
        raise FileNotFoundError(f'BI database does not exist: {db}')
    con = duckdb.connect(str(db), read_only=True)
    try:
        return {key: con.execute(f'SELECT * FROM main_marts."{name}"').df() for key, name in EXPECTED.items()}
    finally:
        con.close()
