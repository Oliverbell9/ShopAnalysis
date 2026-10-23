# Local performance experiment protocol

The repository includes `analytics/benchmark_local.py` to measure two **read-only** DuckDB queries against an existing local mart database. It performs one warm-up and five timed runs by default, reporting minimum, median, and maximum milliseconds. It does not modify data, export records, estimate cloud credits, or create a database.

Example (replace with the actual existing database path):

```powershell
python analytics/benchmark_local.py --db data/shopanalysis.duckdb --repetitions 5
```

Record separately: hardware, CPU/RAM, OS, DuckDB version, database bytes, table row counts, query text, repetitions, cache conditions, timestamp, and raw timing outputs. Compare runs only under documented equivalent conditions.

**Not measured in this repository update:** Snowflake credit usage, warehouse-size comparisons, incremental-vs-full dbt costs, partition pruning, network transfer, and S3/Garage storage costs. Those require separate approved experiments and real billing/query-history evidence.
