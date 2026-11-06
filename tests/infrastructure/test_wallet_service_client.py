"""Contract tests for the wallet-service adapter."""

from datetime import UTC, datetime
from uuid import UUID

import httpx
import jwt
import pytest
import respx

from withdrawal_soles.core.settings import Settings
from withdrawal_soles.domain.exceptions import (
    DependencyUnavailable,
    InsufficientBalance,
    WalletAlreadyReversed,
    WalletAuthFailed,
    WalletConflict,
    WalletNotFound,
    WalletUserInactive,
)
from withdrawal_soles.infrastructure.clients.wallet_service import WalletServiceClient

BASE_URL = "http://wallet-service"
WALLET_ID = UUID("a212968a-21d1-40f1-a47d-5f87c5b36a84")
MOVEMENT_ID = UUID("9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d")
SECRET = "dev-only-change-me"


def settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        user_service_url="http://user-service",
        transaction_service_url="http://transaction-service",
        wallet_service_url=BASE_URL,
        wallet_service_timeout_seconds=0.5,
        wallet_jwt_secret=SECRET,
        wallet_jwt_issuer="billetera-dev",
        wallet_jwt_subject="retiros",
        wallet_jwt_ttl_seconds=60,
        http_max_attempts=2,
        http_backoff_seconds=0,
    )


def wallet_payload(balance: int = 25000) -> dict[str, object]:
    return {
        "id": str(WALLET_ID),
        "idUsuario": 15,
        "currency": "PEN",
        "balance": balance,
        "createdAt": "2026-11-06T20:17:50.707Z",
    }


def movement_payload(
    *, direction: str = "DEBIT", movement_type: str = "PAYMENT"
) -> dict[str, object]:
    return {
        "id": str(MOVEMENT_ID),
        "walletId": str(WALLET_ID),
        "amount": 25000,
        "currency": "PEN",
        "direction": direction,
        "type": movement_type,
        "counterpartyWalletId": None,
        "externalReference": "14544b68-9c70-4365-bd40-6ba0824bba15",
        "reversalOf": None,
        "createdAt": "2026-11-06T20:20:00.000Z",
    }


async def test_get_wallet_success_and_jwt_claims() -> None:
    client = WalletServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        route = mock.get("/v1/wallets").mock(
            return_value=httpx.Response(200, json=wallet_payload())
        )
        result = await client.get_wallet(15)
    await client.aclose()

    assert result.id == WALLET_ID
    assert result.balance == 25000
    token = route.calls[0].request.headers["Authorization"].removeprefix("Bearer ")
    claims = jwt.decode(
        token,
        SECRET,
        algorithms=["HS256"],
        issuer="billetera-dev",
    )
    assert claims["sub"] == "retiros"
    assert claims["exp"] - claims["iat"] == 60


async def test_get_wallet_not_found() -> None:
    client = WalletServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/v1/wallets").mock(
            return_value=httpx.Response(
                404,
                json={
                    "title": "No encontrado",
                    "status": 404,
                    "detail": "Billetera no encontrada",
                },
            )
        )
        with pytest.raises(WalletNotFound):
            await client.get_wallet(17)
    await client.aclose()


async def test_debit_sends_cents_and_idempotency() -> None:
    client = WalletServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        route = mock.post(f"/v1/wallets/{WALLET_ID}/payments").mock(
            return_value=httpx.Response(201, json=movement_payload())
        )
        movement = await client.debit(
            WALLET_ID,
            amount_cents=25000,
            external_reference="14544b68-9c70-4365-bd40-6ba0824bba15",
            idempotency_key="14544b68-9c70-4365-bd40-6ba0824bba15",
        )
    await client.aclose()

    assert movement.id == MOVEMENT_ID
    assert movement.direction == "DEBIT"
    request = route.calls[0].request
    assert request.headers["Idempotency-Key"] == (
        "14544b68-9c70-4365-bd40-6ba0824bba15"
    )
    body = route.calls[0].request.content.decode()
    assert '"amount":25000' in body
    assert '"currency":"PEN"' in body


@pytest.mark.parametrize(
    ("status", "detail", "expected"),
    [
        (422, "Saldo insuficiente", InsufficientBalance),
        (422, "El usuario no está activo", WalletUserInactive),
        (409, "La clave de idempotencia ya se uso con otro cuerpo", WalletConflict),
        (401, "Token invalido", WalletAuthFailed),
    ],
)
async def test_debit_error_mapping(
    status: int, detail: str, expected: type[Exception]
) -> None:
    client = WalletServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post(f"/v1/wallets/{WALLET_ID}/payments").mock(
            return_value=httpx.Response(
                status, json={"title": "Error", "status": status, "detail": detail}
            )
        )
        with pytest.raises(expected):
            await client.debit(WALLET_ID, 25000, "ref", "key")
    await client.aclose()


async def test_debit_timeout_is_unavailable() -> None:
    client = WalletServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post(f"/v1/wallets/{WALLET_ID}/payments").mock(
            side_effect=httpx.ConnectTimeout("timeout")
        )
        with pytest.raises(DependencyUnavailable):
            await client.debit(WALLET_ID, 25000, "ref", "key")
    await client.aclose()


async def test_debit_server_error_is_unavailable() -> None:
    client = WalletServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post(f"/v1/wallets/{WALLET_ID}/payments").mock(
            side_effect=[httpx.Response(503), httpx.Response(503)]
        )
        with pytest.raises(DependencyUnavailable):
            await client.debit(WALLET_ID, 25000, "ref", "key")
    await client.aclose()


async def test_reverse_success_reads_movements_wrapper() -> None:
    client = WalletServiceClient(settings())
    payload = {
        "movements": [
            movement_payload(direction="CREDIT", movement_type="REVERSAL")
        ]
    }
    with respx.mock(base_url=BASE_URL) as mock:
        route = mock.post(f"/v1/movements/{MOVEMENT_ID}/reverse").mock(
            return_value=httpx.Response(201, json=payload)
        )
        movement = await client.reverse(
            MOVEMENT_ID,
            reason="retiro anulado",
            idempotency_key=f"{MOVEMENT_ID}:reverse",
        )
    await client.aclose()

    assert movement.direction == "CREDIT"
    assert movement.type == "REVERSAL"
    assert route.calls[0].request.headers["Idempotency-Key"] == (
        f"{MOVEMENT_ID}:reverse"
    )


async def test_reverse_already_reversed() -> None:
    client = WalletServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post(f"/v1/movements/{MOVEMENT_ID}/reverse").mock(
            return_value=httpx.Response(
                422,
                json={"detail": "El movimiento ya fue reversado", "status": 422},
            )
        )
        with pytest.raises(WalletAlreadyReversed):
            await client.reverse(MOVEMENT_ID, "retiro anulado", "key")
    await client.aclose()


async def test_reverse_missing_movement() -> None:
    client = WalletServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post(f"/v1/movements/{MOVEMENT_ID}/reverse").mock(
            return_value=httpx.Response(404)
        )
        with pytest.raises(WalletNotFound):
            await client.reverse(MOVEMENT_ID, "retiro anulado", "key")
    await client.aclose()


def test_parse_datetime_keeps_timezone() -> None:
    from withdrawal_soles.infrastructure.clients.wallet_service import (
        _parse_datetime,
    )

    value = _parse_datetime("2026-11-06T20:17:50.707Z")
    assert value == datetime(2026, 11, 6, 20, 17, 50, 707000, tzinfo=UTC)
