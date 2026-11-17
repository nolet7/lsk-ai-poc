#!/usr/bin/env bash
# Render-only, no AWS resources created. Requires helm v3 and Python 3.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHART="$ROOT/helm/charts/lsk-gateway"
DIGEST="sha256:$(printf 'a%.0s' {1..64})"
DIR="$(mktemp -d)"
trap 'rm -rf "$DIR"' EXIT
ARGS=(--set-string image.repository=example.invalid/lsk-gateway --set-string image.digest="$DIGEST" --set-string existingSecretName=lsk-poc-test-key)
helm lint "$CHART" "${ARGS[@]}"
helm template lsk "$CHART" --namespace lsk-poc "${ARGS[@]}" > "$DIR/rendered.yaml"
python3 - "$DIR/rendered.yaml" <<'PY'
import sys
from pathlib import Path
data=Path(sys.argv[1]).read_text()
assert "kind: ServiceAccount" in data, "Missing ServiceAccount"
assert "kind: Deployment" in data, "Missing Deployment"
assert "kind: Service" in data, "Missing ClusterIP Service"
assert "kind: NetworkPolicy" in data, "Missing NetworkPolicy"
assert "type: ClusterIP" in data, "Expected internal-only service"
assert "automountServiceAccountToken: false" in data, "Token should not auto mount"
assert "runAsNonRoot: true" in data, "Non-root required"
assert "allowPrivilegeEscalation: false" in data, "Privilege escalation must be off"
assert "kind: Ingress" not in data, "POC cannot have external ingress"
print("PASS: internal-only POC helm structure and baseline pod security")
PY
if helm template lsk "$CHART" --namespace lsk-poc "${ARGS[@]}" --set env.stage=production > "$DIR/invalid.log" 2>&1; then
  echo "FAIL: production stage incorrectly permitted" >&2; exit 1
fi
if helm template lsk "$CHART" --namespace lsk-poc "${ARGS[@]}" --set service.type=LoadBalancer > "$DIR/invalid.log" 2>&1; then
  echo "FAIL: public service incorrectly permitted" >&2; exit 1
fi
if helm template lsk "$CHART" --namespace lsk-poc "${ARGS[@]}" --set replicaCount=2 > "$DIR/invalid.log" 2>&1; then
  echo "FAIL: unsafe POC replica scaling permitted" >&2; exit 1
fi
if helm template lsk "$CHART" --namespace lsk-poc "${ARGS[@]}" --set env.enableDemoWrites=true > "$DIR/invalid.log" 2>&1; then
  echo "FAIL: unsafe demo writes permitted" >&2; exit 1
fi
echo "PASS: negative deployment safety controls"
