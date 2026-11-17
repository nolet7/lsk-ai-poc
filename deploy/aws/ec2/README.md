# AWS EC2 deployment lab — four-service synthetic AI Enablement POC

> **Scope and safety:** This deploys the existing Gateway + Sales + Marketing + Finance Docker Compose topology, not the separate legacy `app/main.py` RAG service. All records are synthetic. The gateway has demo shared-key auth and the POC deliberately blocks real business approvals and writes. **Never expose ports 8090/8101/8102/8103 to the internet or use customer data.** This is a single-instance lab, not enterprise production.

## Prerequisites

- AWS account with permission for EC2, IAM instance profiles, Systems Manager, and (optionally) Bedrock.
- AWS CLI v2 and Session Manager plugin on your Windows workstation if you will use CLI port forwarding. AWS console Session Manager is an alternative for shell access.
- A fresh AWS account budget alert and a region selected (examples use `us-east-1`). EC2, storage, public IPv4, data transfer, CloudWatch, and Bedrock may cost money.
- GitHub access to this repository and to the three sibling repositories at the pinned revisions in `integrations/app-versions.env`. If any are private, set up narrowly scoped GitHub credentials on EC2 rather than publishing tokens.

## 1. Launch EC2 using the AWS console

1. Open EC2 > Instances > Launch instance; name `lsk-ai-poc-aws-lab`.
2. AMI: **Ubuntu Server 24.04 LTS x86_64**; instance: start with **t3.large** (2 vCPU / 8 GiB) to run four Python services and build their images. Increase if builds run out of memory; pricing varies by region.
3. Storage: at least **30 GiB gp3 EBS** for images/build cache/data. Encrypt EBS. Synthetic data only.
4. Network: choose a test VPC and subnet with outbound access to OS packages, Docker image registries, and GitHub. A public subnet with an assigned public IPv4 is easiest for this lab, but **does not authorize inbound access**.
5. Security group: **no inbound rules** (especially no 22, 8090, 8101, 8102, 8103). Allow outbound HTTPS and other egress necessary for image/package installation. Consider an isolated test VPC.
6. IAM role (instance profile): attach a role with the AWS-managed policy `AmazonSSMManagedInstanceCore` for Session Manager. Configure the instance's SSM Agent and connectivity as required. Do **not** attach AdministratorAccess.
7. Launch and wait for EC2 status checks and **Systems Manager > Fleet Manager** managed-node/online status. Use Session Manager > Start session; if offline, check role, SSM Agent, DNS and outbound path to SSM endpoints.
8. If you require Bedrock, add a **separate** tightly scoped IAM policy allowing `bedrock:InvokeModel` on the **exact approved model inference resource(s)** supported by your model/region, and inspect the Bedrock model-access and inference-profile requirements. No static AWS credentials go into Compose.

Alternative: when you don't have EC2 create permissions, ask the account administrator for an Ubuntu 24.04 instance with the above restrictions; the application bootstrap is unchanged.

## 2. Install and launch in the EC2 Session Manager shell

The account used by Ubuntu is `ubuntu`; Session Manager may open as `ssm-user`. If so, switch to `ubuntu` with `sudo -iu ubuntu` before running the commands below.

```bash
cd ~
git clone --branch feature/aws-ec2-poc-deploy \
  https://github.com/nolet7/lsk-ai-poc.git
cd lsk-ai-poc
bash deploy/aws/ec2/bootstrap-ubuntu.sh
```

Bootstrap installs Docker and the Compose v2 package on Ubuntu, clones the **pinned** sibling application revisions, validates their commits, creates `.env.business` with different random 256-bit synthetic demo keys, and starts four containers. It never overwrites an existing `.env.business`.

The bootstrap uses `sudo docker` so you don't need to log out/reconnect for Docker group changes. Docker group members effectively have root-level privileges; do not add untrusted users.

```bash
cd ~/lsk-ai-poc
sudo docker compose --env-file .env.business -f compose.business.yml ps
sudo docker compose --env-file .env.business -f compose.business.yml logs --tail=100 gateway
bash deploy/aws/ec2/smoke.sh
```

**Expected:** smoke ends with `PASS`. It verifies 4-service connectivity; the absence of a key gets HTTP 401; retrieval-only finance evidence works; the deprecated write path returns HTTP 410; and, when no model is configured, inference correctly returns HTTP 503 instead of inventing a response. The script is not evidence of a production security review.

If `docker-compose-v2` cannot be installed from Ubuntu apt sources, follow the official Docker Compose plugin install instructions for your architecture; verify `sudo docker compose version` before continuing.

## 3. Open the portals from Windows without opening inbound ports

Install the AWS CLI and the official **Session Manager plugin** on Windows. In PowerShell:

```powershell
aws sts get-caller-identity
aws ssm start-session --region us-east-1 --target i-REPLACE_WITH_INSTANCE_ID --document-name AWS-StartPortForwardingSession --parameters 'portNumber=8090,localPortNumber=8090'
```

Leave the first PowerShell window running. Browser: `http://localhost:8090` and `http://localhost:8090/docs`.

To open each business portal, start **three more PowerShell terminals**, each with the same command but different ports:

```powershell
aws ssm start-session --region us-east-1 --target i-REPLACE_WITH_INSTANCE_ID --document-name AWS-StartPortForwardingSession --parameters 'portNumber=8101,localPortNumber=8101'
aws ssm start-session --region us-east-1 --target i-REPLACE_WITH_INSTANCE_ID --document-name AWS-StartPortForwardingSession --parameters 'portNumber=8102,localPortNumber=8102'
aws ssm start-session --region us-east-1 --target i-REPLACE_WITH_INSTANCE_ID --document-name AWS-StartPortForwardingSession --parameters 'portNumber=8103,localPortNumber=8103'
```

