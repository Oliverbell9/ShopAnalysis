FROM apache/airflow:3.3.2-python3.12

USER airflow

RUN python -m pip install --no-cache-dir \
    "apache-airflow==3.3.2" \
    "dbt-core==1.12.0" \
    "dbt-duckdb==1.11.0" \
    "duckdb==1.5.6"
