# Retiros en soles — contrato de integración de `withdrawal-soles`

Este documento es lo que necesita el cliente para crear retiros en soles y lo
que necesitan los equipos de usuarios y transacciones para integrarse.

El cliente llama a **retiros**. Retiros llama a **usuarios** para validar la
cuenta y a **transacciones** para registrar el movimiento. Retiros **no llama a
la billetera** y **no descuenta saldos**; solo registra y aprueba la operación de
retiro.

## Dirección

| Dato | Valor |
| --- | --- |
| Base de práctica | `http://aa56b06084cae4b828ba4a1f30f3ceb6-2084714021.us-east-1.elb.amazonaws.com` |
| Base local | `http://localhost:8080` |
| Salud | `GET /health` |
| Documentación | `/docs` |
| OpenAPI | `/openapi.json` y [`openapi.yaml`](openapi.yaml) |
| Región AWS | `us-east-1` |
| Cluster | `app-nube-2-dev-eks` |
| Node group | `app-nube-2-dev-nodes` |
| Base de datos | PostgreSQL 15 privada, `withdrawal_soles_db` |
| Moneda | `PEN` |

La URL pública es un LoadBalancer de práctica y puede cambiar. El gateway de
práctica usa HTTP; no hay TLS configurado. Para obtener la actual:

```bash
terraform -chdir=infra/platform output -raw gateway_url
```

Ejemplos con la URL actual:

```text
http://aa56b06084cae4b828ba4a1f30f3ceb6-2084714021.us-east-1.elb.amazonaws.com/health
http://aa56b06084cae4b828ba4a1f30f3ceb6-2084714021.us-east-1.elb.amazonaws.com/docs
```

## Formato de montos

| Regla | Valor |
| --- | --- |
| Moneda | Solo `PEN` |
| Formato | String decimal con hasta dos decimales, por ejemplo `"250.00"` |
| Mínimo por operación | `10.00` |
| Máximo por operación | `5000.00` |
| Límite diario por cuenta | `10000.00` |
| Zona horaria del límite | `America/Lima` |

No uses céntimos enteros en este servicio. `1500` no significa S/ 15.00; el
contrato espera `"1500.00"`. Para evitar problemas de coma flotante, envía el
monto como string.

## Identidad y encabezados

Todas las rutas de negocio llevan:

```http
X-User-Id: <uuid-del-usuario>
Content-Type: application/json
```

Las operaciones mutativas llevan además:

```http
Idempotency-Key: <uuid-único-por-intento>
```

`X-User-Id` debe ser un UUID. Si falta o no es válido, el servicio responde
`401 UNAUTHORIZED`.

En el despliegue actual el gateway **no valida JWT**; el servicio confía en el
header `X-User-Id`. Para producción, el gateway debe validar el JWT y generar
ese header. No uses el endpoint público de práctica con datos reales.

### Idempotencia

- Una `Idempotency-Key` por operación.
- Si repites la misma clave con el mismo cuerpo, devuelve la operación original
  con `200` y no crea otra.
- Si repites la clave con otro cuerpo, devuelve `409 IDEMPOTENCY_CONFLICT`.
- Si la misma clave está en curso, devuelve `409 IDEMPOTENCY_IN_PROGRESS`.
- Usa un UUID nuevo por cada intento de negocio, no por cada reintento técnico.

## Flujo

1. El cliente conoce `account_id` y el `user_id` autenticado.
2. Llama a `POST /api/v1/withdrawals` con el monto.
3. Retiros valida la cuenta contra `user-service`:
   - debe existir;
   - debe pertenecer al usuario;
   - debe estar en `PEN`;
   - debe estar `ACTIVE`.
4. Retiros verifica el límite diario acumulado de la cuenta.
5. Crea la operación, la aprueba y la reporta a `transaction-service`.
6. Responde:
   - `COMPLETED` si el reporte transaccional funcionó;
   - `APPROVED` si el retiro quedó aprobado pero el reporte falló. En ese caso
     se puede reintentar con `POST /{id}/report`.

Retiros **no descuenta el saldo de una billetera**. Si el caso de negocio
requiere descontar saldo, esa llamada pertenece a otro contrato/servicio.

## Endpoints

### 1. Crear un retiro

```http
POST /api/v1/withdrawals
X-User-Id: 9d1e2f3a-4b5c-6d7e-8f90-1a2b3c4d5e6f
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
  "account_id": "1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11",
  "amount": "250.00"
}
```

Respuesta `201` para una operación nueva:

