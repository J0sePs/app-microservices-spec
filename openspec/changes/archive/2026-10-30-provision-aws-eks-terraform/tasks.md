# Tasks

## 1. Terraform root scaffolding

- [x] 1.1 Create `infra/terraform/versions.tf`, `providers.tf`, `variables.tf`, and `locals.tf` with pinned Terraform/provider versions, input validation, and common tags; verify `terraform fmt -check` and `terraform validate` succeed.
- [x] 1.2 Create `infra/terraform/.gitignore` for state, plans, and variable files; verify `git status` does not show local state or secrets after initialization.

## 2. Network

- [x] 2.1 Create the VPC, two public subnets, two private subnets, internet gateway, NAT gateway, and route tables in `network.tf`; verify `terraform validate` succeeds and the plan lists both subnet tiers in two AZs.
- [x] 2.2 Add EKS subnet discovery tags and private routing through the NAT gateway; verify the plan shows no public IP association for private subnets and a default route to the NAT gateway.

## 3. EKS cluster and nodes

- [x] 3.1 Create the cluster and node IAM roles and attach the EKS cluster, worker, CNI, and ECR read policies in `iam.tf`; verify `terraform validate` and the plan includes all policy attachments.
- [x] 3.2 Create the cluster and node security groups with control-plane and node communication rules in `security-groups.tf`; verify the plan shows the rules and no unrestricted database ingress.
- [x] 3.3 Create the EKS cluster with logging and private/public endpoint configuration in `eks.tf`; verify the plan includes the cluster, role, and subnet associations.
- [x] 3.4 Create the node launch template and managed node group in the private subnets; verify the plan shows the desired capacity and the 1-3 scaling bounds.

## 4. Image registry

- [x] 4.1 Create the ECR repository with scan-on-push, immutable tags, and AES256 encryption in `ecr.tf`; verify the plan shows the repository settings and the repository URL output.

## 5. Database

- [x] 5.1 Create the RDS subnet group, security group, and encrypted PostgreSQL 15 instance in `rds.tf`; verify the plan shows a private instance, port 5432, and ingress only from the node security group.
- [x] 5.2 Add the sensitive database password variable with no default and mark the connection outputs sensitive; verify a plan without the variable fails before creating resources.

## 6. Outputs and operator documentation

- [x] 6.1 Add outputs for the VPC, EKS cluster name and endpoint, certificate authority, ECR URL, RDS endpoint, and database name; verify the plan displays the output changes and marks secrets sensitive.
- [x] 6.2 Write `infra/terraform/README.md` and `terraform.tfvars.example` with init, plan, apply, kubectl, and destroy instructions; verify the documented static commands run as written and the example contains no secret.
- [x] 6.3 Update the architecture deployment notes and root README with the Terraform location and verification commands; verify links resolve and `openspec validate provision-aws-eks-terraform --strict` passes.

## 7. Verification and handoff

- [x] 7.1 Add `scripts/verify-terraform.sh` and a CI job for fmt, init, and validate without AWS credentials; verify the script exits successfully from a clean checkout.
- [x] 7.2 Run `terraform fmt -check -recursive`, `terraform init -backend=false`, `terraform validate`, and a credentialed `terraform plan`; verify the plan includes the VPC, EKS cluster, node group, ECR repository, and RDS instance.
- [x] 7.3 Record Terraform evidence in `feature_list.json`, update `progress.md` and `session-handoff.md`, and run `./init.sh`; verify the harness reports 5/5 subsystems and all checks pass.

## Workflow follow-up

- Apply only after explicit cost approval from the account owner; then confirm the cluster, node group, ECR repository, and RDS instance with the documented outputs.
- Archive the change after review and evidence are complete, then confirm the `aws-platform-infrastructure` spec is in `openspec/specs/`.
