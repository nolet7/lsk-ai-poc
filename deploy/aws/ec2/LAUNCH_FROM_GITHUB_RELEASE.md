# Temporary AWS application launch: four-service LSK POC

**Status:** Opt-in only. GitHub Actions validates/packages the release, but EC2 launch is currently an explicitly confirmed CLI script checked into this repository because the GitHub OIDC deployment role is not provisioned. This is NOT a GitHub-Actions-operated production deployment. The launch script must be manually reviewed before execution. It targets **only the existing development account** in `us-east-2`; do not use in another account.

## Architecture and business flow

Private GitHub Sales/Marketing/Finance repositories → GitHub Actions pinned checkout → contract and safety tests → immutable 4-service release artifact → temporary EC2 with Docker Compose → gateway (8090) → three services (8101–8103) → ACL-grounded read-only Finance question. No customer data, no production identity, no payment action and no model invocation by default.

## Before any paid launch

1. [Package commercial AI POC for AWS](https://github.com/nolet7/lsk-ai-poc/actions/workflows/package-commercial-ai.yml) using `--ref feature/aws-enterprise-terraform -f release_name=dev-poc-02` **after the bootstrap-from-release.sh commit**. Download that run's artifact into a non-OneDrive release folder, verify the SHA256SUMS.
2. Confirm `aws sts get-caller-identity --profile lsk-development` reports the approved member account. Confirm `AWS_REGION=us-east-2`.
3. Understand costs: `t3.large` Linux On-Demand ~US$0.0832/hour in Ohio, plus a public IPv4 at US$0.005/hour, 30 GiB gp3 EBS storage and potential transfer/CPU-credit charges. It is NOT a $20/month always-on architecture. Limit lab runtime and terminate. $20 AWS Budgets notifications are not a hard spend limit.
4. The dedicated LSK VPC has no outbound internet; launch uses the **existing default VPC** and a subnet with outbound access, without altering the dedicated VPC. Existing network controls or SCP may still prevent launch. No inbound app ports. Inbound port 22 only from the invoking workstation's observed public IPv4 /32.
5. The Ubuntu AMI is captured from Canonical's `describe-images` result; inspect validity if substantial time has passed. The instance has no IAM instance profile; optional Bedrock is disabled. Do not insert AWS access keys, GitHub private tokens or secrets into the instance.

## Launch (user explicitly approves)

From the branch checkout in Git Bash:

```bash
export AWS_PROFILE=lsk-development AWS_REGION=us-east-2 AWS_DEFAULT_REGION=us-east-2
bash deploy/aws/ec2/launch-lab.sh
```

Review instance type, AMI, subnet, SSH CIDR and EBS shown on screen, then type `DEPLOY EC2` only when you approve hourly charges. It creates an SSH key in `/c/terraform-work/lsk-ai-poc/ec2-lab` (do not commit or sync with OneDrive); an EC2 key pair, restricted security group and one EC2 instance. The state file holds instance ID, public IP and SG ID, **not AWS credentials**.

## Transfer trusted release securely (NO GitHub tokens on host)

Change `RUN_ID` to the successful packaging run after `dev-poc-02` is built:

```bash
mkdir -p /c/terraform-work/lsk-ai-poc/releases/dev-poc-02
gh run download RUN_ID --repo nolet7/lsk-ai-poc --name lsk-commercial-ai-dev-poc-02 --dir /c/terraform-work/lsk-ai-poc/releases/dev-poc-02
cd /c/terraform-work/lsk-ai-poc/releases/dev-poc-02
sha256sum -c SHA256SUMS
source /c/terraform-work/lsk-ai-poc/ec2-lab/instance.env
KEY=/c/terraform-work/lsk-ai-poc/ec2-lab/lsk-ai-dev-poc-01
ssh -i "$KEY" -o StrictHostKeyChecking=accept-new ubuntu@"$PUBLIC_IP" 'mkdir -p ~/lsk-release'
scp -i "$KEY" lsk-commercial-ai-dev-poc-02.tar.gz ubuntu@"$PUBLIC_IP":~/lsk-release/
ssh -i "$KEY" ubuntu@"$PUBLIC_IP" \
  'cd ~/lsk-release && tar -xzf lsk-commercial-ai-dev-poc-02.tar.gz && bash deploy/aws/ec2/bootstrap-from-release.sh'
```

You should inspect and record SSH host fingerprints before first connecting in a higher-trust environment; `accept-new` alone is an initial trust-on-first-use shortcut for this personal lab.

## Use app privately over SSH forwarding

Open another terminal and leave it running:

```bash
source /c/terraform-work/lsk-ai-poc/ec2-lab/instance.env
ssh -i /c/terraform-work/lsk-ai-poc/ec2-lab/lsk-ai-dev-poc-01 -N \
  -L 8090:127.0.0.1:8090 -L 8101:127.0.0.1:8101 \
  -L 8102:127.0.0.1:8102 -L 8103:127.0.0.1:8103 ubuntu@"$PUBLIC_IP"
```

Open `http://localhost:8090`, Swagger `http://localhost:8090/docs`, and the three portals at localhost:8101/8102/8103. Only use synthetic demo records. App API key is generated on EC2 and stored in `~/lsk-release/.env.business`. Do not print or publish it.

## Cleanup: terminate EC2 and delete SG/key

```bash
export AWS_PROFILE=lsk-development AWS_REGION=us-east-2 AWS_DEFAULT_REGION=us-east-2
bash deploy/aws/ec2/terminate-lab.sh
```

Confirm by typing `TERMINATE EC2`. Wait for termination. Check leftover EBS volumes and snapshots, unusual cost entries and remaining public IPv4 resources. The local private SSH key remains on your workstation until securely deleted.

## Enterprise follow-on

After getting a working user demo, replace the manual EC2 bridge with a protected GitHub Actions deployment job using OIDC roles, reviewed immutable artifacts, GitHub environment required reviewers, secrets management, image registry, automated rollback, and monitored cleanup. Do not present this personal POC as a production deployment.
