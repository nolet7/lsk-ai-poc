#!/usr/bin/env bash
# P28-17: runtime resolves source and interpreter from the SAME approved SHA.
set -euo pipefail
ROOT=/opt/lsk-phase28
link="$(readlink -- "$ROOT/current")" || { echo 'No current release link' >&2; exit 1; }
[[ "$link" =~ ^releases/([0-9a-f]{40})$ ]] || { echo 'Untrusted current release link' >&2; exit 1; }
sha="${BASH_REMATCH[1]}"
[[ -f "$ROOT/releases/$sha/phase28/container_entry.py" ]] || exit 1
[[ -x "$ROOT/venvs/$sha/bin/python" ]] || { echo 'No matching approved venv' >&2; exit 1; }
cd -- "$ROOT/releases/$sha"
exec "$ROOT/venvs/$sha/bin/python" -m uvicorn phase28.container_entry:app --host 127.0.0.1 --port 8080 --workers 1
