#!/usr/bin/env bash
set -euo pipefail
# Run with sudo on a reviewed Ubuntu 24.04 EC2 instance after checkout.
# No network service is exposed publicly. Use a clean pinned checkout.
if [[ "${EUID}" -ne 0 ]]; then echo 'Run as root via sudo' >&2; exit 1; fi
if [[ $# -ne 1 ]]; then echo 'Usage: sudo bash install-from-checkout.sh /absolute/path/to/repo' >&2; exit 1; fi
REPO="$(realpath -- "$1")"
[[ -f "$REPO/requirements-p28-13.txt" && -f "$REPO/phase28/container_entry.py" ]] || { echo 'Invalid checkout' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'Install python3 and python3-venv from approved OS packages first' >&2; exit 1; }
command -v nginx >/dev/null || { echo 'Install NGINX from approved OS packages first' >&2; exit 1; }
getent passwd lskphase28 >/dev/null || useradd --system --home /nonexistent --shell /usr/sbin/nologin lskphase28
install -d -m 0755 -o root -g root /opt/lsk-phase28
python3 -m venv /opt/lsk-phase28/venv
/opt/lsk-phase28/venv/bin/python -m pip install --disable-pip-version-check -r "$REPO/requirements-p28-13.txt"
# Task: lock dependencies with hashes in production and scan artifacts before release.
install -d -m 0755 -o root -g root /opt/lsk-phase28/current
cp -a "$REPO/phase28" /opt/lsk-phase28/current/
find /opt/lsk-phase28/current -type d -exec chmod 0755 {} +
find /opt/lsk-phase28/current -type f -exec chmod 0644 {} +
chown -R root:root /opt/lsk-phase28/current
install -m 0644 "$REPO/deploy/aws/phase28_ec2/lsk-phase28.service" /etc/systemd/system/lsk-phase28.service
install -m 0644 "$REPO/deploy/aws/phase28_ec2/nginx-diagnostic.conf" /etc/nginx/conf.d/lsk-phase28.conf
nginx -t
systemctl daemon-reload
systemctl enable --now lsk-phase28.service
systemctl reload nginx
