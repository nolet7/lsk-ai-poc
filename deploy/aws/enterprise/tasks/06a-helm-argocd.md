# TASK 06A — Enterprise Helm, Argo CD and GitOps release operations

**Status: LOCKED** until tasks 04/04A/05/06 prerequisites pass. Chart and Argo files are learning skeletons, not a ready enterprise release.

## Requirements
1. Establish ownership boundaries: Terraform owns AWS/VPC/EKS/Pod Identity/ECR; Argo CD owns approved cluster application releases. Install Argo CD on private endpoint with corporate identity/RBAC and minimal repo permissions. Review AppProject destination/source allowlists.
2. Run `bash deploy/aws/enterprise/kubernetes/tests/check-gateway-chart.sh` and review [the architecture audit](../kubernetes/OPERATIONS_GAPS.md) before EKS deployment. Pin Helm/chart/Kubernetes versions and immutable digest from signed/scanned ECR build. Run `helm lint` and `helm template` with approved synthetic POC-only values; inspect manifests before sync. Never place credentials in Git or Helm values.
3. Extend `kubernetes/helm/charts/lsk-gateway` with chart templates for each independent business API or separate charts; read-only POC test first. Pilot/production workloads require verified OIDC, Aurora migration, document ACL and admission-policy gates.
4. The starter chart must keep `replicaCount=1` because the existing gateway uses local SQLite and must keep synthetic write routes disabled. Separate pilot/production chart revisions are required after durable state migration. Maintain environment overlays `gitops/environments/poc,pilot,production` in separate accounts/clusters with distinct release policies; do not promote the POC shared-key gateway into pilot/production.
5. Deploy External Secrets Operator (or approved equivalent) to sync Secrets Manager values without committing plaintext keys. Validate encryption/access. Configure dedicated service account identities for gateway/agents/MCP/RAG; prove denial of unauthorized secrets.
6. Argo CD pipeline: signed immutable image -> GitHub PR -> approved digest change -> Argo diff/manual sync -> health/metrics/gates -> rollback. Audit sync and Git commit; prevent direct uncontrolled `kubectl edit` production changes.
7. Add readiness/liveness/startup, resource requests and limits, PDB, HPA, NetworkPolicy and topology spread. Security test unauthorized namespace to app API. Configure app tracing and metrics in OTel.
8. Test pod restart, image rollback, Argo drift reconciliation, missing secret, invalid image digest and blocked non-POC deployment. Observe Argo notifications and incident response.

## Initial chart acceptance commands (require Helm v3 and a valid 64-char digest)
```bash
cd deploy/aws/enterprise/kubernetes/helm/charts/lsk-gateway
helm lint . --set image.repository=example.invalid/lsk-gateway --set image.digest=sha256:$(printf 'a%.0s' {1..64}) --set existingSecretName=lsk-demo-key
helm template lsk . --set image.repository=example.invalid/lsk-gateway --set image.digest=sha256:$(printf 'a%.0s' {1..64}) --set existingSecretName=lsk-demo-key
```
These are **render-only** tests, not deployment instructions; replace fake repository/digest with approved ECR values before deployment. Inspect generated YAML, run kubeconform/admission-policy validation and confirm no Ingress/LoadBalancer is exposed.

## Evidence
- Helm lint/rendered manifests and Git-reviewed values
- ECR immutable digest + CI test/scan/sign provenance
- Approved Argo diff and synced private POC application
- Correct rollback and policy denial tests
- GitOps RBAC, OIDC, secret handling, network isolation and readiness checks
- SRE documentation for install, promotion, failover and incident response

**Stop for reviewer acceptance.**
