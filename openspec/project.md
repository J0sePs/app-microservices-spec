# Project Context

## Purpose
Sistema bancario basado en microservicios para gestionar operaciones de clientes en dos monedas (PEN y USD). El sistema completo contempla cuatro dominios: `user`, `deposit`, `withdrawal` y `transaction`. Las operaciones de depósito y retiro están segmentadas por moneda, resultando en microservicios independientes por combinación dominio-moneda.

Este repositorio corresponde exclusivamente al microservicio **`withdrawal-soles`**, encargado del procesamiento de retiros en soles peruanos (PEN).

## Microservices Inventory
| Service | Responsibility | Owned DB |
| --- | --- | --- |
| `user-service` | Gestión de clientes y cuentas | `user_db` |
| `deposit-soles` | Depósitos en PEN | `deposit_soles_db` |
| `deposit-dollars` | Depósitos en USD | `deposit_dollars_db` |
| `withdrawal-soles` (THIS REPO) | Retiros en PEN | `withdrawal_soles_db` |
| `withdrawal-dollars` | Retiros en USD | `withdrawal_dollars_db` |
| `transaction-service` | Historial transaccional unificado | `transaction_db` |

## Tech Stack
- Lenguaje: Python 3.11+
- Framework web: FastAPI
- Persistencia: PostgreSQL 15 + SQLAlchemy 2.0 async + Alembic
- Contenedores: Docker + Docker Compose
- API Gateway: Traefik v3
- Testing: pytest + httpx
- CI/CD: GitHub Actions

## Project Conventions
### Architecture Patterns
- Arquitectura hexagonal: `api/`, `application/`, `domain/`, `infrastructure/`, `core/`.
- Database per service: ningún microservicio accede a la DB de otro.
- Comunicación entre servicios: siempre HTTP vía API Gateway.
- Idempotencia obligatoria en operaciones mutativas (`Idempotency-Key` header).
- Autenticación delegada al API Gateway (JWT); el servicio recibe `X-User-Id`.

### Git Workflow
- Rama principal: `main` protegida con PR obligatorio y 1 aprobación.
- Ramas: `feature/<nombre>`, `spec/<nombre>`, `docs/<nombre>`, `chore/<nombre>`.
- Conventional Commits.

## Domain Rules (withdrawal-soles)
- Solo se procesan retiros en moneda `PEN`.
- Monto mínimo por operación: `S/ 10.00`.
- Monto máximo por operación: `S/ 5,000.00`.
- Límite acumulado diario por cuenta: `S/ 10,000.00`.
- Estados posibles: `PENDING | APPROVED | REJECTED | COMPLETED | FAILED`.
- Toda operación aprobada se reporta a `transaction-service` vía HTTP.

## External Dependencies
- PostgreSQL 15 dedicado.
- `user-service` (HTTP) para validar titularidad de cuenta.
- `transaction-service` (HTTP) para registrar la operación.
- API Gateway Traefik como punto único de entrada.

## Documentation Requirements
- La arquitectura DEBE estar documentada con un diagrama mermaid del sistema completo.
- Cada microservicio DEBE tener un ERD mermaid con sus tablas, claves y restricciones.
- Los diagramas viven en `openspec/architecture/` como fuente de verdad para humanos y agentes.