```json
{
  "id": "14544b68-9c70-4365-bd40-6ba0824bba15",
  "account_id": "1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11",
  "amount": "250.00",
  "currency": "PEN",
  "status": "COMPLETED",
  "transaction_id": "aa3e255f-40b0-4054-80ee-0e637cb30060",
  "created_at": "2026-10-30T17:56:55.809071Z",
  "updated_at": "2026-10-30T17:56:55.824911Z"
}
```

Si el reporte a transacciones falla, la respuesta sigue siendo `201` pero con:

```json
{
  "status": "APPROVED",
  "transaction_id": null
}
```

Un replay con la misma `Idempotency-Key` y el mismo cuerpo responde `200` con
la misma operación.

Ejemplo con curl:

```bash
curl -sS -X POST "http://aa56b06084cae4b828ba4a1f30f3ceb6-2084714021.us-east-1.elb.amazonaws.com/api/v1/withdrawals" \
  -H "X-User-Id: 9d1e2f3a-4b5c-6d7e-8f90-1a2b3c4d5e6f" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{"account_id":"1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11","amount":"250.00"}'
```

### 2. Listar retiros

```http
GET /api/v1/withdrawals?account_id=<uuid>&status=COMPLETED&limit=20&offset=0
X-User-Id: <uuid>
```

Parámetros opcionales:

| Parámetro | Regla |
| --- | --- |
| `account_id` | UUID de la cuenta |
| `status` | `PENDING`, `APPROVED`, `REJECTED`, `COMPLETED` o `FAILED` |
| `limit` | Entero entre 1 y 100; por defecto 20 |
| `offset` | Entero mayor o igual a 0; por defecto 0 |

Respuesta `200`:

