#!/usr/bin/env bash
# Explicit operator-only installation on an approved PRIVATE Ubuntu 24.04 EC2 instance.
set -euo pipefail
if [[ "${EUID}" -ne 0 || $# -ne 1 ]]; then
 echo 'Usage: sudo bash deploy/aws/phase28_ec2/install-ai.sh /absolute/pinned/checkout' >&2; exit 2
fi
REPO="$(realpath -- "$1")"
[[ -f "$REPO/phase28/live_app.py" && -f "$REPO/requirements-p28-13.txt" ]] || exit 2
command -v python3 >/dev/null || exit 2
command -v systemctl >/dev/null || exit 2
getent passwd lskphase28 >/dev/null || useradd --system --home /nonexistent --shell /usr/sbin/nologin lskphase28
install -d -m 0755 -o root -g root /opt/lsk-phase28-ai
if [[ -e /opt/lsk-phase28-ai/app ]]; then echo 'Existing app: use reviewed release process instead' >&2; exit 2; fi
python3 -m venv /opt/lsk-phase28-ai/venv
/opt/lsk-phase28-ai/venv/bin/python -m pip install -r "$REPO/requirements-p28-13.txt" boto3
install -d -m 0755 -o root -g root /opt/lsk-phase28-ai/app
cp -a "$REPO/phase28" /opt/lsk-phase28-ai/app/
chown -R root:root /opt/lsk-phase28-ai/app
install -d -m 0700 -o lskphase28 -g lskphase28 /var/lib/lsk-phase28-ai
install -d -m 0750 -o root -g lskphase28 /etc/lsk-phase28-ai
install -m 0644 "$REPO/deploy/aws/phase28_ec2/lsk-phase28-ai.service" /etc/systemd/system/lsk-phase28-ai.service
echo 'Install reviewed JWKS and RBAC files at /etc/lsk-phase28-ai, and an operator-owned environment file.'
echo 'Initialize DB as service user; then systemctl daemon-reload && systemctl enable --now lsk-phase28-ai.'
echo 'Do not expose TCP 8081 publicly. Live Bedrock requires explicit IAM/model/cost approval.'
