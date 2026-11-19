# Fast path — run the private AI pilot (no Docker)

**Branch**: `feature/phase28-ai-deploy`. This is an opt-in pilot, not a public production application.

### Your laptop: verify

```bash
git fetch origin
git switch feature/phase28-ai-deploy
python -m pip install -r requirements-p28-13.txt
python -m unittest discover -s phase28/tests -v
```

### Existing approved private EC2: install

Use Session Manager; no public SSH or port 8081 ingress. Transfer a reviewed full-SHA checkout.
Follow `README_DEPLOY_AI_AWS.md` for IAM/JWKS/RBAC/OS preflight.

```bash
sudo bash deploy/aws/phase28_ec2/install-ai.sh "$PWD"
# Operator must prepare:
# /etc/lsk-phase28-ai/jwks.json   -- public keys from your trusted issuer
# /etc/lsk-phase28-ai/rbac.json   -- approved grants
# /etc/lsk-phase28-ai/pilot.env   -- copy ai.env.example and fill
sudo chmod 0640 /etc/lsk-phase28-ai/jwks.json /etc/lsk-phase28-ai/rbac.json /etc/lsk-phase28-ai/pilot.env
sudo chown root:lskphase28 /etc/lsk-phase28-ai/jwks.json /etc/lsk-phase28-ai/rbac.json /etc/lsk-phase28-ai/pilot.env
CHECKOUT="$PWD"  # Capture the reviewed checkout before changing directory
cd /opt/lsk-phase28-ai/app
sudo -u lskphase28 /opt/lsk-phase28-ai/venv/bin/python -m phase28.seed_pilot \
  --db /var/lib/lsk-phase28-ai/data.db \
  --input "$CHECKOUT/deploy/aws/phase28_ec2/sample-sources.json"
```

**The sample JSON lives in the checkout, not the installed app** (`install-ai.sh` copies only `phase28`).
Run the seeding command with `--input /path/to/reviewed/checkout/deploy/aws/phase28_ec2/sample-sources.json`.
Demo JWT must have `tenant_id=demo-tenant` and a role authorized for `orders`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now lsk-phase28-ai
curl -fsS http://127.0.0.1:8081/health/ready
```

From your laptop, use SSM port forwarding on port 8081 and a **real OIDC access token**
as described in `README_DEPLOY_AI_AWS.md`.
Set both opt-in flags only after Bedrock IAM/model/cost review to enable paid calls.

### Current limitations

No private cloud infrastructure has been applied for you. Deployment requires an approved
EC2 instance, authenticated SSM access, a real configured OIDC provider/JWKS, an approved
Bedrock model and IAM role. The internal audit and request cap are SQLite single-host
pilot controls, not enterprise production controls.
