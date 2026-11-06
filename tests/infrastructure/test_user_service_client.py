"""Contract tests for the user-service adapter."""

from uuid import UUID

import httpx
import jwt
import pytest
import respx

from tests.conftest import ACCOUNT_ID, USER_ID
from withdrawal_soles.core.settings import Settings
from withdrawal_soles.domain.exceptions import (
    AccountNotFound,
    AccountNotOwned,
    DependencyUnavailable,
    UserInactive,
    UserNotFound,
)
from withdrawal_soles.infrastructure.clients.user_service import UserServiceClient

BASE_URL = "http://user-service"
SECRET = "dev-only-change-me"


def settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        user_service_url=BASE_URL,
        transaction_service_url="http://transaction-service",
        user_service_timeout_seconds=0.5,
        http_max_attempts=2,
        http_backoff_seconds=0,
    )


def ownership_payload(
    owned: bool = True, currency: str = "PEN", id_usuario: int | None = 15
) -> dict[str, object]:
    payload: dict[str, object] = {
        "account_id": str(ACCOUNT_ID),
        "owner_user_id": str(USER_ID),
        "currency": currency,
        "status": "ACTIVE",
        "owned": owned,
    }
    if id_usuario is not None:
        payload["id_usuario"] = id_usuario
    return payload


async def test_ownership_success() -> None:
    client = UserServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        route = mock.get(
            f"/api/v1/accounts/{ACCOUNT_ID}/ownership"
        ).mock(return_value=httpx.Response(200, json=ownership_payload()))
        result = await client.get_ownership(ACCOUNT_ID, USER_ID)
    await client.aclose()

    assert route.called
    assert result.owned is True
    assert result.currency == "PEN"
    assert result.id_usuario == 15
    assert isinstance(result.account_id, UUID)


async def test_ownership_without_id_usuario_is_none() -> None:
    client = UserServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get(f"/api/v1/accounts/{ACCOUNT_ID}/ownership").mock(
            return_value=httpx.Response(
                200, json=ownership_payload(id_usuario=None)
            )
        )
        result = await client.get_ownership(ACCOUNT_ID, USER_ID)
    await client.aclose()

    assert result.id_usuario is None


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [(403, AccountNotOwned), (404, AccountNotFound)],
)
async def test_ownership_error_mapping(status_code: int, expected: type[Exception]) -> None:
    client = UserServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get(f"/api/v1/accounts/{ACCOUNT_ID}/ownership").mock(
            return_value=httpx.Response(status_code)
        )
        with pytest.raises(expected):
            await client.get_ownership(ACCOUNT_ID, USER_ID)
    await client.aclose()


async def test_ownership_timeout() -> None:
    client = UserServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get(f"/api/v1/accounts/{ACCOUNT_ID}/ownership").mock(
            side_effect=httpx.ConnectTimeout("timeout")
        )
        with pytest.raises(DependencyUnavailable):
            await client.get_ownership(ACCOUNT_ID, USER_ID)
    await client.aclose()


async def test_ownership_server_error() -> None:
    client = UserServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get(f"/api/v1/accounts/{ACCOUNT_ID}/ownership").mock(
            return_value=httpx.Response(500)
        )
        with pytest.raises(DependencyUnavailable):
            await client.get_ownership(ACCOUNT_ID, USER_ID)
    await client.aclose()


async def test_get_user_success_and_jwt_claims() -> None:
    client = UserServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        route = mock.get("/usuarios/15").mock(
            return_value=httpx.Response(
                200, json={"idUsuario": 15, "estado": True}
            )
        )
        result = await client.get_user(15)
    await client.aclose()

    assert result.id_usuario == 15
    assert result.active is True
    token = route.calls[0].request.headers["Authorization"].removeprefix(
        "Bearer "
    )
    claims = jwt.decode(
        token, SECRET, algorithms=["HS256"], issuer="billetera-dev"
    )
    assert claims["sub"] == "billetera-service"
    assert claims["exp"] - claims["iat"] == 60


async def test_get_user_accepts_id_usuario_alias() -> None:
    client = UserServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/usuarios/16").mock(
            return_value=httpx.Response(
                200, json={"id_usuario": 16, "estado": True}
            )
        )
        result = await client.get_user(16)
    await client.aclose()

    assert result.id_usuario == 16


@pytest.mark.parametrize(
    "payload",
    [
        {"idUsuario": 99, "estado": True},
        {"estado": True},
        {"idUsuario": "not-a-number", "estado": True},
    ],
)
async def test_get_user_id_mismatch_is_not_found(
    payload: dict[str, object],
) -> None:
    client = UserServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/usuarios/15").mock(
            return_value=httpx.Response(200, json=payload)
        )
        with pytest.raises(UserNotFound):
            await client.get_user(15)
    await client.aclose()


async def test_get_user_not_found() -> None:
    client = UserServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/usuarios/15").mock(
            return_value=httpx.Response(
                404, json={"detail": "El usuario no existe"}
            )
        )
        with pytest.raises(UserNotFound):
            await client.get_user(15)
    await client.aclose()


@pytest.mark.parametrize(
    "estado", [False, None, "true", 1, 0, "false"]
)
async def test_get_user_inactive(estado: object) -> None:
    client = UserServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/usuarios/15").mock(
            return_value=httpx.Response(
                200, json={"idUsuario": 15, "estado": estado}
            )
        )
        with pytest.raises(UserInactive):
            await client.get_user(15)
    await client.aclose()


async def test_get_user_timeout() -> None:
    client = UserServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/usuarios/15").mock(
            side_effect=httpx.ConnectTimeout("timeout")
        )
        with pytest.raises(DependencyUnavailable):
            await client.get_user(15)
    await client.aclose()


async def test_get_user_server_error() -> None:
    client = UserServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/usuarios/15").mock(
            return_value=httpx.Response(500)
        )
        with pytest.raises(DependencyUnavailable):
            await client.get_user(15)
    await client.aclose()
