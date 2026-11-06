# Retiros en soles — contrato de integración de `withdrawal-soles`

Este documento es lo que necesita el cliente para crear retiros en soles y lo
que necesitan los equipos de usuarios y transacciones para integrarse.

El cliente llama a **retiros**. Retiros llama a **usuarios** para validar la
cuenta, a la **billetera PEN** para debitar el saldo, y a **transacciones** para
registrar el movimiento. La billetera es la única dueña del saldo: retiros
solicita el débito antes de aprobar la operación y guarda los identificadores
del movimiento. También puede revertir el débito completo.

## Dirección

| Dato | Valor |
| --- | --- |
| Base de práctica | `http://a6c1a4b5ffa8a44808f8a8a0784fe0d7-266125410.us-east-1.elb.amazonaws.com` |
| Base local | `http://localhost:8080` |
| Billetera PEN | `http://18.228.136.200` |
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
http://a6c1a4b5ffa8a44808f8a8a0784fe0d7-266125410.us-east-1.elb.amazonaws.com/health
http://a6c1a4b5ffa8a44808f8a8a0784fe0d7-266125410.us-east-1.elb.amazonaws.com/docs
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
Authorization: Bearer <jwt>
X-User-Id: <uuid-del-usuario>
Content-Type: application/json
```

El JWT es el token de servicio acordado: HS256, emisor `billetera-dev`, sujeto
`retiros` y secreto `dev-only-change-me` (solo desarrollo). Sin token válido el
servicio responde `401 UNAUTHORIZED`; `X-User-Id` no reemplaza ese token. El
token autentica al llamador y `X-User-Id` identifica al usuario final.

Las operaciones mutativas llevan además:

```http
Idempotency-Key: <uuid-único-por-intento>
```

`X-User-Id` debe ser un UUID. Si falta o no es válido, el servicio responde
`401 UNAUTHORIZED`.

Para generar un token de desarrollo:

```bash
.venv/bin/python -c "from withdrawal_soles.infrastructure.service_jwt import sign_service_token; print(sign_service_token(secret='dev-only-change-me', issuer='billetera-dev', subject='retiros', ttl_seconds=3600))"
```

En producción, inyecta un secreto fuerte por variable de entorno y no publiques
el token de desarrollo.

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
   - debe estar `ACTIVE`;
   - debe incluir el entero `id_usuario` de la billetera.
4. Retiros verifica el límite diario acumulado de la cuenta.
5. Retiros confirma con `GET /usuarios/{idUsuario}` que el usuario existe y
   tiene `estado: true`.
6. Retiros consulta la billetera por `idUsuario` y debita el monto exacto en
   céntimos con `externalReference` igual al UUID del retiro.
7. Persiste la operación con `wallet_id`, `wallet_movement_id` y timestamps.
8. Reporta la operación a `transaction-service` y responde:
   - `COMPLETED` si el reporte transaccional funcionó;
   - `APPROVED` si el retiro quedó aprobado pero el reporte falló. En ese caso
     se puede reintentar con `POST /{id}/report`.

Si usuarios o la billetera rechazan la operación, no se crea ningún retiro. Un
fallo de reporte posterior no revierte el débito: la operación queda `APPROVED`
y se puede reintentar el reporte.

## Endpoints

### 1. Crear un retiro

```http
POST /api/v1/withdrawals
Authorization: Bearer <jwt>
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
  "wallet_id": "a212968a-21d1-40f1-a47d-5f87c5b36a84",
  "wallet_movement_id": "5d0916cc-5cd9-4fdc-9671-79a79050e6e9",
  "wallet_reversal_movement_id": null,
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
TOKEN=$(.venv/bin/python -c "from withdrawal_soles.infrastructure.service_jwt import sign_service_token; print(sign_service_token(secret='dev-only-change-me', issuer='billetera-dev', subject='retiros', ttl_seconds=3600))")

curl -sS -X POST "http://a6c1a4b5ffa8a44808f8a8a0784fe0d7-266125410.us-east-1.elb.amazonaws.com/api/v1/withdrawals" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-User-Id: 9d1e2f3a-4b5c-6d7e-8f90-1a2b3c4d5e6f" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{"account_id":"1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11","amount":"250.00"}'
```

### 2. Listar retiros

```http
GET /api/v1/withdrawals?account_id=<uuid>&status=COMPLETED&limit=20&offset=0
Authorization: Bearer <jwt>
X-User-Id: <uuid>
```

Parámetros opcionales:

| Parámetro | Regla |
| --- | --- |
| `account_id` | UUID de la cuenta |
| `status` | `PENDING`, `APPROVED`, `REJECTED`, `COMPLETED`, `REVERSED` o `FAILED` |
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
Authorization: Bearer <jwt>
X-User-Id: <uuid>
```

