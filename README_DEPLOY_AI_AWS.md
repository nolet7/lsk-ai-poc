# Deploy the actual AI — private Dockerless EC2 pilot

This branch adds a **real authenticated Bedrock Converse endpoint** rather than another
diagnostic-only container. It is a **single-EC2 pilot**, not production-ready or public.
Live model inference is explicitly disabled by default. The deployment performs **no AWS
writes automatically**. Existing Phase 28 components, Terraform and earlier releases remain intact.

## What is functional

- POST /v1/business/questions with verified RS256 JWT, pinned HTTPS issuer and audience.
- Tenant/domain role grants and tenant-scoped SQLite evidence; optional record filter.
- GET /health/live and GET /health/ready (DB checked); no docs/OpenAPI exposed.
- JSON answer + citation validation and sanitized SQLite audit.
- Explicitly gated real AWS Bedrock Converse calls with per-instance/day request cap.
- Bind to loopback port 8081 only. Access through **approved SSM port forwarding**.

## Operating guardrails / limitations

This is **not enterprise RAG** (SQLite is a pilot evidence store, not a vector index).
The server uses operator-provided JWKS; **refresh/rotation is not automatic**.
The source code is copied into an install directory and pip resolves dependencies
at install time: use a reviewed pinned Git SHA, audited lock/wheelhouse and
release promotion process before real production. The SQLite request cap is
single-instance and does not enforce a USD budget or input-token accounting;
the provider can still charge for any Bedrock request. Keep max 5/day; no
public exposure, no sensitive real data. Use a model ID that is actually enabled
in your account/region and a narrowly scoped instance role.
No AWS IAM credentials are placed in code or environment files. Bedrock
must only be enabled after approved cost and access checks.

## Deploy checklist on an ALREADY approved private Ubuntu EC2 (SSM managed)

1. Validate GitHub Actions Linux tests on the selected revision and review the
   Dockerless Terraform under deploy/aws/phase28_ec2. Confirm private subnet,
   route/SSM access, IMDSv2, encryption, no ingress, costs and instance role.
   **Do not blindly run Terraform apply.**
2. Use approved AWS Systems Manager Session Manager to enter the instance. Install
   python3, python3-venv and required network/package access by organizational process.
3. Transfer reviewed checkout pinned at a **full Git SHA**, then run
   `sudo bash deploy/aws/phase28_ec2/install-ai.sh "$PWD"`.
4. Place trusted OIDC JWKS in `/etc/lsk-phase28-ai/jwks.json` and
   role policy from the reviewed example in `/etc/lsk-phase28-ai/rbac.json`.
   Owner root, group lskphase28, mode 0640; directory mode 0750.
   Never commit generated JWTs, keys, or JWKS containing private key material.
5. Copy `ai.env.example` to `/etc/lsk-phase28-ai/pilot.env`.
   Fill approved issuer, audience, model and region, set root:lskphase28 0640.
   Keep BOTH inference flags false for first startup.
6. Create DB **as service identity**:
   `sudo -u lskphase28 /opt/lsk-phase28-ai/venv/bin/python -c "from phase28.live_app import initialize_database; initialize_database('/var/lib/lsk-phase28-ai/data.db')"`
   Add `PYTHONPATH=/opt/lsk-phase28-ai/app` if executing outside the app working directory.
   Insert reviewed non-sensitive test evidence into `sources` using parameterized SQLite
   statements. Fields are source_id, tenant_id, domain, record_id, content.
7. `sudo systemctl daemon-reload && sudo systemctl enable --now lsk-phase28-ai`
   Check `sudo systemctl status lsk-phase28-ai --no-pager`,
   `curl -fsS http://127.0.0.1:8081/health/ready`,
   `sudo journalctl -u lsk-phase28-ai -n 100 --no-pager`.
8. From your laptop use SSM session port forwarding (SSM permissions and AWS CLI
   Session Manager plugin required), example:
   `aws ssm start-session --target i-YOUR_INSTANCE --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["8081"],"localPortNumber":["18081"]}'`
   Never open security-group inbound 8081. Use a real signed JWT from the trusted
   issuer and POST to http://127.0.0.1:18081/v1/business/questions.
9. With retrieval-only validated, approve Bedrock region/model/IAM/cost. Explicitly
   set AI_LIVE_INFERENCE=true **and** AI_LIVE_INFERENCE_ACK=true and restart service;
   requests additionally need `"use_model": true`. No changes to the diagnostic
   service are required.

### Demo request (do not send fabricated bearer tokens)

```bash
curl -sS http://127.0.0.1:18081/v1/business/questions \
  -H "Authorization: Bearer $OIDC_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"domain":"orders","question":"What is the delivery policy?","use_model":false}'
```

## Tests

```bash
python -m unittest discover -s phase28/tests -v
python -m py_compile phase28/live_app.py
bash -n deploy/aws/phase28_ec2/install-ai.sh
```

## Still required before production

OIDC automatic trusted JWKS refresh; key rotation, customer-backed data
connectors and ACL-aware indexing; tamper-resistant external audit; model-specific
token and financial budgets; model evaluations and red-team testing; safe artifact
promotion, dependency hashing and rollback, reliable SSM runbook, encryption
and backups for SQLite, and dedicated private network endpoint policies.
