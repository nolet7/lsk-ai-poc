#!/usr/bin/env bash
# P28-18: READ ONLY. Run inside an operator-approved SSM Session Manager session.
# No mkdir, package install, systemctl restart, AWS API, or cloud resource mutation.
set -euo pipefail
[[ "$(uname -s)" == Linux ]] || { echo 'Linux required' >&2; exit 2; }
ROOT=/opt/lsk-phase28
[[ -d "$ROOT" && ! -L "$ROOT" ]] || { echo 'Unexpected release root' >&2; exit 2; }
command -v systemctl >/dev/null
command -v nginx >/dev/null
command -v ss >/dev/null
command -v flock >/dev/null
# Do not acquire the writer lock: -n ensures preflight fails rather than waiting
# for an active deployment. Existing lock file is never deleted.
[[ -f "$ROOT/.release-lock" && ! -L "$ROOT/.release-lock" ]] || { echo 'Release lock not initialized' >&2; exit 2; }
(
  flock -n 9 || { echo 'Deployment currently locked' >&2; exit 2; }
  echo 'Release lock available'
) 9<"$ROOT/.release-lock"
nginx -t
systemctl is-enabled lsk-phase28.service
systemctl is-active lsk-phase28.service
ss -lnt
# The diagnostic application must not listen on non-loopback TCP sockets.
# Operator must REVIEW ss output for unrelated listeners and default NGINX sites.
python3 - <<'PY'
import urllib.request, urllib.error
base='http://127.0.0.1:18080'
with urllib.request.urlopen(base+'/health/live',timeout=3) as r:
    assert r.status == 200
for uri in ('/health/ready','/v1/business/questions'):
    try:
        urllib.request.urlopen(base+uri,timeout=3)
    except urllib.error.HTTPError as exc:
        if exc.code != 503:
            raise
    else:
        raise RuntimeError('Diagnostic endpoint unexpectedly available')
print('PASS: 127.0.0.1 diagnostic gate; business access closed')
PY
printf '%s\n' 'READ-ONLY CHECKS FINISHED: no approval or host identity was verified; review output before any change.'
