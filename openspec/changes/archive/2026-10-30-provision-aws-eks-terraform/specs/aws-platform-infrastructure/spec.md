# Spec Delta

## Purpose

Defines the reproducible AWS target environment for the platform: network
isolation, EKS compute, image registry, private PostgreSQL persistence, and the
outputs operators need to deploy services.

## ADDED Requirements

### Requirement: Network isolation

The Terraform configuration SHALL create a VPC with DNS support, two public
subnets, two private subnets in distinct availability zones, an internet
gateway, a NAT gateway, and the route tables needed to reach them.

#### Scenario: Subnets span two availability zones

- **WHEN** the configuration is applied
- **THEN** the VPC contains two public and two private subnets in two distinct
  availability zones

#### Scenario: Private workloads use the NAT gateway

- **WHEN** an EKS node or RDS instance is placed in a private subnet
- **THEN** its route table sends internet-bound traffic through the NAT gateway
  and it has no public IP address

### Requirement: Managed EKS cluster

The configuration SHALL create an EKS cluster with a managed control plane, a
configurable Kubernetes version, cluster logging, and a managed node group in
the private subnets.

#### Scenario: Nodes join the cluster

- **WHEN** the configuration is applied with the default desired capacity
- **THEN** the managed node group reaches the requested size and its nodes join
  the EKS cluster

#### Scenario: Scaling bounds are enforced

- **WHEN** an operator sets the minimum, desired, and maximum node counts
- **THEN** the node group uses those bounds and rejects a desired count outside
  them

### Requirement: Node AWS permissions

Worker nodes SHALL use an IAM role that grants EKS worker, VPC CNI, and ECR read
permissions, so nodes can join the cluster and pull private images.

#### Scenario: Nodes pull the application image

- **WHEN** a pod references an image in the provisioned ECR repository
- **THEN** the node can authenticate to ECR and pull the image

### Requirement: Application image registry

The configuration SHALL create an ECR repository for the `withdrawal-soles`
image with scan-on-push enabled, immutable tags, and encryption at rest.

#### Scenario: Image push is scanned and immutable

- **WHEN** an operator pushes a tagged image
- **THEN** ECR scans the image and rejects a later push that reuses the tag

#### Scenario: Repository URL is available

- **WHEN** the configuration is applied
- **THEN** an output exposes the repository URL for CI image publishing

### Requirement: Private PostgreSQL database

The configuration SHALL create an RDS PostgreSQL 15 instance in the private
subnets with encrypted storage, automated backups, no public accessibility, and
port 5432 reachable only from the EKS node security group. The password MUST be
supplied through a sensitive variable and MUST NOT be committed.

#### Scenario: Database is not publicly reachable

- **WHEN** the database is provisioned
- **THEN** its endpoint is private and connections from outside the VPC are
  refused

#### Scenario: EKS nodes reach the database

- **WHEN** a pod on an EKS node connects to the RDS endpoint on port 5432
- **THEN** the database security group allows the connection

#### Scenario: Missing password blocks the plan

- **WHEN** the database password variable is not supplied
- **THEN** Terraform stops before creating any resource

### Requirement: Deployment outputs

The configuration SHALL output the VPC identifier, EKS cluster name and
endpoint, certificate authority data, ECR repository URL, RDS endpoint, and
database name. Secret values MUST be marked sensitive and MUST NOT be emitted as
plain outputs.

#### Scenario: Operator reads deployment outputs

- **WHEN** the configuration is applied
- **THEN** the outputs expose the values needed to configure kubectl and the
  service database connection without exposing the database password

### Requirement: Reproducible static verification

The configuration SHALL pin its Terraform and provider versions, ship a
`terraform.tfvars.example` without secrets, apply project tags to taggable
resources, and pass formatting, initialization, and validation checks without
AWS credentials.

#### Scenario: Static checks pass

- **WHEN** an operator runs `terraform fmt -check -recursive`,
  `terraform init -backend=false`, and `terraform validate` in
  `infra/terraform`
- **THEN** every command exits successfully

#### Scenario: Plan renders the target resources

- **WHEN** an operator with AWS credentials runs `terraform plan`
- **THEN** the plan includes the VPC, EKS cluster, managed node group, ECR
  repository, and RDS instance

#### Scenario: Tags identify ownership

- **WHEN** taggable resources are created
- **THEN** they carry the project, environment, service, and management tags
