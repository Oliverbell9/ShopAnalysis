# ADR-002: Ingestion Method

- **Status:** Proposed
- **Date:** 2026-10-01
- **Decision Owners:** ShopAnalysis Project
- **Scope:** Source-to-RAW ingestion

## Context

ShopAnalysis must support reliable, observable, and idempotent ingestion into the analytical platform.

The reference cloud architecture will evaluate Snowflake COPY INTO and Snowpipe. The permanent architecture must remain reproducible using local files or Garage with Parquet and DuckDB.

## Decision Drivers

- Idempotency
- Recoverability
- Batch and micro-batch support
- Operational complexity
- Cost
- Observability
- Schema evolution
- Lineage
- Portability

## Options Considered

To be evaluated before acceptance.

## Decision

Pending evaluation.

## Consequences

To be documented after the decision is accepted.

## Validation Evidence

Pending.
