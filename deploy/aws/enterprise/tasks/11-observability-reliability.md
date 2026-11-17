# TASK 11 — observability reliability

**Status: LOCKED** until the preceding task passes. This is an implementation requirement specification, **not** a completed Terraform module or a permission to provision resources. You and the reviewer will write and validate the code during this task.

## Goal
Instrument OpenTelemetry traces/metrics/logs, CloudWatch, Prometheus/Grafana, SLO monitoring and alerts, HPA scaling, multi-AZ topology, load/failure testing and incident runbooks.

## Requirements
1. Review the [target architecture](../ARCHITECTURE.md), the [roadmap](../README.md), current code and earlier acceptance reports. Identify dependencies and missing application features before changes.
2. Produce a concrete implementation plan including resource diagrams, Terraform module boundaries, versioned inputs/outputs, IAM trust and permissions, network paths, dependencies, costs, rollback and test plan. Do not copy production account IDs or secrets into code.
3. Implement on a reviewed task-specific feature branch derived from `feature/aws-enterprise-terraform`; keep nonprod/production state and configuration separate. Use remote state with S3 native lockfiles. Pin Terraform provider and module/chart versions, review versions against official support policy.
4. Run `terraform fmt -check -recursive`, `terraform init`, `terraform validate`, static security/policy scans and `terraform plan`; obtain approval before any apply. Inspect for drift/destruction and costly resources.
5. Deploy only to an approved nonproduction AWS account and validate using positive and negative security tests, failure handling and observability. Write a runbook and an explicit cleanup or retention decision.
6. Submit evidence with secret/account metadata redacted. Do not proceed until reviewer verifies the acceptance criteria.

## Acceptance evidence
Show dashboard screenshots, p95 latency, measured error budget, alert notifications, controlled node/AZ failure drill and rollback time.

## Gate
- [ ] Architecture and ADR review complete
- [ ] Terraform lint/validate/plan pass
- [ ] Least privilege, encryption and network boundaries checked
- [ ] Apply approved in correct environment
- [ ] End-to-end and negative test evidence reviewed
- [ ] Cost/rollback/runbook documented

**Do not start this task until approved.**
