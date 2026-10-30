# Proposal

## Why

The platform architecture names AWS EKS as the target topology, but the
repository contains no infrastructure code. A contributor cannot reproduce the
cluster, image registry, or PostgreSQL database, and a deployment has no defined
network, identity, or persistence boundary.

## What Changes

- Add a Terraform root module under `infra/terraform/` that provisions:
  - a VPC with two public and two private subnets across two availability
    zones, an internet gateway, a NAT gateway, and route tables;
  - an EKS cluster with a managed node group in the private subnets, IAM roles,
    and cluster logging;
  - an ECR repository for the `withdrawal-soles` image with scan-on-push and
    immutable tags;
  - a private, encrypted RDS PostgreSQL 15 instance in the private subnets,
    reachable only from the EKS node security group;
  - outputs for the cluster name and endpoint, ECR repository URL, RDS endpoint,
    and VPC identifier.
- Add variables, validation, an example `terraform.tfvars`, and a README with
  init, plan, apply, and destroy instructions.
- Add Terraform formatting, init, and validation checks to CI without requiring
  AWS credentials.
- Keep the database password out of source control and mark secret outputs as
  sensitive.

Out of scope: deploying the application, Traefik, or Kubernetes manifests to
the cluster; provisioning the other five services or their databases; DNS, TLS,
VPN, bastion hosts, multi-region, and production high availability.

## Capabilities

### New Capabilities

- `aws-platform-infrastructure`: network, EKS cluster and node group, ECR
  repository, private RDS PostgreSQL database, outputs, and variable contracts
  for the AWS target environment.

### Modified Capabilities

- None. The existing `platform-architecture` spec already documents AWS EKS as
  the target topology; this change supplies the implementation without changing
  that requirement.

## Impact

- New `infra/terraform/` directory and Terraform provider lock file.
- New optional verification script and CI job for Terraform static checks.
- No runtime change to `withdrawal-soles` and no change to the other services.
- AWS resources created only when an operator runs `terraform apply`; costs
  include EKS, EC2 nodes, NAT gateway, and RDS.
- Harness subsystems affected: state (`feature_list.json`, `progress.md`),
  verification (CI and Terraform checks), scope (one active change), and
  lifecycle (archive after verification).
