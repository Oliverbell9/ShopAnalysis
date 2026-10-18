# ADR-007: RBAC and Access Model

- **Status:** Proposed
- **Date:** 2026-10-01
- **Decision Owners:** ShopAnalysis Project
- **Scope:** Security and governance

## Context

ShopAnalysis requires governed access to raw, transformed, and analytical data.

The platform must demonstrate role-based access control, PII protection, masking, appropriate row-level restrictions where required, pseudonymization, and auditable access patterns.

ShopAnalysis is a data engineering and analytics knowledge-base and portfolio project.

The public dashboard must be interactive and accessible without visitor registration or sign-in. Public access does not imply access to internal analytical tables, source files, or database connections.

The existing implementation includes:

- DuckDB-backed ingestion and dbt analytical models.
- An internal Streamlit dashboard that reads DuckDB marts directly.
- A separate public Streamlit dashboard that reads validated aggregate CSV files.
- A public aggregate generator with predefined queries and validation rules.

These observations establish existing code paths, not a completed production security assessment.

## Decision Drivers

- Least privilege
- PII protection
- Separation of duties
- Auditability
- Administrative simplicity
- Environment isolation
- BI access requirements
- Reproducibility
- Interactive public portfolio access without visitor authentication
- Protection against bypassing the public aggregate boundary
- Equivalent logical access outcomes across local and Snowflake environments

## Options Considered

### Option A: Public dashboard with direct DuckDB access

Allow the publicly accessible dashboard to query the existing DuckDB marts.

Advantages:

- Reuses the internal analytical database.
- Supports flexible interactive queries.

Disadvantages:

- Exposes a direct route to restricted analytical datasets.
- Requires additional authorization and query restrictions.
- Increases the risk of unintended disclosure through filters or query behavior.

Assessment: Not selected for the proposed public access boundary.

### Option B: Public dashboard using validated aggregate exports

Retain the separate public Streamlit application and supply only predefined, validated aggregate datasets.

Advantages:

- Separates public reporting from restricted source and mart data.
- Supports interactive visualizations using approved aggregate fields.
- Builds on the existing public dashboard and aggregate-validation code.
- Avoids unnecessary visitor identity management.

Disadvantages:

- Arbitrary cross-dimensional filtering is unavailable unless corresponding approved aggregate data exists.
- Aggregate validation does not substitute for privacy review or publication approval.
- Export generation and deployment isolation must be controlled.

Assessment: Preferred option for public reporting.

### Option C: Authenticated public dashboard with an OIDC provider

Require visitors to authenticate before accessing portfolio analytics.

Advantages:

- Enables identity-based access decisions.
- Supports individual access records where implemented.

Disadvantages:

- Conflicts with the confirmed requirement for public viewing without sign-in.
- Adds identity-provider and session-management dependencies.
- Does not independently protect DuckDB or Parquet files.

Assessment: Not required for public portfolio visitors.

## Proposed Decision

ShopAnalysis will retain a separate, publicly accessible, interactive Streamlit dashboard without visitor authentication.

The public application will consume only predefined aggregate exports that have passed schema, reconciliation, privacy, and publication-approval checks.

Public dashboard users will not receive direct access to:

- RAW source datasets.
- DuckDB database files.
- Parquet landing or processing files.
- Customer-level or seller-level restricted marts.
- Arbitrary SQL execution against internal analytical databases.

Internal ingestion, transformation, observability, and administrative operations will use controlled execution identities and least-privilege access to the underlying files and databases.

The existing internal DuckDB dashboard will remain a development and restricted analytical component unless a separate deployment security review authorizes broader access.

Snowflake will implement equivalent logical access outcomes through platform-supported roles, grants, and additional security policies where justified.

This proposal does not assert that Snowflake RBAC, masking, row-access policies, or production filesystem isolation have already been implemented.

## Proposed Logical Access Matrix

| Role | RAW and landing data | Restricted analytical marts | Approved aggregates | Security administration |
|---|---|---|---|---|
| Platform administrator | Controlled administrative access | Controlled administrative access | Allowed | Allowed |
| Data engineer | Required processing access | Required processing access | Allowed | Not by default |
| Data analyst | Denied by default | Explicitly approved datasets only | Allowed | Denied |
| Internal BI consumer | Denied | Denied by default | Allowed | Denied |
| Anonymous public visitor | Denied | Denied | Publication-approved exports only | Denied |

All permissions are proposed logical requirements, not verified deployed grants.

## Data Protection Requirements

- Classify customer identifiers and other linkable fields before granting detailed access.
- Evaluate masking or pseudonymization where restricted analytical use requires those fields.
- Apply row-level restrictions only where an established access requirement justifies them.
- Restrict direct filesystem and database access so public application users cannot bypass the approved aggregate boundary.
- Do not treat a read-only DuckDB connection as user-level RBAC.
- Record privileged access and relevant security failures through appropriate platform-supported mechanisms.
- Deny access when required authorization or data validation fails.

## Public Dashboard Interactivity

The public dashboard may provide charts, tables, sorting, and filters over approved aggregate datasets.

A filter must not imply a multidimensional analytical relationship that the underlying aggregate data does not support.

Additional cross-filtering requirements must be supported by separately defined, privacy-reviewed aggregate datasets before implementation.

The existing public aggregate validation is a technical safeguard, not final authorization to publish.

## Consequences

### Expected benefits

- Public visitors can explore portfolio analytics without creating accounts.
- Existing public aggregate safeguards remain reusable.
- Internal processing and public reporting retain separate data-access boundaries.
- Unnecessary identity infrastructure is avoided.

### Trade-offs and responsibilities

- Public interactivity is constrained by approved aggregate granularity.
- Deployment configuration must prevent direct access to internal data assets.
- Public aggregate exports require privacy, attribution, licensing, and publication review.
- Local and Snowflake enforcement may use different technologies while targeting equivalent authorization outcomes.

## Validation Evidence

Existing inspected code provides evidence of:

- Read-only DuckDB access in the internal dashboard.
- Separate CSV-only access in the public dashboard.
- Fixed public aggregate schemas and validation checks.
- Customer-level and seller-level identifiers in restricted marts.

The following acceptance evidence remains outstanding:

1. Tests confirming the public application cannot retrieve restricted datasets.
2. Deployment verification that internal DuckDB and Parquet files are inaccessible through public interfaces.
3. Tests for aggregate schema, reconciliation, and small-group restrictions.
4. Privacy review of all approved public outputs.
5. Attribution, licensing, and publication approval.
6. Documented internal access restrictions and relevant audit evidence.
7. Snowflake role and policy implementation evidence, if that environment is deployed.
8. Verification that public interactive filters do not misrepresent unsupported cross-dimensional results.

## Decision Status

Proposed. Acceptance is pending implementation and validation evidence.
