# Governed RAW Ingestion

## Purpose

ShopAnalysis uses application-level governance enforcement for
Olist RAW ingestion into DuckDB.

The supported entry point is:

`observability.governed_raw_entrypoint.run_governed_raw_ingestion`

Direct execution of `ingestion.duckdb.load_olist_raw.main`
is not a supported application workflow.

## Required inputs

The governed entry point requires explicit arguments:

- `raw_database`: target DuckDB RAW database path
- `audit_database`: initialized observability DuckDB database path
- `parquet_root`: directory containing the Olist Parquet entities
- `environment`: nonblank execution environment identifier

## Execution contract

1. Validate input paths and environment.
2. Verify that RAW and audit database paths are distinct.
3. Verify compatibility with the required audit schema.
4. Discover and validate all nine Olist Parquet entities.
5. Require a consistent, non-null batch ID.
6. Start governed pipeline and stage audit records.
7. Execute RAW loading with a valid CommitTracker.
8. Reconcile committed RAW data against source counts.
9. Record quality evidence and validate audit evidence.
10. Finalize the governed audit lifecycle when validation succeeds.

## Transaction and recovery behavior

Commit tracking distinguishes:

- `NOT_COMMITTED`
- `ROLLED_BACK`
- `COMMITTED`
- `UNKNOWN`

Failures without a confirmed rollback must not be
misrepresented as safely rolled back.

Post-commit audit failures require separate recovery handling.

## Enforcement boundary

The loader requires an internal governance token and a
valid CommitTracker.

This is an application-level execution guard. It prevents
accidental direct execution through normal application
workflows but is not a security boundary against arbitrary
Python code executing in the same process.

The internal token is not a security credential.

## Validation

The repository's pytest suite includes:

- Mandatory governance enforcement tests
- Preflight validation tests
- Parquet batch-integrity tests
- Commit-boundary tests
- Governed entry-point tests
- Isolated end-to-end ingestion tests
- Pipeline recovery tests

Tests use isolated databases or mocks rather than
intentionally modifying production RAW or audit databases.

## Operational restriction

Do not execute governed ingestion against production RAW
or audit databases without explicit operational authorization.
