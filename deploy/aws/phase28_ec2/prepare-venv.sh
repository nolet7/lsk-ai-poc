#!/usr/bin/env bash
# Offline, explicit, per-SHA environment preparation; requires operator-audited wheelhouse + hash lock.
set -euo pipefail
if [[ "${EUID}" -ne 0 || $# -ne 3 ]]; then
  echo 'Usage: sudo bash prepare-venv.sh <40-char-sha> <approved-wheelhouse> <hashed-lockfile>' >&2; exit 2
fi
SHA="$1"; WHEELHOUSE="$(realpath -- "$2")"; LOCK="$(realpath -- "$3")"
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid revision' >&2; exit 2; }
ROOT=/opt/lsk-phase28
[[ -f "$ROOT/releases/$SHA/requirements-p28-13.txt" && -d "$WHEELHOUSE" && -f "$LOCK" ]] || exit 2
[[ ! -e "$ROOT/venvs/$SHA" ]] || { echo 'Immutable venv already exists' >&2; exit 2; }
mkdir -p "$ROOT/venvs"
TMP="$(mktemp -d "$ROOT/venvs/.preparing-XXXXXXXX")"
trap 'rm -rf -- "$TMP"' EXIT
python3 -m venv "$TMP"
"$TMP/bin/python" -m pip install --no-index --find-links "$WHEELHOUSE" --require-hashes -r "$LOCK"
"$TMP/bin/python" -c 'import fastapi, uvicorn, jwt, cryptography'
# Only an operator-approved lock should be accepted; installed env is never auto-updated.
chmod -R go-w "$TMP"
mv -- "$TMP" "$ROOT/venvs/$SHA"
trap - EXIT
