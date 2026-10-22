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

### Local Public Package Isolation Evidence — 2026-10-17

A local-only isolation test was performed using a temporary directory
outside the ShopAnalysis repository. The test package contained exactly
eight allowlisted files:

- `public_app.py`
- `public_data_access.py`
- `aggregates/executive_kpis.csv`
- `aggregates/revenue_periods.csv`
- `aggregates/customer_states.csv`
- `aggregates/product_categories.csv`
- `aggregates/payment_reconciliation.csv`
- `aggregates/repeat_customers.csv`

The following results were observed:

- All six aggregate CSV datasets passed the existing loader validation.
- The package contained eight expected files, with zero missing or
  unexpected files in the corrected isolation test.
- No DuckDB database files or `.env` files were present in the package.
- Installed direct dependencies matched `requirements-public.txt`:
  Streamlit 1.65.0, pandas 3.0.6, and Plotly 7.1.0,
  using Python 3.14.6.
- The isolated Streamlit `AppTest` execution reported zero application
  exceptions and rendered one title, six metrics, and five dataframes.
- The temporary test package was removed after execution.

The initial package-allowlist test failed after module import.
The corrected test disabled Python bytecode generation and passed.
The initial discrepancy was consistent with generated bytecode;
the original unexpected file was not independently identified.

These results demonstrate successful local aggregate-loader isolation
and isolated Streamlit test execution. They do not establish production
filesystem isolation, clean-environment dependency reproducibility,
complete disclosure protection, or authorization to redistribute data.

The public package remains a tested temporary layout, not an implemented
permanent deployment artifact. Public redistribution and deployment
remain unauthorized.

The following acceptance evidence items are tracked below. Items 1 and 2 have partial local security evidence; items 3 and 8 have local technical verification evidence. Items 4–7 remain outstanding. Criteria 1 and 2 still require complete restricted-data and deployment isolation evidence, respectively, and criterion 3 requires disclosure-policy approval:

1. Local application access controls partially verified; see the restricted-data access evidence below. Complete restricted-data isolation and formal acceptance remain outstanding.
2. Local package isolation and repository exclusion controls partially evidenced; see the criterion 2 assessment below. Production filesystem and public-interface isolation remain unverified, and formal acceptance is outstanding.
3. Technically verified against existing aggregate schema, reconciliation, and small-group validation controls; see the criterion 3 evidence below. Approved disclosure-policy requirements remain outstanding.
4. Privacy review of all approved public outputs.
5. Attribution, licensing, and publication approval.
6. Documented internal access restrictions and relevant audit evidence.
7. Snowflake role and policy implementation evidence, if that environment is deployed.
8. Technically verified for the tested local public dashboard and aggregate export; see the runtime interaction evidence below. Formal acceptance and publication approval remain pending.

### Nine-File Public Package Reproducibility Evidence — 2026-10-17

A local-only reproducibility test was completed on Windows x64
(AMD64) using Python 3.14.6. The test created a temporary public
dashboard package outside the ShopAnalysis repository and installed
its dependencies into a fresh, isolated virtual environment.

The package contained exactly nine allowlisted files:

- `public_app.py`
- `public_data_access.py`
- `requirements.txt` (copied from `dashboards/requirements-public.txt`)
- `aggregates/executive_kpis.csv`
- `aggregates/revenue_periods.csv`
- `aggregates/customer_states.csv`
- `aggregates/product_categories.csv`
- `aggregates/payment_reconciliation.csv`
- `aggregates/repeat_customers.csv`

The following results were observed:

- SHA-256 verification passed for all nine source files.
- Initial and final package allowlist checks passed.
- Fresh dependency resolution identified 38 packages.
- All 38 dependencies installed successfully in a temporary virtual environment.
- `pip check` reported no broken requirements.
- Direct dependencies were Streamlit 1.65.0, pandas 3.0.6, and Plotly 7.1.0.
- The isolated Streamlit `AppTest` rendered one title, six metrics, and five dataframes.
- The application reported zero exceptions and zero errors.
- Final SHA-256 verification confirmed the packaged files remained unchanged.
- The temporary package and virtual environment were removed after execution.
- No repository files or existing project virtual-environment packages were modified.

The initial nine-file application test failed because its test harness
did not supply the required `--export-dir` argument. Source inspection
confirmed that `public_app.py` requires this argument. After correcting
the test harness, application execution passed in both the existing
development environment and the fresh isolated environment. No
application-code change was required.

These results establish local application-level reproducibility for
the tested Windows x64 / Python 3.14.6 environment. They do not establish
long-term dependency reproducibility because transitive dependencies
are not fully pinned. Linux compatibility, production deployment
isolation, privacy approval, licensing clearance, and authorization
to redistribute data remain unverified.

The nine-file package was temporary and was not retained as a
permanent deployment artifact. Public redistribution, Git push,
and deployment remain unauthorized.

