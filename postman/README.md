# Colección Postman — withdrawal-soles + Billetera PEN

Una sola colección para probar los dos microservicios:

| Carpeta | Servicio | Base URL |
| --- | --- | --- |
| `1. withdrawal-soles (mio)` | Retiros en soles | `{{withdrawal_base_url}}` |
| `2. Billetera PEN (amigo)` | Billetera Digital PEN v1.1.0 | `{{wallet_base_url}}` |
| `3. Flujo integrado (ambos servicios)` | Ambos, en cadena | ambas |

Archivo:

```text
postman/withdrawal-soles-billetera.postman_collection.json
```

## Importar

1. Abre Postman.
2. `File → Import` y selecciona el archivo.
3. Revisa la pestaña **Variables** de la colección.
4. Ejecuta los requests en orden o corre toda la colección con el Runner.

## Variables

| Variable | Valor por defecto | Uso |
| --- | --- | --- |
| `withdrawal_base_url` | `http://localhost:8080` | Gateway local de withdrawal-soles |
| `wallet_base_url` | `http://52.67.162.209` | Billetera publicada de tu amigo |
| `jwt_secret` | `dev-only-change-me` | Firma HS256 (solo desarrollo) |
| `jwt_issuer` | `billetera-dev` | Emisor esperado por ambos servicios |
| `jwt_subject` | `retiros` | `sub` del token de servicio |
| `jwt_ttl_seconds` | `3600` | Vigencia del token |
| `user_id` | UUID de ejemplo | Header `X-User-Id` de withdrawal-soles |
| `account_id` | UUID de ejemplo | Cuenta del retiro |
| `wallet_user_id` | `15` | `idUsuario` de la billetera |
| `wallet_id` | vacío | Se llena solo al consultar/crear la billetera |
| `target_wallet_id` | wallet de ejemplo | Destino de la transferencia |
| `withdrawal_id` | vacío | Se llena solo al crear un retiro |
| `movement_id` | vacío | Se llena solo con cobros/recargas/movimientos |
| `withdrawal_amount` | `10.00` | Monto del retiro en soles |
| `wallet_amount_cents` | `1000` | Cobro en centimos (S/ 10.00) |
| `top_up_cents` | `2500` | Recarga en centimos (S/ 25.00) |

## JWT automático

El script de **pre-request** de la colección firma un JWT HS256 con
`jwt_secret`, `jwt_issuer`, `jwt_subject` y `jwt_ttl_seconds`, y lo guarda en
`jwt_token`. No necesitas pegar el token a mano ni instalar librerías: Postman
incluye `crypto-js` en su sandbox.

Si tu servicio usa otro secreto o emisor, cambia esas variables y el token se
regenera en el siguiente request. Para generar uno desde la terminal:

```bash
.venv/bin/python -c "from withdrawal_soles.infrastructure.service_jwt import sign_service_token; print(sign_service_token(secret='dev-only-change-me', issuer='billetera-dev', subject='retiros', ttl_seconds=3600))"
```

## Montos

- **withdrawal-soles** usa soles decimales: `"amount": "10.00"`.
- **Billetera PEN** usa **centimos enteros**: `1000` = S/ 10.00.

## Idempotencia

Los requests de escritura envían `Idempotency-Key: {{$guid}}` para que cada
ejecución sea única. Para probar un replay:

1. Copia el valor de `Idempotency-Key` de una ejecución.
2. Reemplaza `{{$guid}}` por ese valor fijo.
3. Reenvía el mismo cuerpo: debe responder `200` con el recurso original.
4. Cambia solo el cuerpo y reenvía: debe responder `409`.

## Stub local vs API publicada

El stack de Docker Compose incluye un stub del wallet que **solo implementa**:

- `GET /v1/wallets?idUsuario=...`
- `GET /v1/wallets/{walletId}/movements`
- `POST /v1/wallets/{walletId}/payments`
- `POST /v1/movements/{movementId}/reverse`

Por eso, si pones `wallet_base_url = http://localhost:8080`, los requests de
crear billetera, recargar y transferir responderán `404/405`. Es esperado. Usa
`http://52.67.162.209` para probar el contrato completo de tu amigo.

Para que el flujo integrado cuadre, el servicio de retiros debe apuntar a la
misma billetera. En local:

```bash
WITHDRAWAL_SOLES_WALLET_SERVICE_URL=http://52.67.162.209 docker compose up --build
```

o, si usas el stub, deja el valor por defecto `http://traefik`.

## Ejecutar con Newman

```bash
npx newman run postman/withdrawal-soles-billetera.postman_collection.json \
  --env-var "wallet_base_url=http://localhost:8080"
```

Sin `--env-var`, la colección usa la billetera publicada de tu amigo.