Respuesta `200` con el mismo objeto de retiro. Si no existe o no pertenece al
usuario, responde `404 WITHDRAWAL_NOT_FOUND`.

### 4. Cancelar un retiro

```http
POST /api/v1/withdrawals/{withdrawal_id}/cancel
Authorization: Bearer <jwt>
X-User-Id: <uuid>
Idempotency-Key: <uuid>
```

Solo se puede cancelar una operación en `PENDING`. Si ya está `REJECTED`,
responde `200` con la operación ya rechazada. Para cualquier otro estado responde
`409 INVALID_STATE`.

En el flujo actual una creación válida pasa inmediatamente a `APPROVED` o
`COMPLETED`, así que la cancelación exitosa aplica a operaciones pendientes
creadas por un flujo futuro o manual.

### 5. Revertir un retiro

```http
POST /api/v1/withdrawals/{withdrawal_id}/reverse
Authorization: Bearer <jwt>
X-User-Id: <uuid>
Idempotency-Key: <uuid>
Content-Type: application/json

{
  "reason": "Reversión solicitada por operaciones"
}
```

Revierte el débito completo en la billetera mediante un movimiento
compensatorio y marca la operación como `REVERSED`. Solo aplica a operaciones
`APPROVED` o `COMPLETED` que tengan `wallet_movement_id`.

- `200`: la billetera acreditó el monto y la operación quedó `REVERSED`.
- `409 INVALID_STATE`: la operación no tiene débito de billetera.
- `422 WALLET_ALREADY_REVERSED`: la operación ya fue revertida.
- `503 DEPENDENCY_UNAVAILABLE`: la billetera no respondió; se puede reintentar.

### 6. Reintentar el reporte

```http
POST /api/v1/withdrawals/{withdrawal_id}/report
Authorization: Bearer <jwt>
X-User-Id: <uuid>
Idempotency-Key: <uuid>
```

- `200`: la operación quedó `COMPLETED`.
- `202`: el reporte sigue fallando y la operación permanece `APPROVED`.
- `409 INVALID_STATE`: la operación no está en `APPROVED` ni `COMPLETED`.

Es útil cuando la creación respondió `APPROVED` con `transaction_id: null`.

### 7. Salud

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
| 401 | `UNAUTHORIZED` | Falta el JWT, es inválido, o falta `X-User-Id` |
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
| 422 | `INSUFFICIENT_BALANCE` | La billetera no tiene saldo suficiente |
| 422 | `USER_INACTIVE` | El usuario de la billetera está inactivo |
| 422 | `WALLET_ALREADY_REVERSED` | El retiro ya fue revertido |
| 422 | `VALIDATION_ERROR` | Cuerpo o parámetros no cumplen el contrato |
| 404 | `USER_NOT_FOUND` | Usuarios no encontró el `idUsuario` |
| 404 | `WALLET_NOT_FOUND` | El usuario no tiene billetera |
| 409 | `WALLET_CONFLICT` | Conflicto de idempotencia o estado en la billetera |
| 503 | `DEPENDENCY_UNAVAILABLE` | `user-service`, la billetera o `transaction-service` no respondió |
| 503 | `WALLET_AUTH_FAILED` | La billetera rechazó el token de servicio |
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
  "id_usuario": 15,
  "currency": "PEN",
  "status": "ACTIVE",
  "owned": true
}
```

Retiros usa `owned`, `currency` y `status` para decidir si puede continuar.
`404` se traduce a `ACCOUNT_NOT_FOUND`; `403` a `ACCOUNT_NOT_OWNED`;
`currency != PEN` o `status != ACTIVE` a `ACCOUNT_NOT_ELIGIBLE`. Sin
`id_usuario` no se llama a la billetera y se responde `503
DEPENDENCY_UNAVAILABLE`.

#### Estado del usuario para la billetera

Antes de debitar o reversar, retiros llama el mismo contrato que la billetera:

```http
GET {USERS_SERVICE_URL}/usuarios/{idUsuario}
Authorization: Bearer <jwt sub=billetera-service>
Accept: application/json
```

Respuesta mínima:

```json
{ "idUsuario": 15, "estado": true }
```

También se acepta `id_usuario` en lugar de `idUsuario`. El id del cuerpo debe
coincidir con el de la ruta y `estado` debe ser el booleano `true`.

| Respuesta de usuarios | Respuesta de retiros |
| --- | --- |
| `200` y `estado: true` | Continúa con la billetera |
| `404` o el id no coincide | `404 USER_NOT_FOUND`; no hay movimiento |
| `200` y `estado` distinto de `true` | `422 USER_INACTIVE`; no hay movimiento |
| Timeout de 2 segundos o cualquier otro estado | `503 DEPENDENCY_UNAVAILABLE`; no hay movimiento |

`WITHDRAWAL_SOLES_USERS_SERVICE_URL` es opcional y, si está vacía, usa la misma
base que `WITHDRAWAL_SOLES_USER_SERVICE_URL`. En el stack local el mock responde
`/usuarios/{idUsuario}` con los usuarios 15, 16 y 18 activos y el 17 inactivo.

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

### `wallet` (billetera PEN)

La billetera es la dueña del saldo y se llama directamente con un JWT HS256
(issuer `billetera-dev`, subject `retiros`, TTL de 60 segundos). El contrato
completo está en [`openapi-billetera.yaml`](openapi-billetera.yaml) y en
[`openspec/architecture/integration-contract.md`](openspec/architecture/integration-contract.md).

```http
GET /v1/wallets?idUsuario=15
Authorization: Bearer <jwt>
```

```http
POST /v1/wallets/{wallet_id}/payments
Authorization: Bearer <jwt>
Idempotency-Key: <withdrawal_id>