### Public Dashboard Runtime Interaction Evidence — 2026-10-17

Local Streamlit `AppTest` verification was performed using
`dashboards/public_app.py`, Streamlit 1.65.0, Plotly 7.1.0,
Python 3.14.6, and the validated aggregate export
`data/public_aggregate_exports/export_20261012T141941Z_5e2149187ff6`.

The following runtime checks passed:

- The reporting-period, customer-state, and payment-status multiselects
  updated their respective displayed data without changing unrelated
  sections or the six dashboard metrics.
- Empty selections removed their associated tables and charts without
  application errors. Restoring selections restored baseline rendering.
- The reporting-period and customer-state charts displayed the correct
  values for single-category selections; unrelated charts remained unchanged.
- The payment reconciliation chart matched all five aggregate
  classifications, and the non-exact-match chart matched the four
  applicable classifications.
- Each of the five individual payment-status selections produced the
  expected chart values and chart counts without changing unrelated
  charts or dashboard metrics.
- The reporting-period, customer-state, and product-category monetary
  selectors displayed values matching the selected `gross`,
  `merchandise`, or `freight` measure.
- Product-category top-N settings of 1, 15, and 72 displayed the
  corresponding highest-gross categories and values without changing
  unrelated charts, tables, or dashboard metrics.
- Tested control restoration returned all six Plotly chart
  specifications to their baseline state.
- The completed runtime checks reported zero application errors
  and zero application exceptions.

The checks used Plotly chart specifications exposed through
Streamlit `AppTest`, including decoding of base64-encoded numeric
arrays. The tests were executed locally without modifying application
source files or aggregate exports.

These results provide technical verification of acceptance item 8
for the tested application, export, and interactions. They do not
constitute exhaustive testing of every possible selection combination,
a production deployment assessment, privacy approval, licensing
clearance, or authorization for public redistribution.

Items 1 and 2 have partial local security evidence; items 3 and 8 have local technical verification evidence. Items 4–7 remain outstanding. Criteria 1 and 2 still require complete restricted-data and deployment isolation evidence, respectively, and criterion 3 requires disclosure-policy approval. ADR-007 remains Proposed.
Public redistribution, Git push, and deployment remain unauthorized.

### Public Aggregate Validation Evidence — 2026-10-18

Local validation evidence was collected for the existing public aggregate
generator, public data loader, dashboard metrics, and validated aggregate
export `data/public_aggregate_exports/export_20261012T141941Z_5e2149187ff6`.

The three existing pytest modules completed with 26 tests passed,
four skipped, and zero failed. All four skips involved unavailable
Windows symbolic-link creation privileges. Consequently, those
real-filesystem symlink scenarios were not verified by this run.

Existing validation controls check exact dataset inventories and schemas,
expected row counts, grouping-key uniqueness, monetary reconciliation,
delivered-order parity, and expected classification totals. Earlier
aggregate checks also confirmed monetary parity across reporting periods,
customer states, and product categories.

Additional local in-memory negative tests confirmed that the generator
rejects a count of 9 in each of the reporting-period, customer-state,
and product-category datasets. For reporting periods and states,
the tests preserved the overall delivered-order total so the
small-group rejection branch could be reached.

The repeat-customer dataset is constrained to exact group counts of
90,557 and 2,801. Its subsequent minimum-count check of 10 is
redundant for data that satisfy those earlier fixed-count requirements;
the minimum-count rejection branch was not independently exercised.

The validated published export produced the following group diagnostics:

| Dataset | Groups | Minimum count | Below 10 | Below 50 |
| --- | ---: | ---: | ---: | ---: |
| Revenue periods | 21 | 267 | 0 | 0 |
| Customer states | 27 | 41 | 0 | 1 |
| Product categories | 72 | 12 | 0 | 13 |
| Payment reconciliation | 5 | 39 | 0 | 1 |
| Repeat customers | 2 | 2801 | 0 | 0 |
| **Total** | **127** | **12** | **0** | **15** |

All 127 published groups satisfy the implemented minimum count of 10.
The 15 groups below 50 are a diagnostic inventory, not a finding
that an approved disclosure threshold has been violated.

The threshold of 10 is an existing technical validation control,
not an approved privacy-disclosure standard. Small-group linkage,
exact financial disclosures, complementary disclosure risks, and
formal disclosure-policy approval remain unresolved.

This evidence supports technical verification of criterion 3 against
the current implemented controls and tested export. It does not
establish complete privacy clearance or formal ADR acceptance.

### Public Restricted-Data Access Evidence — 2026-10-18

Local read-only inspection examined `dashboards/public_app.py`,
`dashboards/public_data_access.py`, and existing public data-access tests.

The inspected dashboard uses `load_public_aggregates()` to obtain
analytical data. No direct DuckDB, Parquet, or Snowflake access path
was identified in the inspected public application and loader.
The application accepts an explicit `--export-dir` launch argument;
this is process configuration, not a dashboard filter.

