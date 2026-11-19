# P28-14 — Diagnostic container and offline CI (fail closed)

This is a **diagnostic container**, not a functioning public customer gateway. The existing `create_app(...)` factory requires real, trusted OIDC JWKS, tenant-filtered storage, and a durable audit backend. P28-14 intentionally does not manufacture these dependencies. `/health/live` returns HTTP 200, `/health/ready` returns HTTP 503, and `/v1/business/questions` returns HTTP 503. It exposes no Service or Ingress; the Kubernetes Deployment has zero replicas and an unresolvable image name. Nothing should be applied or exposed publicly.

## Install and validate

From repository root:

```bash
unzip -o ~/Downloads/P28-14-gateway-packaging.zip
python -m pip install -r requirements-p28-13.txt
python -m unittest discover -s phase28/tests -p 'test_container_entry.py' -v
python -m unittest discover -s phase28/tests -v
```

Optional local container build (requires Docker engine):

```bash
docker build -f deploy/aws/phase28_gateway/Dockerfile -t phase28-gateway:local .
docker run --rm -p 127.0.0.1:18080:8080 phase28-gateway:local
# In another terminal: curl -i http://127.0.0.1:18080/health/live
# curl -i http://127.0.0.1:18080/health/ready  # expect 503
```

## CI safety gates

GitHub Actions runs the full Python suite, `pip-audit` dependency scan, local Docker build, and diagnostic HTTP smoke test. No AWS credentials, cloud deployments, image pushes, or paid inference. The `pip-audit` command deliberately fails when vulnerable package resolutions are found; update/pin reviewed dependencies rather than ignoring vulnerabilities. Image vulnerability/SBOM scanning and digest-pinned action attestations should be added as separate production release gates. GitHub-hosted runners may require network to fetch dependencies and base images.

## Deployment and rollback

The sample Kubernetes Deployment intentionally sets `replicas: 0`, lacks Ingress/Service, and uses `registry.invalid` image placeholder. No live deploy should be attempted. A future production readiness milestone must implement trusted HTTPS JWKS refresh/rotation, independent tenant filters in storage, durable audit, request limits, centrally enforced quota, identity validation, external TLS and ingress controls, supply-chain scan, versioned digests, and effective readiness checks. Use revisioned Kubernetes rollout and `kubectl rollout undo deployment/<name>` only after a real release is approved and established. **Do not enable** `AI_LIVE_INFERENCE` or `AI_LIVE_INFERENCE_ACK`.
