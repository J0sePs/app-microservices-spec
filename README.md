# app-nube-2 — Banking Microservices

Banking platform built as independent microservices for PEN (soles) and USD
(dollars) operations. This repository is the home of the **withdrawal-soles**
service and the system architecture that surrounds it.

## Scope

The full platform covers four domains — `user`, `deposit`, `withdrawal`, and
`transaction` — split by currency into independently deployable services:

| Service | Responsibility | Owned database |
| --- | --- | --- |
| `user-service` | Customer and account management | `user_db` |
| `deposit-soles` | PEN deposits | `deposit_soles_db` |
| `deposit-dollars` | USD deposits | `deposit_dollars_db` |
| `withdrawal-soles` | PEN withdrawals (this repository) | `withdrawal_soles_db` |
| `withdrawal-dollars` | USD withdrawals | `withdrawal_dollars_db` |
| `transaction-service` | Unified transaction history | `transaction_db` |

## Tech stack

- Python 3.11+ with FastAPI
- PostgreSQL 15 with SQLAlchemy 2.0 async and Alembic
- Docker and Docker Compose
- Traefik v3 as the API gateway
- pytest and httpx for testing
- GitHub Actions for CI/CD
- Terraform for AWS infrastructure (EKS cluster)

## Architecture

Architecture documentation lives in `openspec/architecture/` and is the source
of truth for humans and agents. It includes a system-level mermaid diagram and
one ERD per microservice.

## withdrawal-soles service

The only implemented service in this repository is `withdrawal-soles`. See
[docs/withdrawal-soles.md](docs/withdrawal-soles.md) for setup, API examples,
migrations, and Docker Compose instructions. For current URLs, endpoints, and
the ERD, see [service-reference.md](service-reference.md). For the
cross-team integration contract, see
[withdrawal-soles-integration.md](withdrawal-soles-integration.md).

```bash
make install && make verify   # Python service checks
docker compose up --build      # PostgreSQL + Traefik + service + local stubs
```

## AWS infrastructure

The target AWS topology (VPC, EKS cluster, managed node group, ECR repository,
and private RDS PostgreSQL 15) is defined in
[`infra/terraform/`](infra/terraform/README.md). The Kubernetes platform
(Traefik gateway, namespace, Secret, migrations, application, mock, and Ingress)
is defined in [`infra/platform/`](infra/platform/README.md). Static validation
runs without AWS credentials:

```bash
./scripts/verify-terraform.sh
```

A credentialed `terraform plan` is expected before any approved apply. After an
approved apply, `./scripts/deploy-eks-demo.sh` builds and pushes the image and
applies the platform module. Tear it down with `./scripts/destroy-eks-demo.sh`.
This repository does not create AWS resources automatically.

## Spec-driven workflow

This repository uses the OpenSpec + five-subsystem harness. Read `AGENTS.md`
first, then `context.md` for the project brief.

```bash
./init.sh                 # install, validate harness, validate OpenSpec, run checks
openspec list             # active changes
openspec validate --all --strict
```

The workflow is: propose → review → apply → verify → archive. One active change
at a time.