{
  "amount": 25000,
  "currency": "PEN",
  "externalReference": "<withdrawal_id>",
  "description": "PEN withdrawal"
}
```

```http
POST /v1/movements/{movement_id}/reverse
Authorization: Bearer <jwt>
Idempotency-Key: <withdrawal_id>:reverse
```

`amount` viaja en céntimos enteros: `S/ 250.00` se envía como `25000`. Retiros
guarda el `wallet_id` y el id del movimiento de débito; la reversión guarda el
id del movimiento compensatorio.

## Qué no hace esta API

- No administra usuarios ni cuentas; eso pertenece a `user-service`.
- No implementa la billetera: solo consume su contrato de débito y reversión.
- No registra banco, cajero, motivo, comisión ni comprobante.
- No procesa retiros en USD; este servicio es solo `PEN`.
- No emite tokens de usuario: exige el JWT de servicio acordado y toma la
  identidad final de `X-User-Id`.
- No permite que otro servicio lea o escriba directamente su base de datos.

## Datos que guarda

- `withdrawal_operations`: operación, cuenta, usuario, `wallet_user_id`,
  `wallet_id`, `wallet_movement_id`, `wallet_reversal_movement_id`, monto,
  moneda, estado, `transaction_id` y timestamps de débito/reversión.
- `withdrawal_status_history`: auditoría de transiciones.
- `idempotency_records`: clave, hash del request, operación y snapshot.
- `reporting_attempts`: intentos de reporte, estado y error.

El ERD completo está en
[`service-reference.md`](service-reference.md#entity-relationship-diagram) y en
[`openspec/architecture/erd/withdrawal-soles.md`](openspec/architecture/erd/withdrawal-soles.md).

## Acuerdo con la billetera

El acuerdo de integración con la billetera PEN está implementado en esta
versión: retiros resuelve `id_usuario` desde `user-service`, debita la billetera
en céntimos y permite revertir el débito completo. El detalle histórico está en
[`ACUERDO-INTEGRACION-BILLETERA.md`](ACUERDO-INTEGRACION-BILLETERA.md).

## Práctica local

El simulador local de dependencias expone las mismas rutas de billetera y
verifica el mismo JWT. Las billeteras sembradas son usuario 15 = `S/ 250.00`,
usuario 16 = `S/ 15.00`, y usuario 18 = `S/ 5,000.00`; el usuario 17 no tiene
billetera y está inactivo.

```bash
docker compose up -d --build
curl http://localhost:8080/health
curl http://localhost:8080/docs
.venv/bin/python scripts/simulate_wallet_integration.py --mode simulate
.venv/bin/python scripts/wallet_contract_check.py --base-url http://localhost:8080 --wallet-url http://localhost:8080
```

`wallet_contract_check.py` es la herramienta pensada para el compañero: solo usa
HTTP, comprueba el `401` sin token, crea y revierte un retiro, y verifica el
saldo si se pasa `--wallet-url`. Es seguro repetirla porque siempre revierte.

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
