# Tasks

## 1. Inbound authentication

- [x] 1.1 Add inbound JWT settings (secret, issuer, algorithms, allowed subjects) and verify `Settings` loads the documented defaults.
- [x] 1.2 Add the token verifier and the router-level dependency; verify missing, malformed, expired, wrong-issuer, and wrong-subject tokens return `401 UNAUTHORIZED`.
- [x] 1.3 Keep `X-User-Id` as the user identity and return `401` when it is absent even with a valid token; verify the health, docs, and root routes stay public.

## 2. Users-service contract

- [x] 2.1 Add `UserIdentity`, `UserNotFound`, `UserInactive`, and `UserServicePort.get_user`; verify the domain imports without FastAPI or SQLAlchemy.
- [x] 2.2 Implement `GET /usuarios/{idUsuario}` with the `billetera-service` JWT, `idUsuario`/`id_usuario`, `estado is true`, and the `404`/`422`/`503` mapping; verify adapter tests for success, mismatch, inactive, timeout, and `5xx`.
- [x] 2.3 Validate the wallet owner before a debit and before a reversal; verify a failing users call creates no withdrawal and no wallet movement.

## 3. Local contract and tooling

- [x] 3.1 Add the users stub and JWT verification to `tools/mock_dependencies.py`; verify the compose gateway routes `/usuarios` to the mock.
- [x] 3.2 Extend `scripts/simulate_wallet_integration.py` with the service token, the users cases, and a wallet history read; verify simulator mode passes.
- [x] 3.3 Add `scripts/wallet_contract_check.py` for a running service and verify it passes against the simulator stack.

## 4. Contract and documentation

- [x] 4.1 Regenerate `openapi.yaml` with the bearer scheme and updated descriptions; verify `make openapi`.
- [x] 4.2 Update the integration documents, service reference, README, `.env.example`, and settings docs with the JWT and users contract.
- [x] 4.3 Run `make verify`, `openspec validate --all --strict`, and `./init.sh`; record evidence in `feature_list.json`, `progress.md`, and `session-handoff.md`.

## Workflow follow-up

- Archive the change after review and update `openspec/specs/` through the archive command.
