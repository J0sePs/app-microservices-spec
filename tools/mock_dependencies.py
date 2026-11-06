"""Local-only stubs for user-service, transaction-service, and the PEN wallet.

The real services are separate repositories. These endpoints let the compose
stack exercise the full withdrawal flow without them.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

import jwt
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="mock-dependencies",
    description="Local stubs for user-service, transaction-service, and wallet.",
)

JWT_SECRET = "dev-only-change-me"
JWT_ISSUER = "billetera-dev"
WALLET_SUBJECT = "retiros"
USERS_SUBJECT = "billetera-service"

_transactions: dict[tuple[str, str], dict[str, object]] = {}

SEED_USERS: dict[int, bool] = {
    15: True,
    16: True,
    17: False,
    18: True,
}

SEED_WALLETS: dict[int, dict[str, Any]] = {
    15: {
        "id": "a212968a-21d1-40f1-a47d-5f87c5b36a84",
        "idUsuario": 15,
        "currency": "PEN",
        "balance": 25000,
        "createdAt": "2026-11-06T20:17:50.707Z",
    },
    16: {
        "id": "dadf4b90-cb5f-48ac-8046-5acb3726a7a9",
        "idUsuario": 16,
        "currency": "PEN",
        "balance": 1500,
        "createdAt": "2026-11-06T20:17:51.166Z",
    },
    18: {
        "id": "0b8b5c3f-b373-495f-80ef-555fc824ec8b",
        "idUsuario": 18,
        "currency": "PEN",
        "balance": 500000,
        "createdAt": "2026-11-06T20:17:51.501Z",
    },
}

_wallets: dict[int, dict[str, Any]] = {
    key: dict(value) for key, value in SEED_WALLETS.items()
}
_movements: dict[str, dict[str, Any]] = {}
_idempotency: dict[str, dict[str, Any]] = {}
_external_references: dict[tuple[str, str], str] = {}


class TransactionReport(BaseModel):
    source_service: str
    source_operation_id: str
    account_id: UUID
    type: str
    amount: str
    currency: str
    status: str
    occurred_at: datetime


class PaymentRequest(BaseModel):
    amount: int
    currency: str | None = None
    externalReference: str | None = None


class ReverseRequest(BaseModel):
    reason: str


def _problem(status: int, title: str, detail: str, instance: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": instance,
        },
    )


def _require_token(authorization: str | None, subject: str) -> None:
    """Mirror the wallet's HS256 service-token check."""

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Falta el token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            issuer=JWT_ISSUER,
        )
    except jwt.PyJWTError as error:
        raise HTTPException(status_code=401, detail="Token invalido") from error
    if claims.get("sub") != subject:
        raise HTTPException(status_code=401, detail="Sujeto invalido")


