# ADR-004: dbt Materialization Policy

- **Status:** Proposed
- **Date:** 2026-10-01
- **Decision Owners:** ShopAnalysis Project
- **Scope:** dbt transformation architecture

## Context

ShopAnalysis uses dbt STAGING, INTERMEDIATE, and MARTS layers.

The project must determine appropriate materializations for each layer while considering correctness, runtime, warehouse cost, maintainability, incremental processing, and cross-platform compatibility.

## Decision Drivers

- Correctness
- Build performance
- Warehouse cost
- Maintainability
- Incremental processing
- Testability
- Snowflake and DuckDB compatibility

## Options Considered

To be evaluated before acceptance.

## Decision

Pending evaluation.

## Consequences

To be documented after the decision is accepted.

## Validation Evidence

Pending.
