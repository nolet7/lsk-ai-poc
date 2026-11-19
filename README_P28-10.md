# P28-10 — AWS Bedrock runtime security (offline validation)

This package adds **two Python files**. It does not modify existing P28-09
execution paths, enable live inference, create AWS clients by default, or deploy
infrastructure. No AWS calls are made by the tests.

## Interface

- `phase28.aws_security.build_invoke_policy(region, model_id, vpce_id)` builds an
  example role policy for **one** regional foundation model and **one** Bedrock
  runtime VPC interface endpoint.
- `create_runtime_client(...)` requires double configuration opt-in, a separately
  constructed trusted approval, matching model/region, and injected SDK
  factories. It constructs a client but never invokes inference.
- SDK retries use `total_max_attempts=1`; this protects against automatic
  duplicate inference requests after ambiguous network failures.

## AWS account deployment checklist (manual, not automated)

1. Verify the exact model ID and supported AWS region. For inference profiles,
   stop and develop an appropriate policy for the profile and underlying models.
2. Create a **bedrock-runtime** PrivateLink interface endpoint in appropriate
   subnets with private DNS and security-group rules for TCP 443. Verify DNS
   resolution and connectivity in the actual workload VPC.
3. Scope the workload IAM role to `bedrock:InvokeModel` for the approved
   foundation model and `aws:SourceVpce` for the exact endpoint; review ALL
   other attached role policies, SCPs, permission boundaries and endpoint policy.
4. Use short-lived workload role credentials (for example IRSA / EKS Pod Identity);
   never store AWS access keys in Git, environment files, or the application.
5. Prohibit unbudgeted SDK calls at the application architecture boundary;
   this runtime client factory alone cannot guarantee enforcement.
6. Verify model-specific token preflight, account-level concurrency and costs;
   the SQLite ledger remains **single-host only**.
7. Verify identity, signed authorization, separate append-only audit storage,
   alerting, spend alarms, incident response, deployment rollback, and failure drills.
8. Keep `AI_LIVE_INFERENCE=false` and `AI_LIVE_INFERENCE_ACK=false` until a
   production deployment review approves all dependencies.

## Optional code example (offline only)

```python
from phase28.aws_security import build_invoke_policy
policy = build_invoke_policy(
    region="us-east-1",
    model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
    vpce_id="vpce-0123456789abcdef0", # REPLACE with your real endpoint ID
)
```

## Run

```bash
python -m py_compile phase28/aws_security.py phase28/tests/test_aws_security.py
python -m unittest discover -s phase28/tests -p 'test_aws_security.py' -v
python -m unittest discover -s phase28/tests -v
```

The policy is an **example**, not verification that a specific model or its
availability, endpoint, IAM conditions, and inference profile requirements are
valid for your AWS account. See AWS official documentation:

- https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/vpc-interface-endpoints.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-prereq.html
- https://docs.aws.amazon.com/botocore/latest/reference/config.html
