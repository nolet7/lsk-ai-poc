# P28-12 — AWS infrastructure and offline deployment preflight

**Scope:** isolated Terraform for an *existing* VPC, subnets, application security group, and application IAM role. No application deployment, OIDC verifier, API gateway, or production multi-replica quotas are included. The default `enabled=false` creates **zero resources**. Opt-in VPC interface endpoints incur AWS charges.

## Offline checks

From the repository root:

```bash
python -m unittest discover -s phase28/tests -p 'test_deployment_smoke.py' -v
python -m unittest discover -s phase28/tests -v
python -c "from phase28.config import AISettings; from phase28.deployment_smoke import offline_preflight; print(offline_preflight(settings=AISettings(), terraform_dir='deploy/aws/phase28_poc'))"
```

## Terraform checks (require Terraform CLI and provider installation)

```bash
cd deploy/aws/phase28_poc
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
terraform plan -var='enabled=false' -out=p28-disabled.tfplan
cd ../../..
```

The `terraform init` command may download the provider; the plan may need AWS credentials to refresh provider context even though resources are disabled. No `apply` should be performed until approved. The provider lock file should be reviewed and committed once initialized.

## Before ANY billable `apply`

1. Confirm the correct AWS account/region (`aws sts get-caller-identity`).
2. Confirm target VPC and private subnets exist and belong to that account/region; verify endpoint availability.
3. Confirm the application IAM role ARN/name refer to the same existing role and its trust policy is reviewed.
4. Confirm application security group is in the target VPC; ensure DNS and private connectivity from workload subnets.
5. Check provider and model support, model access, endpoint service availability and endpoint costs.
6. Review `terraform plan` and obtain approval. Inspect identity policy plus endpoint policy and other attached IAM permissions/SCPs.
7. Do not deploy more than one replica with the SQLite quota ledger. Implement a centralized atomic quota store before multi-node production.
8. Keep `AI_LIVE_INFERENCE=false` and `AI_LIVE_INFERENCE_ACK=false`; this scaffold does not enable live inference.

## Limitations

- No verified OIDC/JWT authentication or HTTP gateway is provided in this phase.
- IAM and endpoint policy are additive controls; other IAM grants can permit different access. Ensure account-level guardrails.
- The endpoint resource is opt-in, uses private DNS, has a limited model-scoped endpoint policy, and only accepts TLS from a specified application security group.
- No cloud smoke tests were run. Do not claim deployment success from these tests.
