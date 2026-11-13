# Spec Delta

## Purpose

Adds image retention, shared Terraform state, and CI cluster access to the AWS
infrastructure capability.

## MODIFIED Requirements

### Requirement: Application image registry

The configuration SHALL create an ECR repository for the `withdrawal-soles`
image with scan-on-push enabled, encryption at rest, and immutable tags except
for `latest`. A lifecycle policy SHALL expire untagged images one day after push
and keep only the newest configurable number of images.

#### Scenario: Image push is scanned and immutable

- **WHEN** CI pushes an image tagged with a commit SHA
- **THEN** ECR scans the image and rejects a later push that reuses that SHA tag

#### Scenario: Latest tag moves

- **WHEN** CI pushes a new image tagged `latest`
- **THEN** ECR accepts the push and `latest` points at the new digest

#### Scenario: Old images are removed

- **WHEN** the repository holds more images than `ecr_max_image_count`, or an
  untagged image is older than one day
- **THEN** the lifecycle policy expires the surplus and untagged images

#### Scenario: Repository URL is available

- **WHEN** the configuration is applied
- **THEN** outputs expose the repository URL and name for CI image publishing

### Requirement: Deployment outputs

The configuration SHALL output the VPC identifier, EKS cluster name and
endpoint, certificate authority data, ECR repository URL and name, RDS
endpoint, database name, and AWS region. Secret values MUST be marked sensitive
and MUST NOT be emitted as plain outputs.

#### Scenario: Operator reads deployment outputs

- **WHEN** the configuration is applied
- **THEN** the outputs expose the values needed to configure kubectl and the
  service database connection without exposing the database password

## ADDED Requirements

### Requirement: Shared Terraform state

The `infra/terraform` and `infra/platform` roots SHALL store state in an S3
backend with encryption and native lockfiles. A bootstrap script SHALL create the
versioned, encrypted, non-public state bucket, and the destroy script MUST NOT
delete it.

#### Scenario: CI and operator share state

- **WHEN** an operator applies `infra/terraform` locally and CI later applies
  `infra/platform`
- **THEN** both read the same state objects from S3

#### Scenario: Concurrent applies are serialized

- **WHEN** two applies run against the same root at the same time
- **THEN** the second fails to acquire the lock instead of corrupting state

### Requirement: CI cluster access

The configuration SHALL accept a list of IAM principal ARNs and grant each one
cluster administration through an EKS access entry. The list MUST default to
empty.

#### Scenario: Dedicated CI user deploys

- **WHEN** the CI IAM user ARN is listed in `cluster_admin_principal_arns`
- **THEN** the CI job can update the kubeconfig and apply `infra/platform`
