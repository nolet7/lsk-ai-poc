# LSK FDE AI delivery — POC / PILOT / PRODUCTION-STYLE

One shared application source directory `phase28/`, separate deployment stacks and evidence gates.

| Stage | Runtime | Implemented in Git | Cloud status |
|---|---|---|---|
| POC | Local FastAPI tests and synthetic evidence | Yes | No cloud needed |
| Pilot | Private EC2 + SSM/Bedrock endpoints + encrypted EBS | Terraform, IAM/bootstrap scripts, offline install | **Not deployed** |
| Production-style | ECR + GitHub OIDC + private ECS Fargate / HTTPS ALB + PostgreSQL Multi-AZ + CloudWatch alarms | Terraform, containerized PostgreSQL API, schema migration | **Not deployed or production-certified** |

## Important controls
- `enabled=false` is the default in Terraform. AWS resources cost money when enabled.
- Complete approved remote S3 state backend, IAM, subnets, DNS, AMI/image digest and secrets first.
- Pilot EC2 uses SQLite, cannot be horizontally scaled.
- Production-style API uses PostgreSQL; migration is a deliberate operator step before deploying live ECS tasks.
- Production model calls remain OFF by default. No AWS changes happen merely by committing code.
- See `docs/fde/RELEASE_GATES.md` and environment README/OPERATIONS for validation gaps.

## Quick static validation
```bash
python scripts/check_fde_environments.py
python -m unittest discover -s phase28/tests -v
```
GitHub `fde-aws-infrastructure-validation` runs Terraform `init -backend=false` + `validate` against all stacks without AWS credentials or spending.
