# TASK 04A — EKS Kubernetes platform operations

**Status: LOCKED** until Task 04 EKS foundation is provisioned and accepted. This is a hands-on learning and acceptance specification; no infrastructure in this folder has been applied.

## Objective
Operate a private, multi-AZ EKS platform with independently scaled system and application capacity, secure pods, supported add-ons, rescheduling, autoscaling and safe upgrade processes.

## Requirements
1. Verify Terraform EKS topology and account isolation from Task 04. Capture sanitized `aws eks describe-cluster`, `kubectl get nodes -o wide`, `kubectl get pods -A`, and add-on versions/support. Do not publish account IDs, private network details or credentials.
2. Set up dedicated system and workload node groups; ensure no public IPs. Review failure domains across three AZs, cluster API access design, upgrade compatibility and platform costs.
3. Install/version-pin EKS VPC CNI, CoreDNS, kube-proxy as required, EKS Pod Identity Agent, metrics-server, AWS Load Balancer Controller, and OpenTelemetry Collector; verify service accounts, RBAC, Pod Identity and certificates.
4. Implement namespace ResourceQuota and LimitRange, standard securityContext, pod topology spread, rolling updates, readiness/startup/liveness probes, PDB, network policy and restricted RBAC for service operators. Test network policies actually enforce isolation on chosen CNI.
5. Add HPA for stateless workloads using CPU/memory or validated custom metric. Test scaling under bounded synthetic load and measure p95 latency, pods scheduled, cost and scale-down. Note HPA scales pods but **does not add EC2 nodes**.
6. Choose the **node capacity strategy**. Default: EKS managed node groups and its configured cluster node autoscaling strategy. Evaluate Cluster Autoscaler vs Karpenter, not both contending over the same nodes. For Karpenter later, design NodePool, EC2NodeClass, controller IAM/Pod Identity, interruption handling, limits, budgets and disruption safeguards. Validate supported versions before actual installation.
7. Document node drain, rolling upgrade, pod rescheduling, unavailable-zone simulation (in a permitted nonprod cluster), EKS component upgrades and rollback limitations. Do not run disruptive drills without permission.

## Commands to collect evidence
```bash
kubectl cluster-info
kubectl get nodes -o wide
kubectl get pods -A
kubectl get hpa,pdb -A
kubectl auth can-i delete namespaces --as=system:serviceaccount:lsk-poc:lsk-gateway
helm version
kubectl version --client
```

## Acceptance
- [ ] Cluster healthy, version/add-on matrix reviewed, managed nodes private and spread across AZs
- [ ] Least-privilege RBAC and Pod Identity deny prohibited APIs
- [ ] Network policy enforced for an unauthorized namespace
- [ ] HPA scales with load; node scheduling strategy demonstrated and cost reviewed
- [ ] PDB and topology spread keep service available across bounded node maintenance
- [ ] Alerting and step-by-step day-2 runbook for upgrades, rollbacks and on-call
- [ ] Reviewer approves tests and account-cost evidence

**Do not advance until evidence is accepted.**
