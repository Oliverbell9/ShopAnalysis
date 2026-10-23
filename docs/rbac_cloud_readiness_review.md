# RBAC and Cloud-Security Readiness — Code Review

**Assessment type:** repository-source inspection only. **Status:** evidence gathering, not security certification. No infrastructure was provisioned or changed; no live AWS permissions were tested.

## Reviewed files

- `docs/adr/ADR-007-rbac-access-model.md` (Proposed)
- `infra/terraform/aws/iam.tf`, `oidc.tf`, `s3.tf`, `providers.tf`
- `.github/workflows/aws-s3-access-check.yml`
- `infra/garage/garage.toml`
- `dashboards/data_access.py`, `dashboards/public_data_access.py`

## Observations and evidence gaps

| Control | Observed in repository | Unverified / required evidence |
| --- | --- | --- |
| Public reporting boundary | Public dashboard data loader reads six fixed CSV aggregates; internal loader directly queries DuckDB marts read-only. | Actual deployed artifact contents, process/file permissions, network boundaries, privacy approval, and public publishing authorization. |
| Logical RBAC | ADR-007 proposes roles and least-privilege matrix; ADR status is **Proposed**. | Deployed role/grant inventory and positive/negative access tests. A read-only DuckDB connection is not user-level RBAC. |
| AWS workload federation | Terraform defines a GitHub OIDC provider and environment-scoped IAM roles; workflow requests `id-token: write` for a manually selected GitHub environment. | Actual IAM trust documents, GitHub Environment configuration/protection rules, STS caller identity, and denied cross-environment operations. |
| OIDC subject | `iam.tf` sets `github_repository = "Oliverbell9@92740323/ShopAnalysis@1401892624"` and builds `repo:${local.github_repository}:environment:${each.key}`. | **Potential configuration mismatch:** compare the literal value with the actual `sub` claim from GitHub's OIDC token for each environment. Do not assume authentication works. Standard repository subject format uses owner/repository, not this annotated string; confirm before any change. |
| S3 permissions | Environment role policy allows `ListBucket` restricted by prefix, `GetObject`/`PutObject` on that prefix, and `DeleteObject` for dev/ci but not prod. | IAM policy simulation or live positive/negative tests, including cross-prefix denial and production delete denial. Explicit absence of a role allow does not alone prove denial if other policies or grants exist. |
| S3 bucket safeguards | Terraform declares public-access block, AES256 default encryption, versioning, BucketOwnerEnforced ownership, and 30-day noncurrent-version expiration. | Confirm actual bucket configuration, policy, ACL/public-access findings, encryption enforcement, logging, retention expectations and drift. |
| AWS access-check workflow | Manual workflow tests STS identity and an environment-prefix list operation. | Does not test GetObject, PutObject, denied operations, prod delete denial, or public exposure; a successful workflow alone is insufficient for RBAC certification. |
| Garage local storage | Configuration shows single-node S3-compatible endpoint, replication factor 1, and comment that RPC secret comes from environment. | Credentials, bind/firewall exposure, object-store access policies, encryption, backup/restore, and audit logs have not been assessed. |

## Non-deployment acceptance sequence

1. Confirm intended environment roles, datasets, public boundary and ADR-007 ownership; keep ADR **Proposed** until explicitly approved.
2. Export **sanitized** GitHub Environment rules, AWS role trust/policies, bucket public-access and encryption configuration, and any Snowflake grants. Never commit tokens, keys, account secrets, or sensitive source data.
3. Validate OIDC `sub`/audience expectations against actual token claims using a controlled, approved test; resolve any mismatch via separate reviewed PR.
4. Perform approved positive and negative access tests for each role and environment; include cross-prefix reads/writes and prod deletion denial, and record redacted results.
5. Verify public package contains only approved aggregates, and perform separate privacy, licensing, attribution, and publication approvals before any public deployment.
6. Record evidence, exceptions, and responsible approvers. Do not mark RBAC or cloud controls certified until independently verified.

**Explicit exclusions:** No deployment, Terraform apply, GitHub environment changes, permission grants, secrets rotation, public data publication, PR merge, or ADR status change is authorized by this document.
