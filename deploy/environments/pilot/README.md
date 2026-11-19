# Pilot — controlled live AWS integration

**Runtime already implemented:** Dockerless, private EC2 + systemd + FastAPI, using `deploy/aws/phase28_ec2/`. This is a pilot architecture, **not a production deployment**.

## AWS target
- Development account `179793764737`, region `us-east-2`.
- Existing VPC `vpc-009da120ff1cddbf5`, private subnet `subnet-054275fd09fd75d15`.
- Single EC2 instance, no public IP or inbound application ports.
- SSM port forwarding for restricted access.
- Bedrock private service access only after endpoint, IAM, model and budget approval.

## Verified vs pending
- App code and Linux CI: complete.
- IAM Identity Center permission set: inline policy submitted, provisioning completion not yet verified.
- Dedicated `LSK-Phase28-EC2-Role` and instance profile: not created.
- VPC interface endpoints, approved package access: missing from observed network.
- EC2 launch and live Bedrock invocation: **not verified**.
- Existing `deploy/aws/phase28_ec2/main.tf` is opt-in **diagnostic EC2** and does not install the AI app or provision endpoints.

## Operator sequence
1. Confirm SSO provisioning `SUCCEEDED` and verify scoped IAM, then create approved EC2 instance role/profile.
2. Review VPC DNS, subnet routes, endpoint SG, endpoints for SSM/SSM Messages and Bedrock Runtime; approve monthly costs.
3. Provide signed, pinned build artifacts or reviewed offline dependencies (no internet egress currently).
4. Review a Terraform plan and apply only with approval. Do not presume `terraform apply` installs the app.
5. Follow `README_DEPLOY_AI_AWS.md` and `README_AI_QUICKSTART.md`; provide real OIDC issuer, JWKS and RBAC, seed **synthetic** records, install systemd service.
6. Test health and authorization with model off. Then approve one real Bedrock request using both opt-in flags, capture sanitized audit/latency/cost evidence.
7. Practice rollback, endpoint failure, JWT expiry and access denial.

**Pilot exit:** evidence of real authenticated request and model result, cost review, failure handling and written go/no-go decision. This still does not establish production readiness.