These commands must run in different windows because each starts a persistent session. Portals: `http://localhost:8101/portal`, `http://localhost:8102/portal`, `http://localhost:8103/portal`.

**Important:** The hub contains localhost URLs that work only when corresponding port-forward sessions are active. SSM port-forward sessions do not provide full command content logging, so use separate audited application logging for environments beyond the lab.

## 4. Test the workflow

Run `bash deploy/aws/ec2/smoke.sh` on the instance first. For a browser/API exercise, inspect the gateway Swagger schema at `http://localhost:8090/docs`.

In EC2, without printing the secret:

```bash
cd ~/lsk-ai-poc
set -a; source .env.business; set +a
curl -sS http://127.0.0.1:8090/v1/apps \
 -H "X-API-Key: $GATEWAY_API_KEY" -H 'X-Actor: employee' | jq
curl -sS http://127.0.0.1:8090/v1/platform/ask \
 -H "X-API-Key: $GATEWAY_API_KEY" -H 'X-Actor: employee' \
 -H 'Content-Type: application/json' \
 -d '{"question":"Explain the invoice exception review process.","domain":"finance","record_id":"inv-1002","use_model":false}' | jq
```

Check `mode=retrieval-only`, cited source IDs, the finance record evidence, and `actions_taken=[]`. Use `GET /v1/apps/{domain}/records` and `GET /v1/apps/{domain}/records/{id}/insight` for each domain. For model-inference acceptance, see below.

### Optional Amazon Bedrock test

The gateway's optional model path uses EC2 instance-role credentials through Boto3, **not** an API key or AWS access key in `.env.business`.

1. Pick a model available and authorized for the EC2 region; verify that its identifier or inference profile is supported by the code in `integrations/bedrock_gateway.py`.
2. Grant **only** the Bedrock inference resource permissions needed. Monitor Bedrock token usage and charges.
3. Edit `.env.business` on EC2 to set `BEDROCK_MODEL_ID=<your-approved-model-id>` and the correct `AWS_REGION`; restart only the gateway:

```bash
cd ~/lsk-ai-poc
sudo docker compose --env-file .env.business -f compose.business.yml up -d --force-recreate gateway
```

4. Repeat `POST /v1/platform/ask` above with `"use_model":true`. Verify a clearly identified model mode, grounded response/evidence, no business mutation, and appropriate error handling. Confirm billing in AWS Cost Explorer.

**Gateway container AWS credentials caveat:** EC2 instance-profile access via IMDS may not work inside a Docker container under every networking/IMDS hop-limit configuration. Verify with a real `use_model=true` request. Use an appropriately restricted instance profile and AWS's documented IMDSv2 container configuration rather than copying credentials into the container.

## 5. Operational checks and troubleshooting

| Symptom | Check |
|---|---|
| SSM instance offline | EC2 instance role, SSM Agent, outbound HTTPS, DNS and SSM VPC endpoints/NAT |
| `docker compose` missing | Install a supported Compose v2 plugin; check Docker service and Compose version |
| Build process killed / no space | `free -h`, `df -h`, `sudo docker system df`; increase EBS / memory if required |
| `/v1/apps` lists unavailable | `sudo docker compose ... ps` and service logs; verify pinned sibling checkouts |
| HTTP 401 | Missing or incorrect demo key; check `X-Actor` and `X-API-Key` |
| HTTP 503 for model | Expected without model ID; if configured, inspect Bedrock region, permissions, model access and IMDS |
| Portal not opening on Windows | Keep separate SSM port-forward session alive per port; check no local port conflicts |
| HTTP 410 for legacy proposal | Expected safety control; this is a blocked write, not a failed deployment |

Logs:

```bash
sudo docker compose --env-file .env.business -f compose.business.yml logs --tail=200 gateway sales marketing finance
sudo docker stats --no-stream
```

## 6. Cost and cleanup

Before testing, set an AWS Budget alert; use a small, dedicated instance; avoid Bedrock calls until you explicitly enable them. Stop the lab when not needed (EBS still incurs charges). Terminate the instance when finished, and remove unneeded EBS volumes, snapshots, Elastic IPs and other separately created resources. Do not delete resources outside this lab.

```bash
cd ~/lsk-ai-poc
sudo docker compose --env-file .env.business -f compose.business.yml down
# DANGER: Only when you intentionally want to erase synthetic persisted demo data:
# sudo docker compose --env-file .env.business -f compose.business.yml down -v
```

## 7. Enterprise promotion boundary

**Not production-ready:** This EC2 Compose lab does not add OIDC workforce identity, real tenant isolation, HTTPS internet ingress, WAF, encrypted managed state, multi-AZ failover, business approval authority, or reliable centralized telemetry. Do not describe it as a production rollout. For an enterprise pilot, independently design ECS or EKS deployment, ALB/API gateway, private task networking, OIDC, Secrets Manager, separate IAM roles, durable managed databases, metrics/logging, backups, CI/CD, load testing, disaster recovery, and the explicit acceptance gates in `docs/RELEASE_GATES.md`.

## Reference

- [AWS Session Manager port forwarding](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html)
- [AWS Session Manager prerequisites](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-prerequisites.html)
- [Docker Compose plugin install](https://docs.docker.com/compose/install/linux/)
- [AWS Bedrock IAM](https://docs.aws.amazon.com/bedrock/latest/userguide/security_iam_service-with-iam.html)
