# P28-15 Terraform syntax hotfix

Replaces the invalid semicolon-separated HCL declarations from P28-15 in
`deploy/aws/phase28_ec2/{variables,main,outputs}.tf`. Also adds a regression test
that executes `terraform fmt -check -recursive` when Terraform CLI is available.

This ZIP does **not** turn on EC2 or inference (`enabled` remains `false`).

From the repository root (after extracting):

```bash
python -m unittest discover -s phase28/tests -p 'test_terraform_syntax.py' -v
python -m unittest discover -s phase28/tests -v
cd deploy/aws/phase28_ec2
terraform fmt -recursive
terraform init -backend=false
terraform validate
cd ../../..
```

Do not run `terraform apply`. Once Terraform validation passes, stage the
P28-15 files plus these changes and commit them together.
