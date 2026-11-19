#!/usr/bin/env bash
# Connected build host: match target Linux/Python ABI. Review and hash artifacts before transfer.
set -euo pipefail
[[ "$#" == 1 ]] || { echo "Usage: bash build-wheelhouse.sh /absolute/output" >&2; exit 2; }
OUT="$(mkdir -p "$1" && cd "$1" && pwd)"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
python3 -m pip download --only-binary=:all: --dest "$OUT" -r "$ROOT/requirements-p28-13.txt" boto3
(cd "$OUT" && sha256sum ./*.whl > SHA256SUMS)
echo "Review dependency licenses, pinned resolved versions and SHA256SUMS. Do not use arbitrary untrusted wheels."