```json
{
  "items": [
    {
      "id": "14544b68-9c70-4365-bd40-6ba0824bba15",
      "account_id": "1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11",
      "amount": "250.00",
      "currency": "PEN",
      "status": "COMPLETED",
      "transaction_id": "aa3e255f-40b0-4054-80ee-0e637cb30060",
      "created_at": "2026-10-30T17:56:55.809071Z",
      "updated_at": "2026-10-30T17:56:55.824911Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

Solo se devuelven operaciones del `X-User-Id` que consulta.

### 3. Consultar un retiro

```http
GET /api/v1/withdrawals/{withdrawal_id}
X-User-Id: <uuid>
```

Respuesta `200` con el mismo objeto de retiro. Si no existe o no pertenece al
usuario, responde `404 WITHDRAWAL_NOT_FOUND`.

### 4. Cancelar un retiro

```http
POST /api/v1/withdrawals/{withdrawal_id}/cancel
X-User-Id: <uuid>
Idempotency-Key: <uuid>
```

Solo se puede cancelar una operación en `PENDING`. Si ya está `REJECTED`,
responde `200` con la operación ya rechazada. Para cualquier otro estado responde
`409 INVALID_STATE`.

En el flujo actual una creación válida pasa inmediatamente a `APPROVED` o
`COMPLETED`, así que la cancelación exitosa aplica a operaciones pendientes
creadas por un flujo futuro o manual.

### 5. Reintentar el reporte

```http
POST /api/v1/withdrawals/{withdrawal_id}/report
X-User-Id: <uuid>
Idempotency-Key: <uuid>
```

- `200`: la operación quedó `COMPLETED`.
- `202`: el reporte sigue fallando y la operación permanece `APPROVED`.
- `409 INVALID_STATE`: la operación no está en `APPROVED` ni `COMPLETED`.

Es útil cuando la creación respondió `APPROVED` con `transaction_id: null`.

### 6. Salud

```http
GET /health
```

- `200 {"status":"ok"}`: base de datos accesible.
- `503 {"status":"unavailable"}`: base de datos no accesible.

## Errores

Todas las rutas devuelven el mismo envelope:

```json
{
  "code": "DAILY_LIMIT_EXCEEDED",
  "message": "The daily withdrawal limit was exceeded.",
  "details": {
    "accumulated": "9900.00",
    "requested": "200.00",
    "limit": "10000.00"
  }
}
```

| Código HTTP | `code` | Cuándo |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | Falta `X-User-Id` o no es un UUID válido |
| 403 | `ACCOUNT_NOT_OWNED` | La cuenta no pertenece al usuario |
| 404 | `ACCOUNT_NOT_FOUND` | `user-service` no encontró la cuenta |
| 404 | `WITHDRAWAL_NOT_FOUND` | El retiro no existe o no pertenece al usuario |
| 409 | `IDEMPOTENCY_CONFLICT` | La misma clave se usó con otro cuerpo |
| 409 | `IDEMPOTENCY_IN_PROGRESS` | La misma clave sigue en proceso |
| 409 | `INVALID_STATE` | Transición no permitida, por ejemplo cancelar un `COMPLETED` |
| 422 | `MISSING_IDEMPOTENCY_KEY` | Falta `Idempotency-Key` en una mutación |
| 422 | `INVALID_AMOUNT` | Monto fuera de rango o con más de dos decimales |
| 422 | `DAILY_LIMIT_EXCEEDED` | Se supera el límite diario de la cuenta |
| 422 | `ACCOUNT_NOT_ELIGIBLE` | Cuenta inactiva o moneda distinta de `PEN` |
| 422 | `VALIDATION_ERROR` | Cuerpo o parámetros no cumplen el contrato |
| 503 | `DEPENDENCY_UNAVAILABLE` | `user-service` no respondió; el saldo/registro no cambió |
| 500 | `INTERNAL_ERROR` | Error inesperado del servicio |

Cuando `user-service` no responde, se puede reintentar con la misma
`Idempotency-Key`; la operación no se duplica.

## Dependencias que consume retiros

Estos son los contratos que `withdrawal-soles` llama. Si cada equipo despliega
su microservicio, deben respetar estas rutas y payloads.

### `user-service`

```http
GET /api/v1/accounts/{account_id}/ownership
X-User-Id: <uuid>
```

Respuesta `200`:

```json
{
  "account_id": "1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11",
  "owner_user_id": "9d1e2f3a-4b5c-6d7e-8f90-1a2b3c4d5e6f",
  "currency": "PEN",
  "status": "ACTIVE",
  "owned": true
}
```

Retiros usa `owned`, `currency` y `status` para decidir si puede continuar.
`404` se traduce a `ACCOUNT_NOT_FOUND`; `403` a `ACCOUNT_NOT_OWNED`;
`currency != PEN` o `status != ACTIVE` a `ACCOUNT_NOT_ELIGIBLE`.

### `transaction-service`

```http
POST /api/v1/transactions
X-User-Id: <uuid>
Idempotency-Key: <withdrawal-id>
Content-Type: application/json
```

Payload:

```json
{
  "source_service": "withdrawal-soles",
  "source_operation_id": "14544b68-9c70-4365-bd40-6ba0824bba15",
  "account_id": "1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11",
  "type": "WITHDRAWAL",
  "amount": "250.00",
  "currency": "PEN",
  "status": "POSTED",
  "occurred_at": "2026-10-30T17:56:55.809071Z"
}
```

Respuesta esperada: `201` o `200` con `transaction_id`. Retiros guarda ese
`transaction_id` en la operación y responde `COMPLETED`; si falla, deja la
operación en `APPROVED` para reintentar.

## Qué no hace esta API

- No descuenta saldos de una billetera.
- No administra usuarios ni cuentas; eso pertenece a `user-service`.
- No registra banco, cajero, motivo, comisión ni comprobante.
- No procesa retiros en USD; este servicio es solo `PEN`.
- No valida JWT por sí mismo; confía en `X-User-Id` inyectado por el gateway.
- No permite que otro servicio lea o escriba directamente su base de datos.

## Datos que guarda

- `withdrawal_operations`: operación, cuenta, usuario, monto, moneda, estado,
  `transaction_id` y timestamps.
- `withdrawal_status_history`: auditoría de transiciones.
- `idempotency_records`: clave, hash del request, operación y snapshot.
- `reporting_attempts`: intentos de reporte, estado y error.

El ERD completo está en
[`service-reference.md`](service-reference.md#entity-relationship-diagram) y en
[`openspec/architecture/erd/withdrawal-soles.md`](openspec/architecture/erd/withdrawal-soles.md).

## Acuerdo con la billetera

El acuerdo pendiente para conectar el retiro con la billetera PEN, incluyendo
quién debita, cómo se obtiene `idUsuario` y cómo se convierten los montos a
céntimos, está en
[`ACUERDO-INTEGRACION-BILLETERA.md`](ACUERDO-INTEGRACION-BILLETERA.md).

## Práctica local

```bash
docker compose up -d --build
curl http://localhost:8080/health
curl http://localhost:8080/docs
```

La URL pública de práctica se puede recrear con:

```bash
terraform -chdir=infra/terraform apply
./scripts/deploy-eks-demo.sh
terraform -chdir=infra/platform output -raw gateway_url
```

Para apagarla:

```bash
./scripts/destroy-eks-demo.sh
```