The loader enforces the six expected aggregate CSV filenames,
validates CSV schemas and expected row counts, applies file and
field size limits, and validates aggregate content and reconciliation.
It checks path components for symbolic links and Windows junctions.

The CSV inventory check does not reject unrelated non-CSV files
within the supplied directory. This observation does not establish
that such files are retrievable through the dashboard.

Existing negative tests cover missing and unexpected CSV files,
invalid schemas, altered totals, invalid payment classifications,
excess rows, oversized files, invalid UTF-8, and malformed CSV data.

A targeted local filesystem security test run produced one pass,
two skips, and zero failures. Windows junction rejection passed.
CSV-file and directory symbolic-link tests were skipped because
symbolic-link creation was unavailable in the tested Windows
environment. Runtime symbolic-link rejection therefore remains
unverified by those tests.

Three additional temporary-input negative checks passed:
a database file supplied as the export directory was rejected;
a directory containing an unexpected CSV was rejected; and a
directory containing only a dummy database file was rejected.
These tests used placeholders and did not open internal project
databases or restricted datasets.

A Streamlit `AppTest` using a temporary directory containing a
dummy database placeholder confirmed fail-closed application
behavior. The dashboard displayed its aggregate-validation error,
rendered zero analytical metrics, produced zero application
exceptions, and displayed no successful-validation message.

These findings support partial local verification of acceptance
criterion 1 for the inspected application, loader, and tested
invalid-input scenarios. They do not establish that every possible
restricted-data access path is blocked.

Complete restricted-dataset isolation, public-interface security,
deployment filesystem permissions, package contents, and production
access restrictions remain unverified. These require separate
evidence before formal acceptance or public deployment.

### Public Deployment Isolation Assessment — 2026-10-18

This assessment reviewed existing local package evidence, Git tracking
and ignore rules, deployment-related source references, Docker
configuration, and local runtime observations. It did not create or
deploy a public application.

The documented nine-file public package contains exactly two public
Python modules, one public requirements file, and six validated
aggregate CSV files. Earlier local tests confirmed package allowlist
integrity, SHA-256 verification, dependency installation in a fresh
Windows x64 / Python 3.14.6 environment, and successful Streamlit
`AppTest` execution. The package was temporary and was removed.

A subsequent read-only source inventory confirmed that all nine
allowlisted files existed, none was a symbolic link or Windows
junction, and their combined size was 31,370 bytes. The specified
allowlist excludes the identified internal dashboard, DuckDB access
module, aggregate generator, internal requirements file, database
files, and environment files. This inventory did not construct or
inspect a deployment artifact.

Git tracking inspection identified zero tracked `.duckdb` or
`.parquet` files. Ignore-rule inspection and ignored-file enumeration
identified five project DuckDB databases, 18 project Parquet datasets,
five Parquet files within the Python virtual environment, and two
local `.env` files excluded from Git tracking.

The tracked environment templates contained placeholder or empty
values in the inspected credential-related matches. This was not
a comprehensive repository-wide secret scan.

Git exclusions reduce accidental inclusion in commits but do not
prevent a deployment process from copying ignored local files.
The repository therefore must not be treated as equivalent to the
nine-file public package.

The tracked deployment-related inventory identified the root Docker
Compose configuration, Airflow Docker Compose configuration, and
Airflow Dockerfile. No dedicated public Streamlit deployment
configuration or public dashboard deployment script was identified
by the inspected filename and source-reference searches.

The root Docker Compose configuration defines Garage object storage
with published host ports 3900 and 3901 without explicit host-IP
restrictions. The Airflow configuration defines internal services
that mount restricted processing data, including the Airflow
workspace and raw Olist source directory. Its API server publishes
port 8080 with an explicit `127.0.0.1` host binding. Neither
inspected Compose configuration defines a public Streamlit service.

These configuration findings do not establish external network
reachability, authorization behavior, or actual public exposure.

A Docker runtime inventory was attempted but could not connect to
the Docker Desktop Linux engine. Consequently, active Docker
container state and runtime port bindings were not verified.

A separate Windows host inspection reported no matching
Streamlit/Python processes and no listeners on ports 8501, 8502,
8080, 3900, or 3901 at the time of inspection. This limited
observation does not prove that other ports, hosts, containers,
or public interfaces are inaccessible.

The findings provide partial local evidence supporting the
nine-file package isolation design and existing repository
exclusion controls. They do not satisfy acceptance criterion 2.

An implemented public deployment boundary, enforced package
allowlist, production filesystem permissions, verification that
internal DuckDB and Parquet files cannot be retrieved through
public interfaces, and appropriate runtime/network security
evidence remain outstanding.

ADR-007 remains Proposed. Public redistribution, Git push,
and deployment remain unauthorized.

## Decision Status

Proposed. Acceptance is pending implementation and validation evidence.
