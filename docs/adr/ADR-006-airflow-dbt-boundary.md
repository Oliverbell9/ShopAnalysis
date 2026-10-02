# ADR-006: Airflow and dbt Orchestration Boundary

- **Status:** Proposed
- **Date:** 2026-10-01
- **Decision Owners:** ShopAnalysis Project
- **Scope:** Workflow orchestration

## Context

ShopAnalysis uses Apache Airflow for workflow orchestration and dbt for analytical transformation.

A clear responsibility boundary is required so that scheduling, dependencies, retries, backfills, transformation logic, and data-quality execution are not duplicated across tools.

## Decision Drivers

- Separation of concerns
- Operational clarity
- Retry behavior
- Backfill support
- Observability
- Maintainability
- Testability
- Local reproducibility

## Options Considered

To be evaluated before acceptance.

## Decision

Pending evaluation.

## Consequences

To be documented after the decision is accepted.

## Validation Evidence

Pending.
