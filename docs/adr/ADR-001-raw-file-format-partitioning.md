# ADR-001: Raw File Format and Partitioning

- **Decision status:** Accepted (architectural and governance policy only)
- **Implementation status:** In progress; backend enforcement not certified
- **Date:** 2026-10-01
- **Decision Owners:** ShopAnalysis Project
- **Scope:** Data ingestion and raw storage

## Context

ShopAnalysis requires a reproducible raw-data layer supporting both the reference AWS/Snowflake architecture and the permanent local DuckDB portfolio architecture.

The existing local CSV-to-Parquet converter produces one Parquet landing file per Olist entity. A separate uploader targets Garage S3-compatible object storage using date- and batch-partitioned object keys.

AWS S3 infrastructure is defined in Terraform, but the reviewed evidence does not establish that the AWS landing workflow has been deployed or validated.

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

### Option A: Hybrid local and object-storage architecture

Maintain a flat local Parquet landing layout for DuckDB and a partitioned, batch-addressed layout for S3-compatible object storage.

This is the selected architectural direction.

### Option B: Unified partitioned layout

Use the same partitioned directory structure for local storage and object storage.

Not selected. The existing local implementation uses flat entity-level Parquet files, and a unified layout is not required by the selected design.

### Option C: Defer the storage architecture decision

Retain the existing implementations without establishing a shared architectural contract.

Not selected because explicit storage and replay requirements are needed for governance and implementation validation.

## Decision

The project selects a hybrid raw-data architecture.

### Local Parquet landing

The current local Olist landing convention is:

`data/parquet/olist/<entity>.parquet`

Local DuckDB ingestion consumes validated Parquet files. The local landing directory is a replaceable working representation and does not independently establish historical batch retention.

### S3-compatible object storage

The selected logical object-key convention is:

`raw/<source>/<entity>/ingest_date=YYYY-MM-DD/batch_id=<batch_id>/part-00000.parquet`

The existing Garage uploader implements this pattern for Olist.

The ingestion date represents the UTC date of the upload operation. The batch identifier is derived deterministically from validated source-file hashes by the local converter and is carried in Parquet lineage.

This convention is the intended object-storage contract for both Garage and AWS S3. The reviewed evidence does not establish an equivalent AWS upload implementation or runtime validation.

### Protected historical batches

Both Garage and AWS S3 must enforce the following logical requirements:

1. New batch objects may be created when their target keys do not exist.
2. Repeated uploads of identical content may be treated as idempotent no-ops after content equality is verified.
3. An attempt to write different content to an existing object key must be rejected.
4. Historical batches must be protected against unintended replacement or removal under an explicit retention policy.
5. Upload outcomes must provide auditable evidence distinguishing new uploads, identical replays, and rejected conflicts.

**Approved governance policy:** Protected historical batches are retained indefinitely in `dev`, `ci`, and `prod`. Ordinary ingestion identities must not delete protected batches. Exceptional deletion requires explicit authorization by the repository/project owner, with no mandatory waiting period. Deletion execution must be separately controlled and auditable. These decisions are final; enforcement remains subject to implementation and verification.

The implementation mechanism must be validated for each storage backend. S3 versioning alone is not considered sufficient evidence of overwrite prevention.

### Source fidelity and lineage

Raw CSV source artifacts remain immutable according to the Olist source contract.

The local converter verifies source-file SHA-256 hashes and embeds lineage fields in Parquet outputs.

The object-storage workflow must preserve batch identity and provide verifiable content integrity.

## Consequences

### Benefits

- Preserves the existing local DuckDB workflow.
- Provides a portable partitioned object-storage convention.
- Makes batch identity explicit in object keys.
- Establishes consistent replay-protection requirements across Garage and AWS S3.
- Supports separation between local working files and protected historical batches.

### Tradeoffs and limitations

- Two physical landing layouts must be documented and maintained.
- Backend-specific overwrite-prevention mechanisms require implementation and validation.
- The Garage uploader implements conditional creation and SHA-256 comparison; its mocked tests do not certify live backend enforcement.
- Object-size verification does not establish cryptographic content equality.
- Local Parquet regeneration may change file bytes without changing the source-derived batch identifier.
- AWS S3 Terraform configures versioning and expiration of noncurrent versions after 30 days; this does not establish indefinite historical retention.
- Retention duration, environment scope, approval authority, and waiting-period policy are decided. Backend deletion controls and recovery verification remain outstanding.

## Validation Evidence

### Reviewed repository evidence

- `docs/source_contracts/olist.yml`: source immutability and source-fidelity requirements.
- `ingestion/landing/olist_csv_to_parquet.py`: local Parquet landing, source hash verification, and deterministic batch identification.
- `ingestion/object_store/upload_olist_to_garage.py`: Garage upload key construction, cross-entity batch consistency, and uploaded object-size verification.
- `infra/terraform/aws/s3.tf`: configured S3 public-access blocking, encryption, versioning, and noncurrent-version expiration.
- `tests/test_raw_parquet_batch_integrity.py`: local batch-integrity test definitions.

Repository source inspection is not equivalent to successful runtime validation.

### Outstanding validation and decisions

- Validate Garage conditional writes, conflict rejection, and concurrency against an authorized isolated backend.
- Define and validate equivalent protection for AWS S3.
- Verify cryptographic content equality for replay handling on each live backend.
- Implement the approved indefinite-retention and owner-authorized deletion controls for all three environments.
- Reconcile the existing 30-day noncurrent-version expiration policy with the selected retention requirements.
- Validate new-upload, identical-replay, and conflicting-replay scenarios for each backend.
- Establish deployment and runtime evidence for the AWS landing workflow.
- Complete governance review before changing ADR status to Accepted.

**Decision disposition:** The architecture and governance policy are **Accepted** by the project owner. This does not certify backend enforcement or deployment. Implementation acceptance requires separate runtime evidence.

## Approved exceptional-deletion contract

An owner authorization must identify the exact environment, bucket/backend, object key(s) and version(s) where applicable, reason, approver identity, and authorization reference. The executor must verify authorization before any delete operation. Ordinary ingestion and CI roles must not be able to invoke the exceptional deletion mechanism. Record the approval reference, actor, operation, outcome, and timestamps in durable tamper-resistant audit evidence. No waiting period is mandated.

**Design caution:** AWS S3 versioning and lifecycle expiration do not enforce this policy by themselves. Object Lock compliance retention may prevent immediate authorized deletion, while governance bypass requires carefully restricted permissions; select controls only after validating this tradeoff. Garage requires separately validated access and deletion controls. No production enforcement is certified by this document.

## Local implementation increment (review required)

The local patch adds append-and-fsync JSONL records for uploader attempts and outcomes, structural checks for owner deletion approval (without any deletion executor), explicit normal-role deletion denial in Terraform, and disables the 30-day noncurrent-version expiration rule in Terraform source. Terraform is **not applied**.

The JSONL ledger is **not tamper-resistant** and may fail after a successful remote write; such failures require reconciliation against object storage. Owner ID matching is **not authentication**, and no exceptional deletion workflow is authorized or implemented. Existing objects and live cloud permissions remain unverified.
