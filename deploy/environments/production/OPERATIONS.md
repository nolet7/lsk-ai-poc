# Production-style deployment operations

## Safe sequence
1. Resolve IAM/SSO, networking, endpoint and regional model requirements in the **target account**; this IaC has never been applied.
2. Create an organization-controlled ECR repository, push scanned immutable image, note digest; create ACM certificate and operator-controlled JWKS Secrets Manager secret.
3. Use two private subnets in different AZs, corresponding route tables, approved trusted client CIDRs, and private DNS enabled.
4. Run Terraform with `enabled=true, approved_release=true, bootstrap_mode=true`. **This creates billable ALB, RDS, endpoints, ECS etc but launches zero API tasks**. SSO identity must have approvals and change log.
5. Start the dedicated one-shot migration task (not the normal API task definition), in approved isolated subnets:
```bash
aws ecs run-task --cluster lsk-p28-prod --launch-type FARGATE \
  --task-definition lsk-p28-prod \
  --network-configuration 'awsvpcConfiguration={subnets=[subnet-REPLACE-AZ1,subnet-REPLACE-AZ2],securityGroups=[sg-REPLACE-TASK],assignPublicIp=DISABLED}' \

```
Record task exit code and inspect sanitized CloudWatch Logs. Create only synthetic seed records through reviewed database tool access. Migration uses an isolated task execution role with the RDS managed master password and separately supplied app credential. API/MCP tasks receive the restricted app secret only. Confirm DB grants and RDS TLS verification before enabling API tasks.
6. Set `bootstrap_mode=false`, plan, approve and apply. Verify tasks healthy behind internal **HTTPS** ALB.
7. Test OIDC signed requests, 401/403 cross-tenant, abstention and denied inference; enable inference only with approved model/region/IAM/finance caps.
8. Test two-AZ failover, rollback, restore, secret rotation and operational alerts before asserting production readiness.

## Known required production enhancements
- Dedicated restricted DB application role must be verified with denied DDL/privilege tests in target RDS.
- Enforce actual USD/token budgets, add alarms and detailed Bedrock quality evaluations.
- OIDC JWKS is loaded at startup: rotate by updating trusted secret and rolling ECS tasks.
- DB trust bundle: production app defaults to OS CA store for verify-full. Mount organization-approved RDS CA bundle at specified `LSK_DB_CA_CERT` or include approved certificate in image if OS bundle lacks RDS CA; prove TLS verification in a task.
- Internal ALB HTTPS listener terminates TLS; ALB to ECS currently HTTP on private SG-restricted network; apply full in-transit TLS if required by organizational policy.
- Install AWS WAF / private API Gateway or other enterprise ingress controls if enterprise policy requires; current listener ingress is allowlisted CIDR only.
- Implement immutable audit offload and database PITR restore drills, IAM policies for endpoint access and key rotation.
- Snapshot/DR, IAM permission boundaries, cost alerts and enterprise business connectors remain validation/implementation gates.

## Rollback
Apply previously reviewed ECR digest and task definition; rollback circuit breaker handles health-related deployment failure. Do not automatically downgrade database schema. Backup/restore via approved RDS runbook.

## Database secret prerequisite

Create and authorize an existing AWS Secrets Manager secret for the application
with JSON keys `username` and `password`. The username must match
`[a-z_][a-z0-9_]{2,30}` and the password must contain at least 24 characters.
Set `app_db_secret_arn` in ignored Terraform variables. Do not put credentials
directly in Terraform or Git. Migrations must finish and database access
checks must pass before `bootstrap_mode=false`. The administrator password
is injected **only into the one-shot migration task**.
