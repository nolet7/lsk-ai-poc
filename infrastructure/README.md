# LSK AI Platform — AWS EC2 POC (without Docker)

This folder provisions **one Ubuntu 24.04 EC2 machine** for the Sales, Marketing, Finance, and AI Gateway Python services. It does **not** deploy application code or use Docker. Deploy and operate the Python services after SSH connectivity is working.

## Prerequisites
- AWS CLI signed in as an authorized identity; region `us-east-1`.
- Appropriate EC2 permissions (`Describe*`, `RunInstances`, tagging and related actions).
- A verified Ubuntu 24.04 Canonical AMI, an existing VPC subnet, security group, and imported SSH key.
- Check AWS credit eligibility, billing, and budget alerts before launching.
- Security group inbound port 22 **only from your current /32 public IP**. Do not open 8090–8103 publicly.

## Git Bash on Windows

```bash
git switch poc
git pull --ff-only origin poc
cp infrastructure/config.env.example infrastructure/config.env
code infrastructure/config.env
bash infrastructure/status-ec2.sh
bash infrastructure/launch-ec2.sh
bash infrastructure/status-ec2.sh
```

The launch script checks for existing instances by the `Name` tag, verifies the AMI owner and key/network IDs, and requires typing `LAUNCH` before creating a billable instance. It uses a fresh AWS client token for each launch attempt. It does not create an SSH key or change firewall rules.

If a CLI call fails, **do not immediately rerun launch**. Inspect instances and errors first:

```bash
aws ec2 describe-instances --region us-east-1 \
  --filters 'Name=instance-state-name,Values=pending,running,stopping,stopped' \
  --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags]' --output table
```

## SSH

```bash
ssh -i ~/.ssh/lsk-ai-poc ubuntu@<EC2_PUBLIC_IP>
```

Verify the server's SSH host fingerprint before trusting it. Prefer local SSH tunnels for access to application APIs. `infrastructure/config.env` is local-only and must not contain cloud credentials.

## Costs and stopping

A running instance, EBS volume, and public IPv4 can incur charges; stopping an instance stops compute charges but **not** all storage/address charges. Use the EC2 console to stop or terminate the instance after testing. Termination with DeleteOnTermination enabled deletes the root EBS volume and its application data; back up anything important first.
