"""Contract tests for the transaction-service adapter."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
import respx

from tests.conftest import ACCOUNT_ID, USER_ID
from withdrawal_soles.core.settings import Settings
from withdrawal_soles.domain.enums import WithdrawalStatus
from withdrawal_soles.domain.exceptions import ReportingError
from withdrawal_soles.domain.models import Withdrawal
from withdrawal_soles.infrastructure.clients.transaction_service import (
    TransactionServiceClient,
)

BASE_URL = "http://transaction-service"


def settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        user_service_url="http://user-service",
        transaction_service_url=BASE_URL,
        transaction_service_timeout_seconds=0.5,
        http_max_attempts=2,
        http_backoff_seconds=0,
    )


def withdrawal() -> Withdrawal:
    now = datetime(2026, 10, 30, tzinfo=UTC)
    return Withdrawal(
        id=uuid4(),
        account_id=ACCOUNT_ID,
        user_id=USER_ID,
        amount=Decimal("250.00"),
        currency="PEN",
        status=WithdrawalStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )


async def test_report_success() -> None:
    client = TransactionServiceClient(settings())
    value = withdrawal()
    with respx.mock(base_url=BASE_URL) as mock:
        route = mock.post("/api/v1/transactions").mock(
            return_value=httpx.Response(
                201, json={"transaction_id": f"tx-{value.id}"}
            )
        )
        transaction_id = await client.report(value)
    await client.aclose()

    assert transaction_id == f"tx-{value.id}"
    assert route.called
    request = route.calls[0].request
    assert request.headers["Idempotency-Key"] == str(value.id)


async def test_report_retries_server_error() -> None:
    client = TransactionServiceClient(settings())
    value = withdrawal()
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/api/v1/transactions").mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(201, json={"transaction_id": "tx-retry"}),
            ]
        )
        transaction_id = await client.report(value)
    await client.aclose()

    assert transaction_id == "tx-retry"


async def test_report_conflict_raises_reporting_error() -> None:
    client = TransactionServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/api/v1/transactions").mock(return_value=httpx.Response(409))
        with pytest.raises(ReportingError):
            await client.report(withdrawal())
    await client.aclose()


async def test_report_timeout_raises_reporting_error() -> None:
    client = TransactionServiceClient(settings())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.post("/api/v1/transactions").mock(
            side_effect=httpx.ReadTimeout("timeout")
        )
        with pytest.raises(ReportingError):
            await client.report(withdrawal())
    await client.aclose()
