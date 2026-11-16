# Kubernetes reference deployment — synthetic LSK gateway only

**NOT a production-certified manifest.** This example isolates a single commercial API gateway with non-root containers, resource requests/limits, liveness/readiness probes and NetworkPolicy. It does not create an EKS cluster, IAM role, OIDC provider, business database, certificate, WAF, or any of the three downstream business services.

## Required dependencies
- A private cluster with NetworkPolicy-capable CNI and validated DNS/egress policy.
- A signed, immutable container image built from `integrations/Dockerfile`.
- A Kubernetes secret `lsk-gateway-credentials` holding distinct `GATEWAY_API_KEY`, `DEMO_API_KEY`; never check values into Git.
- Three services `lsk-sales`, `lsk-marketing`, `lsk-finance` in the same namespace and accessible only through allowed network paths.
- The gateway uses Bedrock only with an approved EKS Pod Identity/IRSA role (not static access keys) and an authorized model ID.

The manifest defaults to explicit `LSK_STAGE=poc`, `LSK_ENABLE_DEMO_WRITES=false`; it MUST NOT be used for production customer traffic. Configuration of Bedrock permissions, managed ingress and observability is the cluster platform team's responsibility.

## Design only — do not apply without substitution
Replace `REPLACE_WITH_SIGNED_IMAGE_DIGEST` with a verified digest, then review manifests and validate dependencies:

```bash
kubectl kustomize deploy/k8s/base
kubectl diff -k deploy/k8s/base
```

A syntactically valid manifest and successful pods do not establish enterprise readiness. Deployment requires an environment-specific admission policy, network testing, real OIDC identity, secret rotation, RAG ACL tests and backup/DR evidence. See `docs/RELEASE_GATES.md`.
