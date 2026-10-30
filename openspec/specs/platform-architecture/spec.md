# platform-architecture Specification

## Purpose
Defines the platform's service catalog, domain boundaries, required diagrams,
and deployment topology so every service is designed against one architecture.

## Requirements

### Requirement: Service catalog covers every platform service

The platform SHALL document exactly six services: `user-service`,
`deposit-soles`, `deposit-dollars`, `withdrawal-soles`, `withdrawal-dollars`,
and `transaction-service`. Each entry MUST state its responsibility, owned
database, and public API surface.

#### Scenario: Catalog is complete

- **WHEN** a contributor reads the service catalog
- **THEN** all six services are listed with responsibility, owned database, and API surface

#### Scenario: Ownership is unambiguous

- **WHEN** a service's database ownership is checked
- **THEN** exactly one service owns each database and no database is shared

### Requirement: Service boundaries align domain and currency

Each service SHALL implement one domain-currency slice. `withdrawal-soles` MUST
process only PEN withdrawals, `withdrawal-dollars` only USD withdrawals, and the
deposit services MUST follow the same split. `user-service` and
`transaction-service` remain cross-currency shared services.

#### Scenario: Currency isolation

- **WHEN** a PEN withdrawal request reaches `withdrawal-dollars`
- **THEN** the request is rejected and no USD operation is created

#### Scenario: Domain isolation

- **WHEN** a withdrawal service receives a deposit command
- **THEN** the command is not processed by that service

### Requirement: System context diagram is authoritative

The repository SHALL contain a mermaid system-context diagram at
`openspec/architecture/system-context.md` showing clients, Traefik, all six
services, and every owned database, including the direction of synchronous
calls.

#### Scenario: End-to-end path is traceable

- **WHEN** a contributor follows a withdrawal request in the diagram
- **THEN** the path shows client, Traefik, `withdrawal-soles`, its database, `user-service`, and `transaction-service`

#### Scenario: Diagram matches the catalog

- **WHEN** the diagram is compared with the service catalog
- **THEN** every cataloged service and database appears exactly once

### Requirement: Every service has an ERD

Each microservice SHALL have one mermaid `erDiagram` at
`openspec/architecture/erd/<service>.md` describing its tables, primary keys,
foreign keys, and constraints. The architecture index MUST link every ERD.

#### Scenario: ERD coverage

- **WHEN** the ERD directory is listed
- **THEN** six ERD files exist, one per cataloged service

#### Scenario: ERD has keys and constraints

- **WHEN** a service ERD is reviewed
- **THEN** it declares primary keys, relationships, and at least one uniqueness or check constraint

### Requirement: Architecture index is the entry point

`openspec/architecture/README.md` SHALL link the project context, service
catalog, system-context diagram, every ERD, and the integration contract.

#### Scenario: New contributor navigates the architecture

- **WHEN** a contributor opens the architecture index
- **THEN** every architecture document is reachable through a relative link

### Requirement: Deployment topology is documented

The architecture SHALL document Docker Compose as the local topology and AWS
EKS with Traefik as the target cluster topology, and MUST identify PostgreSQL as
an external dependency of each service.

#### Scenario: Operator identifies an environment

- **WHEN** an operator reads the deployment section
- **THEN** local and AWS target environments, their entry points, and their database dependencies are distinguishable
