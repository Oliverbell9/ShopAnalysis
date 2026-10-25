"""Read-only local DuckDB performance evidence; never creates or modifies the database."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import sys
from pathlib import Path

from analytics.benchmark_local import QUERIES, measure


def build_evidence(connection, *, db_path: Path, repetitions: int, duckdb_version: str, notes: str = "") -> dict:
    if not 1 <= repetitions <= 100:
        raise ValueError("repetitions must be between 1 and 100")
    if not db_path.is_file():
        raise FileNotFoundError("Existing DuckDB database required")
    measurements = {}
    for name, query in QUERIES.items():
        measurements[name] = {
            "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            **measure(connection, query, repetitions),
        }
    return {
        "schema_version": 1,
        "status": "MEASURED_LOCAL_ONLY",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "duckdb": duckdb_version,
            "database_bytes": db_path.stat().st_size,
            "database_name": db_path.name,
        },
        "method": {"warmup_runs_per_query": 1, "timed_runs_per_query": repetitions,
                   "clock": "time.perf_counter", "cache_condition": "not controlled"},
        "measurements": measurements,
        "operator_notes": notes,
        "limitations": [
            "Measurements are local elapsed times, not server-side execution plans or cloud costs.",
            "Cache state, machine load, and hardware comparability are not controlled.",
            "No production performance or SLA is certified by this report.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--notes", default="")
    parser.add_argument("--output", type=Path, help="Optional JSON report path; must not already exist")
    args = parser.parse_args(argv)
    if not 1 <= args.repetitions <= 100:
        parser.error("--repetitions must be between 1 and 100")
    if not args.db.is_file():
        parser.error("Database must exist; refusing to create one")
    if args.output is not None and args.output.exists():
        parser.error("Output already exists; refusing to overwrite")
    import duckdb
    con = duckdb.connect(str(args.db.resolve()), read_only=True)
    try:
        report = build_evidence(con, db_path=args.db, repetitions=args.repetitions,
                                duckdb_version=duckdb.__version__, notes=args.notes)
    finally:
        con.close()
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        # Exclusive create; avoids races and accidental replacement of existing evidence.
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(serialized)
        print(f"Evidence saved: {args.output}")
    else:
        sys.stdout.write(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
