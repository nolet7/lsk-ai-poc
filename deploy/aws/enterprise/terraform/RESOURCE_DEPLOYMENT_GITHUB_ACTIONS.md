# Enterprise resource deployment: GitHub Actions control plane

**Status:** Workflow code committed; **NOT yet operational**. AWS OIDC roles, cross-account trust, repository variables and reviewer protection must be configured and validated before any cloud execution. The existing development VPC is deployed locally and tracked in management-account S3 remote state. **Never re-create or import the VPC during workflow migration.** GitHub Actions will read that SAME state key.

## User interaction / CTO mandate

The engineer uses the GitHub repository Actions tab (or `gh workflow run`), chooses **resource**, **environment**, **action**, and for deployment types **DEPLOY network**. Default is PLAN ONLY. A completed plan is displayed and uploaded for review. Deployment executes the exact saved plan only after the repository's protected GitHub environment gate approves. The workflow does not deploy anything automatically on push, PR, or schedule.

Resource menu: `network`, `eks`, `s3`, `database`, `sagemaker`, `bedrock`. **Only `network` is implemented.** All other selections intentionally fail with a clear unsupported-resource message. Do not interpret the menu as claiming services exist. Environment menu currently supports only `development`.

## Why two AWS roles?

GitHub Actions uses temporary OIDC credentials instead of stored IAM access keys.

1. GitHub OIDC exchanges a scoped identity token for a **management-account** state-access IAM role. Trust its claims for `nolet7/lsk-ai-poc` and either the reviewed branch (plan) or the protected environment (apply).
2. Terraform S3 backend reads/writes the EXISTING bucket `lsk-ai-platform-proj1asr`, key `development/network/terraform.tfstate`, in `us-east-1`; it also needs access to the S3 lockfile and versioned state objects. Avoid wildcard bucket access.
3. The AWS Terraform provider then uses `sts:AssumeRole` to enter a **separate least-privilege deployment role in the existing member account**, pointing at `us-east-2`. The member-role trust grants assume-role only to the approved management state role. Terraform account precondition verifies the approved account.
4. The member deployment role must allow only the Terraform resource types needed for this module (EC2 VPC, subnet, route-table, association, tags and reads), with organization guardrails still enforced. Do not reuse `PowerUserAccess` or management bootstrap for CI.

This is an architecture contract; no role, OIDC provider or trust policy has been provisioned by this commit.

## Required repository variables

In repository Settings > Secrets and variables > Actions > Variables, configure:

| Name | Meaning |
| --- | --- |
| `AWS_TERRAFORM_STATE_ROLE_ARN` | Approved management-account state access role ARN |
| `AWS_MANAGEMENT_ACCOUNT_ID` | 12-digit management account ID, for OIDC account assertion |
| `AWS_DEVELOPMENT_TERRAFORM_ROLE_ARN` | Approved development-account Terraform deploy role ARN |
| `AWS_DEV_ACCOUNT_ID` | 12-digit approved member account ID |

For the GitHub environment **`lsk-development-apply`**, configure required reviewers, restrict allowed deployment branches, optionally prevent self-review, and **only after confirming these rules** set the *environment variable* `LSK_APPROVAL_GATE_CONFIGURED=true`. If unset, apply fails closed. Do not set this variable in repository-wide settings without reviewing the environment; the workflow is intended to require the protected environment.

**GitHub licensing:** Required reviewers may depend on repository visibility and account plan. Verify GitHub actually enforces the reviewer gate; a job `environment:` name alone does not constitute protection. Do not set the gate flag if reviews are unavailable. Use organizational branch protection and authorized human review.

## OIDC trust least-privilege checklist

- GitHub Actions OIDC provider `https://token.actions.githubusercontent.com` with audience `sts.amazonaws.com` is registered in the management account.
- Role trust enforces `token.actions.githubusercontent.com:aud = sts.amazonaws.com` and restrictive `sub` matches to this repo, reviewed source branch for plan and protected environment for apply.
- The management state role has narrow S3 state and lockfile read/write permissions, and only `sts:AssumeRole` for the dedicated development deployment role.
- The development Terraform role explicitly trusts this one management role and uses a narrow EC2 policy. The roles are not interchangeable with local Identity Center permission sets.
- Verify role sessions with `aws sts get-caller-identity` and test a plan before enabling apply.

## Existing VPC migration (no recreation)

Development VPC created by Terraform: `lsk-ai-dev-vpc`, CIDR `10.42.0.0/16`; the last reported run was **16 added, 0 changed, 0 destroyed** and then **no drift**. Backend bucket/key remain unchanged. GitHub Actions must produce `No changes` for `network` before any attempted apply. If its plan proposes creating or replacing the VPC, STOP and check state key, backend access, account ID, and region. Never run `terraform import` or `terraform state mv` without a state-recovery procedure.

## Workflow safety / release process

- `workflow_dispatch` is manual; `action=plan` defaults to read-only Terraform planning. `action=deploy` requires exact text `DEPLOY network`, job environment protection, and gate variable.
- A deployment's apply stage uses the **exact** plan artifact from the plan job in the same workflow run and the same checked-out Git commit. The artifact has a 1-day retention period, can contain sensitive metadata, and should be limited to trusted repository viewers.
- Concurrency serializes same resource/environment runs. State has native S3 lockfile. Plans are never trusted between distinct workflow runs.
- GitHub currently uses `terraform fmt -check -recursive`. Commit the local formatting changes from the working Terraform directory before expecting a successful CI run.
- The module currently has no committed `.terraform.lock.hcl`; `terraform init` resolves the provider version allowed in `versions.tf`. **Commit the provider lockfile after review** and then switch CI to `terraform init -lockfile=readonly` for reproducibility. Use vetted action SHA pins in a hardened production environment.
- **Existing local runs:** Backend profile was removed from `backend.tf` to support OIDC. For local CLI only, use `AWS_PROFILE=lsk-management terraform init -reconfigure` in the module for backend initialization, while the provider remains configured with `lsk-development`. Do not use `-migrate-state`, change the state key, or overwrite remote state.
- Once CI fully validated, future resource changes should go through PR, review, GitHub Actions plan, approval, and apply rather than workstation `terraform apply`.

## First successful no-change test

1. Verify all roles and trust policies through AWS CLI (read only).
2. Check the workflow is present on the repository default branch; GitHub generally requires that for the manual Run workflow UI.
3. Run `Enterprise resource deployment (manual + approval)` with `resource=network`, `environment_name=development`, `action=plan`.
4. Expected: S3 state opens, Terraform validates, plan says **No changes**, artifact uploaded. Investigate failures, do not deploy to fix a broken plan.
5. Once environment gate is verified and a genuine change has been reviewed, select `action=deploy`, type `DEPLOY network`, have authorized reviewers approve and examine the planned changes.

## Future resources

Add a separate Terraform root module and state key per resource (`development/eks`, `development/s3`, `development/database`, `development/sagemaker`, `development/bedrock`) with separate lifecycle, cost/quotas, safe defaults, plan validation and task-specific role permissions. Extend the dispatch allowlist ONLY after each module has been validated. Bedrock model invocation and SageMaker model hosting are separately metered; network and EKS are not interchangeable modules.
