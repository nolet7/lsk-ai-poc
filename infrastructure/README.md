# EC2 deployment — LSK LSK-branded commercial AI (no Docker)

This repository contains **reproducible infrastructure and service deployment artifacts**.
The system remains a synthetic-data portfolio demonstration. Real customer data,
real LSK systems, and any claim of LSK endorsement are out of scope.

## Deployment prerequisites

- An authorized AWS administrator with EC2, CloudFormation and IAM role
  permissions; an existing SSH key and an inbound security group limited to
  SSH from your own /32 IP. The business ports must never be open to the internet.
- An approved Bedrock model or inference profile in the target region, a model ID,
  and explicitly scoped model/inference-profile ARNs for the EC2 instance role.
- SSH access and budget confirmation before creating a new billed instance.
- Pilot and production additionally require a real OIDC issuer and application
  audience, a same-host HTTPS JWKS URL, users provisioned with a signed
  `roles=["lsk.ai.read"]` and `domains=["sales"]` (or marketing/finance)
  claim. Token signatures, expiration, issuer and audience are validated both at
  the gateway and at the individual service. This does not yet implement
  record-level entitlement to real customer data.
- `METRICS_API_KEY` is distinct from both API keys and is required for
  authenticated Prometheus scrape in pilot/production.

## Check existing resources FIRST

```bash
aws sts get-caller-identity
aws ec2 describe-instances --region us-east-1 \
  --filters 'Name=instance-state-name,Values=pending,running,stopping,stopped' \
  --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags]' --output table
```

**Do not create a duplicate instance if an earlier deployment exists.**

## Two infrastructure choices

**A. Existing EC2 host:** Keep your already provisioned Ubuntu VM and key pair.
No additional AWS instance is required; clone the branch and install systemd
services below.

**B. CloudFormation-managed host:** Review
`infrastructure/cloudformation/ai-ec2.yaml` and launch it via the AWS Console
or authorized CLI:

```bash
aws cloudformation deploy \
  --region us-east-1 \
  --stack-name lsk-ai-CHOOSE_STAGE \
  --template-file infrastructure/cloudformation/ai-ec2.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    Stage=CHOOSE_STAGE \
    UbuntuAmiId=ami-08b275ac6cc5dbefb \
    SubnetId=subnet-0e711369ba0ab1b51 \
    SecurityGroupId=sg-03898c99fff2ae352 \
    KeyName=lsk-ai-poc \
    InstanceType=t3.medium \
    BedrockResourceArns=REPLACE_WITH_AUTHORIZED_BEDROCK_MODEL_OR_PROFILE_ARN
```

Replace `CHOOSE_STAGE` with the desired branch stage and the Bedrock ARN
placeholder with an actual approved resource ARN (or comma-separated ARNs,
including underlying foundation-model permissions where required). CloudFormation
creates an IAM instance profile, EC2 instance, encrypted 20 GiB volume and CPU
alarm. It does **not** install app code, create OIDC users, configure active SNS
notifications or validate model access. The AMI is region-specific and must be
re-verified at deployment time.

This command may incur EC2 compute, EBS, public IPv4, CloudWatch, inference and
related charges; AWS credits may not cover all services. Avoid launching separate
pilot and production hosts until authorization and costs are approved.

## Configure the Ubuntu services

SSH in to the authorized EC2 instance, and clone the chosen GitHub branch:

```bash
git clone -b CHOOSE_STAGE https://github.com/nolet7/lsk-ai-poc.git
cd lsk-ai-poc
bash scripts/clone_business_apps.sh
bash scripts/verify_business_versions.sh
cp .env.business.example .env.business
chmod 600 .env.business
nano .env.business
```

Set unique long `GATEWAY_API_KEY`, `DEMO_API_KEY`,
`BEDROCK_MODEL_ID`, and (for pilot/production) `OIDC_ISSUER`,
`OIDC_AUDIENCE`, `OIDC_JWKS_URL`, `METRICS_API_KEY`. Never put AWS
access keys into the environment file: attach a Bedrock-scoped IAM instance
profile to EC2. If clones already exist at different commits, check they are
clean then run `bash scripts/sync_business_versions.sh` with explicit
per-repository confirmation.

Run from Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y rsync
bash infrastructure/install-systemd.sh
sudo systemctl --no-pager status lsk-gateway lsk-sales lsk-marketing lsk-finance
sudo journalctl -u lsk-gateway -n 50 --no-pager
curl http://127.0.0.1:8090/health
```

The installer requires typing `INSTALL`, copies **only application code**
under `/opt/lsk-ai-poc`, copies local secrets into root-controlled
`/etc/lsk-ai`, puts SQLite state under `/var/lib/lsk-ai`, and starts
four loopback-only services as unprivileged user `lskai`.

## Access privately

From Git Bash on Windows:

```bash
ssh -i ~/.ssh/lsk-ai-poc \
  -L 8090:127.0.0.1:8090 \
  ubuntu@YOUR_EC2_PUBLIC_IP
```

Open `http://127.0.0.1:8090/agent`. POC accepts its private demo gateway
key and synthetic actor. Pilot/production require an OIDC bearer access token;
demo headers never count as signed identity.

## Acceptance

```bash
python -m unittest discover -s tests -p test_oidc_crypto.py -v
python -m unittest discover -s tests -p test_oidc_stage.py -v
python -m unittest discover -s tests -p test_lsk_agent.py -v
python scripts/smoke_integration.py
```

`scripts/smoke_integration.py` tests real local business APIs with temporary
databases and **does not call Bedrock**. The live-model acceptance procedure:

```bash
# Never enable demo writes during model evaluation
export LSK_ENABLE_DEMO_WRITES=false
export GATEWAY_API_KEY='POC_GATEWAY_KEY'    # POC only
# For pilot/production use: export OIDC_ACCESS_TOKEN='REAL_SIGNED_USER_ACCESS_TOKEN'
python scripts/evaluate_lsk.py
```

The evaluator uses synthetic examples and saves evidence under
`evaluation/results/`. It does not automatically certify model quality,
release readiness or actual LSK outcomes. Use the stage's acceptance
document and `docs/RELEASE_AUDIT.md`.

## Cleanup and rollback

Stop the individual services with `sudo systemctl stop lsk-gateway lsk-sales
lsk-marketing lsk-finance`; persistent SQLite data is in `/var/lib/lsk-ai`.
To terminate the stack use a reviewed `aws cloudformation delete-stack`
command, noting that termination may delete the root volume. Back up important
data first. Stopping compute does not stop all EBS/address charges.

Production still requires a real security/business approval, user-specific
record-level entitlements, hardened audit retention, cost/latency SLOs, incident
ownership, tested backup/recovery and release signoff. **Do not interpret
code completion as those approvals.**
