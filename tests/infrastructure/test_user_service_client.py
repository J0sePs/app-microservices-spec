"""Contract tests for the user-service adapter."""

from uuid import UUID

import httpx
import pytest
import respx

from tests.conftest import ACCOUNT_ID, USER_ID
from withdrawal_soles.core.settings import Settings
from withdrawal_soles.domain.exceptions import (
    AccountNotFound,
    AccountNotOwned,
    DependencyUnavailable,
)
from withdrawal_soles.infrastructure.clients.user_service import UserServiceClient

BASE_URL = "http://user-service"


def settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        user_service_url=BASE_URL,
        transaction_service_url="http://transaction-service",
        user_service_timeout_seconds=0.5,
        http_max_attempts=2,
        http_backoff_seconds=0,
    )


def ownership_payload(owned: bool = True, currency: str = "PEN") -> dict[str, object]:
    return {
        "account_id": str(ACCOUNT_ID),
        "owner_user_id": str(USER_ID),
        "currency": currency,
        "status": "ACTIVE",
        "owned": owned,
    }


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
    assert isinstance(result.account_id, UUID)


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
