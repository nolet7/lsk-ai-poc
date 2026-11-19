# P28-18 — Supervised diagnostic EC2 release gates (Docker-free)

## Delivered, and NOT delivered
This is an **offline approval-record validator**, a **read-only host diagnostic probe**, a GitHub Actions Linux test gate, and an operator runbook. It does NOT create a Systems Manager association/document or call SSM APIs, deploy software, migrate a live instance, prove approval authenticity, or authorize AWS operations. All real operations remain manual and require an independently authorized operator and reviewed IAM/SSM change controls.

Application remains diagnostic-only: /health/live HTTP 200; /health/ready HTTP 503; business requests HTTP 503. AI inference off. Terraform `enabled=false`; no AWS apply or public access.

## Test in Windows Git Bash (from repo root)
```bash
unzip -o ~/Downloads/P28-18-supervised-ec2-gates.zip
python -m py_compile phase28/supervised_preflight.py phase28/tests/test_supervised_preflight.py
python -m unittest discover -s phase28/tests -p 'test_supervised_preflight.py' -v
python -m unittest discover -s phase28/tests -v
bash -n deploy/aws/phase28_ec2/host-readonly-preflight.sh
```
There are 10 additional P28-18 tests. Expected Windows total **177 tests: 167 passed, 10 Linux-only skipped** (assuming previously reported 167 total / 10 skipped); Linux CI should execute all 177 with zero skips. CI status must be checked separately in GitHub Actions.

## Operator preflight — offline, NO privileges or cloud actions
1. Create a real change ticket in your company's system, independently approve deployment. Use the example JSON only as a schema reference; replace fake metadata and timestamps. Never commit real approval records if they identify internal account/instance information.
2. In a controlled checkout, verify the exact commit and signature/provenance independently: `git status --porcelain`, `git rev-parse HEAD`, relevant GitHub Actions Linux CI and artifact manifest. This module does not verify Git identity or signed commits.
3. Create a private evidence directory (`mkdir -p ./private-p28-evidence`), ensure it is ignored by Git, and run:
```bash
python -m phase28.supervised_preflight --approval-file /absolute/private/approval.json --checkout . --evidence-dir /absolute/private/evidence
```
This only validates the attestation shape/time window and required files. The receipt clearly states `record-validated-not-host-authorized` and must NOT be treated as deployment permission. Keep the receipt in approved auditable storage; local receipts are not tamper-evident or durable enterprise audit records.
4. Have the authorized operator connect via approved **AWS Systems Manager Session Manager**, verify the *actual* AWS account/region/instance and live environment identity independently, and execute the read-only script in the private instance: `bash deploy/aws/phase28_ec2/host-readonly-preflight.sh`. The script intentionally expects the diagnostic app to be running and the release lock file to exist. If either is absent, it fails; investigate without deleting locks.

## Critical change-window procedure (DOCUMENTATION ONLY — no automated rollout)
- Pre-deploy: require approvals, valid Linux CI, reviewed dependency wheelhouse with hashes, verified release SHA, immutable artifact copy, SSM permissions scoped to the intended instance, controlled session logs, lock owner and rollback revision.
- Inspect `/opt/lsk-phase28/current`, `/opt/lsk-phase28/legacy-current-backup`, per-revision `venvs`, running systemd unit, `nginx -t`, loopback listeners, disk free space, and SSM reachability.
- **STOP** on mismatched unit, revision, instance identity, permissions, stale/non-releasable lock, missing systemd host dependencies or failed read-only health probes.
- Legacy migration (`phase28.ec2_rollout.migrate_legacy`) requires service stop, exclusive deployment lock, a known good staged release and venv, and trusted restart/probe callbacks. It is **NOT** wired into a production operator CLI. Never invoke it casually on EC2.
- P28-16 `release_manager` activation requires the same supervised lock. Its probe tests diagnostic endpoints and attempts rollback. Run and review Linux failure drills before any production adoption.
- Recovery: consult systemd journal and release links, stop traffic changes, retain previous release and legacy backup, document a change incident, perform a supervised restore with operator escalation if probes fail.

## Architecture limitations and engineering TODOs
- Implement real SSM Run Command document with explicit IAM instance allowlist, signed artifact verification, operator confirmation, narrow sudo commands, strict revision validation, S3 or CloudWatch audit evidence, and automatic failure stop. **Do not deploy a document granting broad shell access.**
- For production business queries: implement trusted OIDC discovery/rotation, database tenant ACL filtering, durable audit, real readiness checks, TLS ingress, observability, SLOs and operational tests.
- The P28-17 `prepare-venv.sh` requires an operator-produced hashed dependency lock and wheelhouse; neither is supplied. Validate software supply chain before host rollout.
- Current Phase28 EC2 config is no-ingress, no public-IP and billable only when explicitly enabled. IAM/S3/SSM permissions, private network paths and base OS are not provisioned by this patch.
- Current Linux CI success is **not established** by local offline tests; verify after pushing.