def _body_hash(payload: BaseModel) -> str:
    encoded = json.dumps(payload.model_dump(), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _wallet_by_id(wallet_id: str) -> dict[str, Any] | None:
    for wallet in _wallets.values():
        if wallet["id"] == wallet_id:
            return wallet
    return None


def _movement(
    wallet: dict[str, Any],
    *,
    amount: int,
    direction: str,
    movement_type: str,
    external_reference: str | None,
    reversal_of: str | None = None,
) -> dict[str, Any]:
    value = {
        "id": str(uuid4()),
        "walletId": wallet["id"],
        "amount": amount,
        "currency": "PEN",
        "direction": direction,
        "type": movement_type,
        "counterpartyWalletId": None,
        "externalReference": external_reference,
        "reversalOf": reversal_of,
        "createdAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    _movements[value["id"]] = value
    return value


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/accounts/{account_id}/ownership")
async def ownership(
    account_id: UUID,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    owned: bool = Query(default=True),
    currency: str = Query(default="PEN"),
    status: str = Query(default="ACTIVE"),
    id_usuario: int = Query(default=15),
) -> dict[str, object]:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="missing identity")
    return {
        "account_id": str(account_id),
        "owner_user_id": x_user_id,
        "id_usuario": id_usuario,
        "currency": currency,
        "status": status,
        "owned": owned,
    }


@app.get("/usuarios/{id_usuario}")
async def get_user(
    id_usuario: int,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> Any:
    _require_token(authorization, USERS_SUBJECT)
    if id_usuario not in SEED_USERS:
        return _problem(
            404,
            "No encontrado",
            "El usuario no existe",
            f"/usuarios/{id_usuario}",
        )
    return {"idUsuario": id_usuario, "estado": SEED_USERS[id_usuario]}


@app.post("/api/v1/transactions", status_code=201)
async def report_transaction(
    payload: TransactionReport,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key")
    ] = None,
) -> dict[str, object]:
    if not x_user_id or not idempotency_key:
        raise HTTPException(status_code=401, detail="missing identity")
    key = (payload.source_service, payload.source_operation_id)
    existing = _transactions.get(key)
    if existing is not None:
        return existing

    transaction = {
        "transaction_id": str(uuid4()),
        "source_service": payload.source_service,
        "source_operation_id": payload.source_operation_id,
        "account_id": str(payload.account_id),
        "type": payload.type,
        "amount": payload.amount,
        "currency": payload.currency,
        "status": payload.status,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _transactions[key] = transaction
    return transaction


@app.get("/v1/wallets")
async def get_wallet(
    idUsuario: int = Query(..., ge=1),
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> Any:
    _require_token(authorization, WALLET_SUBJECT)
    wallet = _wallets.get(idUsuario)
    if wallet is None:
        return _problem(
            404,
            "No encontrado",
            "Billetera no encontrada",
            "/v1/wallets",
        )
    return wallet


@app.get("/v1/wallets/{wallet_id}/movements")
async def list_movements(
    wallet_id: str,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> dict[str, object]:
    _require_token(authorization, WALLET_SUBJECT)
    items = [
        movement
        for movement in _movements.values()
        if movement["walletId"] == wallet_id
    ]
    items.sort(key=lambda movement: movement["createdAt"], reverse=True)
    return {"items": items, "nextCursor": None}


@app.post("/v1/wallets/{wallet_id}/payments")
async def create_payment(
    wallet_id: str,
    payload: PaymentRequest,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key")
    ] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> Any:
    _require_token(authorization, WALLET_SUBJECT)
    if not idempotency_key:
        return _problem(
            400, "Solicitud invalida", "El encabezado Idempotency-Key es obligatorio",
            f"/v1/wallets/{wallet_id}/payments",
        )

    wallet = _wallet_by_id(wallet_id)
    if wallet is None:
        return _problem(
            404, "No encontrado", "Billetera no encontrada",
            f"/v1/wallets/{wallet_id}/payments",
        )
    if payload.currency is not None and payload.currency != "PEN":
        return _problem(
            400, "Solicitud invalida", "La moneda debe ser PEN",
            f"/v1/wallets/{wallet_id}/payments",
        )
    if payload.amount < 1:
        return _problem(
            400, "Solicitud invalida", "El monto debe ser mayor que cero",
            f"/v1/wallets/{wallet_id}/payments",
        )

    fingerprint = _body_hash(payload)
    previous = _idempotency.get(idempotency_key)
    if previous is not None:
        if previous["hash"] != fingerprint:
            return _problem(
                409,
                "Conflicto",
                "La clave de idempotencia ya se uso con otro cuerpo",
                f"/v1/wallets/{wallet_id}/payments",
            )
        return previous["response"]

    reference_key = (wallet_id, payload.externalReference or "")
    if reference_key in _external_references:
        return _problem(
            409,
            "Conflicto",
            "La referencia externa ya existe para esta billetera",
            f"/v1/wallets/{wallet_id}/payments",
        )
    if wallet["balance"] < payload.amount:
        return _problem(
            422,
            "Regla de negocio",
            "Saldo insuficiente",
            f"/v1/wallets/{wallet_id}/payments",
        )

    movement = _movement(
        wallet,
        amount=payload.amount,
        direction="DEBIT",
        movement_type="PAYMENT",
        external_reference=payload.externalReference,
    )
    wallet["balance"] -= payload.amount
    if payload.externalReference:
        _external_references[reference_key] = movement["id"]
    _idempotency[idempotency_key] = {
        "hash": fingerprint,
        "response": movement,
    }
    return JSONResponse(status_code=201, content=movement)


@app.post("/v1/movements/{movement_id}/reverse")
async def reverse_movement(
    movement_id: str,
    payload: ReverseRequest,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key")
    ] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> Any:
    _require_token(authorization, WALLET_SUBJECT)
    if not idempotency_key:
        return _problem(
            400, "Solicitud invalida", "El encabezado Idempotency-Key es obligatorio",
            f"/v1/movements/{movement_id}/reverse",
        )
    if not 1 <= len(payload.reason) <= 500:
        return _problem(
            400, "Solicitud invalida", "El motivo debe tener entre 1 y 500 caracteres",
            f"/v1/movements/{movement_id}/reverse",
        )

    fingerprint = _body_hash(payload)
    previous = _idempotency.get(idempotency_key)
    if previous is not None:
        if previous["hash"] != fingerprint:
            return _problem(
                409,
                "Conflicto",
                "La clave de idempotencia ya se uso con otro cuerpo",
                f"/v1/movements/{movement_id}/reverse",
            )
        return previous["response"]

    original = _movements.get(movement_id)
    if original is None:
        return _problem(
            404, "No encontrado", "Movimiento no encontrado",
            f"/v1/movements/{movement_id}/reverse",
        )
    if original.get("reversalOf") or original.get("reversedBy"):
        return _problem(
            422,
            "Regla de negocio",
            "El movimiento ya fue reversado",
            f"/v1/movements/{movement_id}/reverse",
        )

    wallet = _wallet_by_id(original["walletId"])
    if wallet is None:
        return _problem(
            404, "No encontrado", "Billetera no encontrada",
            f"/v1/movements/{movement_id}/reverse",
        )

    reversal = _movement(
        wallet,
        amount=original["amount"],
        direction="CREDIT",
        movement_type="REVERSAL",
        external_reference=None,
        reversal_of=movement_id,
    )
    original["reversedBy"] = reversal["id"]
    wallet["balance"] += original["amount"]
    response = {"movements": [reversal]}
    _idempotency[idempotency_key] = {
        "hash": fingerprint,
        "response": response,
    }
    return JSONResponse(status_code=201, content=response)
