# ADR-001: Raw File Format and Partitioning

- **Status:** Proposed
- **Date:** 2026-10-01
- **Decision Owners:** ShopAnalysis Project
- **Scope:** Data ingestion and raw storage

## Context

ShopAnalysis requires a reproducible raw-data layer supporting both the reference AWS/Snowflake architecture and the permanent local portfolio architecture.

The target cloud landing convention is:

`raw/<source>/<entity>/ingest_date=YYYY-MM-DD/part-*.parquet`

Raw data must preserve source fidelity, support lineage, enable replay, and remain suitable for downstream ingestion into Snowflake and DuckDB.

## Decision Drivers

- Reproducibility
- Immutability
- Storage efficiency
- Query efficiency
- Cross-platform portability
- Lineage
- Idempotent reprocessing
- Long-term portfolio reproducibility

## Options Considered

To be evaluated before acceptance.

## Decision

Pending evaluation.

## Consequences

To be documented after the decision is accepted.

## Validation Evidence

Pending.
