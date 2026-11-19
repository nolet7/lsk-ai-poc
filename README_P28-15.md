# P28-15 — Dockerless EC2 diagnostic deployment

## Scope / CTO guardrails
No Docker, no Kubernetes, no billable inference. Existing Phase28 application remains **diagnostic-only**; /health/live=200, /health/ready=503, business requests blocked. Gateway auth + real storage + durable audit + JWKS rotation are not wired; do not expose publicly. P28-15 provides **manual** EC2 deployment using Python venv, systemd and loopback NGINX. Nothing auto-deploys.

## File locations
- `deploy/aws/phase28_ec2`: opt-in Terraform instance, service, NGINX, operator install and smoke scripts.
- `.github/workflows/phase28-p14-ci.yml`: replaces previous Docker build with Python-only CI and vulnerability scanning.
- `phase28/tests/test_ec2_deployment.py`: offline static deployment guard checks.
- `phase28/tests/test_container_entry.py`: existing P28-14 tests updated to check the **new Dockerless CI** while preserving previous container artefacts for historical compatibility.

## Local acceptance (from root)
```bash
python -m unittest discover -s phase28/tests -p 'test_ec2_deployment.py' -v
python -m unittest discover -s phase28/tests -v
bash -n deploy/aws/phase28_ec2/install-from-checkout.sh deploy/aws/phase28_ec2/smoke.sh
cd deploy/aws/phase28_ec2
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
terraform plan -var='enabled=false' # AWS credentials may be required even with resources off
cd ../../..
```

## Before any apply (TASK — manual operator approval)
1. Review all IAM permissions, network access, AWS costs, storage charges and AWS Region/account. EC2 with `enabled=true` incurs EC2/EBS/monitoring charges. Default `enabled=false` creates zero resources.
2. Select an approved Ubuntu AMI (explicit `ami_id`), existing VPC and **private subnet**, and an existing approved SSM-enabled instance profile. This template does not create an IAM role, NAT, endpoints, key pair, or public IP.
3. Verify subnet routing permits fetching approved apt packages, Python packages and GitHub source by a controlled mechanism. Private EC2 has no route by default; prefer internal artifact mirror and SSM. Avoid public SSH.
4. Reduce `egress_cidr` from the broad `0.0.0.0/0` default (still TCP 443 only) before organizational use; approval is required.
5. Set `enabled=true` only after plan review; use a protected Terraform backend and operator-managed state. No `terraform apply` or real AWS validation has been performed here.
6. **Do not attach Bedrock permission to this diagnostic EC2 profile.** Phase28_poc Bedrock permission template is separate and must stay disabled.

## EC2 operator steps AFTER infrastructure deployment
1. Use approved SSM Session Manager to connect. Ensure `python3`, `python3-venv`, `nginx`, and a supported Python runtime are present (review package repo and OS). Do not enable NGINX internet-facing listeners.
2. Transfer a **reviewed and pinned repo checkout** via approved internal distribution. In a sandbox lab only, an authorized git clone may be used; pin to the reviewed Git SHA. Do not use branch HEAD for unreviewed production rollouts.
3. `sudo bash deploy/aws/phase28_ec2/install-from-checkout.sh "$PWD"` from repo root; it installs the diagnostic app under `/opt/lsk-phase28`, configures loopback NGINX and systemd. Install script is not rollback-safe; stage/test it before production.
4. `sudo systemctl status lsk-phase28 --no-pager`, `sudo journalctl -u lsk-phase28 -n 100 --no-pager`, `bash deploy/aws/phase28_ec2/smoke.sh`.
5. Rollback requires restoring an approved checkout and rerunning the reviewed installer. For a true atomic rollback, implement versioned releases and a symlink switch in P28-16.

## Important limitations
- No live AWS deployment, SSH, external HTTPS ingress, real token issuer, TLS certs, remote audit, true JWKS refresh or multi-replica budget store.
- Terraform security group has no inbound rules; the diagnostic NGINX listener is loopback. Existing control planes, SSM, and base OS still need their own security review.
- `nginx` package may install a **default public listener** unless that default site is removed. Before enabling a security-group ingress rule, disable default sites and verify `sudo ss -lntp`; this template deliberately has no ingress.
- A container image is not needed locally or in CI; legacy P28-14 container artifacts remain inert.
