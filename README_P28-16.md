# P28-16 — Dockerless versioned EC2 diagnostic releases

## Acceptance scope
A **single-instance, diagnostic-only** release manager for the pre-existing Phase28 EC2 `systemd`/Uvicorn service. No Docker, AWS calls, package download, public ingress, or model inference. The code provides isolated release staging, an atomic **symlink replacement**, serialized operator execution on Linux (`flock`), immediate `systemd` restart, fail-closed loopback smoke checks, and automatic attempt to restore the previous release on restart/health failure. Tests inject fake restart/probe callbacks: they never run systemd or make network calls.

The existing service already uses `WorkingDirectory=/opt/lsk-phase28/current`. **Do not change that contract.** The P28-15 installer creates `/opt/lsk-phase28/current` as a *real directory*: the new release manager refuses to overwrite that directory. **Existing installations need a carefully reviewed one-time manual migration**, maintenance window, backups and a rollback plan. This package does not automate that migration.

## Local Git Bash (Windows) acceptance, no Docker

```bash
unzip -o ~/Downloads/P28-16-dockerless-releases.zip
python -m py_compile phase28/release_manager.py phase28/tests/test_release_manager.py
python -m unittest discover -s phase28/tests -p 'test_release_manager.py' -v
python -m unittest discover -s phase28/tests -v
```

Expected full-suite count based on P28-15 is **159** (149 previous + 10 new). The 10 new tests were executed in Linux with an isolated fixture. Your Windows full suite is not yet verified.

## Operator-approved EC2 workflow (not for local Windows or live use yet)

**Prerequisites and TASKs:** Approved maintenance/change ticket; version-pinned clean source checkout at full reviewed 40-character Git SHA, verified source provenance; existing `systemd` service/virtualenv with matching dependencies; disabled inference; strict root-controlled `/opt/lsk-phase28`; no public listeners. Install and smoke test the diagnostic P28-15 system first. This module cannot implement identity integrations or safe package upgrades.

**Do not run these until a manual P28-15 current-directory migration is completed.** All commands below are examples performed **on the EC2 host** by an approved operator using SSM; no SSH key or Docker needed.

```bash
# Reviewed checkout at an exact full commit SHA and CLEAN working tree.
export REVISION="<APPROVED_FULL_40_CHARACTER_GIT_SHA>"
export CHECKOUT="/srv/lsk-ai-poc-reviewed"

# Ensure operator-approved release dependencies are installed into the existing
# /opt/lsk-phase28/venv; never modify a live shared venv mid-rollback.
sudo /usr/bin/python3 "$CHECKOUT/phase28/release_manager.py" stage \
  --checkout "$CHECKOUT" --revision "$REVISION"
sudo /usr/bin/python3 "$CHECKOUT/phase28/release_manager.py" status
sudo /usr/bin/python3 "$CHECKOUT/phase28/release_manager.py" activate --revision "$REVISION"

# On failure, activation attempts to restore previous link and restart service.
# To explicitly select a prior staged revision:
sudo /usr/bin/python3 "$CHECKOUT/phase28/release_manager.py" rollback \
  --revision "<PREVIOUS_APPROVED_FULL_GIT_SHA>"
```

The manager rejects a dirty checkout or revision mismatch. Staging copies Python source (`phase28/**/*.py`, excluding tests) and `requirements-p28-13.txt`; staging does **not** install Python packages or verify signed commits. An independent artifact attestation/provenance mechanism remains required for production. Each release is staged once; no automatic pruning. `activate` does not enable inbound security-group rules, Bedrock, or business APIs. The smoke probe expects `/health/live` 200, `/health/ready` 503, business POST forbidden/unavailable, all via `127.0.0.1:18080`.

### Known gaps before deployment

- **No real AWS deployment tested**; actual systemd/NGINX/EBS behavior must be checked with approved SSM operator access.
- Before first use on a P28-15 instance, migrate the existing non-symlink `current` directory to the versioned-release layout. The tool deliberately refuses to do this itself.
- Releases share a Python virtual environment. For dependency changes, create an independently versioned virtualenv and update the service deployment plan; otherwise rollback may not restore dependency compatibility.
- Atomic link switching is not a zero-downtime deployment and cannot guarantee recovery across power loss or failed rollback. Observe journal and manually reconcile before returning service to use.
- The diagnostic app **never serves business traffic**. Do not expose publicly or enable live inference. OIDC discovery/refresh, real scoped retrieval, durable audit, centralized budget and production readiness are separate work.

## Engineer review and commit

```bash
git diff --check
git add phase28/release_manager.py phase28/tests/test_release_manager.py README_P28-16.md
git commit -m "feat(phase28): add Dockerless versioned diagnostic releases and rollback"
git push origin feature/phase28-bedrock-ai-lab
git status --short
```
