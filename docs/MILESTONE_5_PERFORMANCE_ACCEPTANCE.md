# Milestone 5 — Local Performance Evidence and Documentation

## Existing baseline

The repository already provides `analytics/benchmark_local.py`, its synthetic tests, and `docs/performance_experiment_protocol.md`. The new `analytics/performance_evidence.py` **reuses** that benchmark's query definitions and measurement function. It does not replace them.

## Run (PowerShell, from repository root)

```powershell
python -m pytest tests/test_performance_evidence.py -q
python -m pytest -q -rs
python -m analytics.performance_evidence --db "data/airflow_dev/shopanalysis_airflow.duckdb" --repetitions 7 --notes "Local development workstation; cache not controlled"
```

The final command writes no files and opens DuckDB read-only. To save a **new** report in an explicitly chosen directory, append `--output "<new_path>.json"`; existing reports cannot be overwritten. Avoid putting reports inside protected data directories. Inspect the output for sensitive machine information before sharing.

## Interpretation

- Evidence contains timestamp, OS, Python/DuckDB versions, database size, SQL SHA-256 fingerprints, warm-up/timed-run methodology, and min/median/max milliseconds.
- No query-result rows are exported. Query performance can vary with hardware, cache, background activity, and DB version.
- **No numerical performance acceptance threshold is assumed.** The measured values must be reviewed and a target agreed before claiming a performance SLA.
- This is **not** evidence of Snowflake credit consumption, AWS/Garage costs, partition pruning, production throughput, live alert delivery, or cloud retention enforcement.
- Milestone 3 delivered gross-value reconciliation was previously verified; Milestone 4 local automated tests passed. Production-only gaps remain open.

## Milestone 5 acceptance gates

1. Benchmark harness tests pass.
2. A real read-only benchmark is run against the existing local DuckDB database.
3. Report captures measurement method and environment, with no invented cloud metrics.
4. Existing architecture/runbook documentation is reviewed for consistency; no production certification is claimed.
5. Milestone 6 final acceptance retains explicit limitations and five Windows symlink skips until executed in a suitable environment.
