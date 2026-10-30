"""Shared test fixtures and in-memory adapters."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from withdrawal_soles.core.settings import Settings
from withdrawal_soles.domain.exceptions import ReportingError
from withdrawal_soles.domain.models import AccountOwnership, Withdrawal
from withdrawal_soles.infrastructure.db.base import Base
from withdrawal_soles.main import create_app

ACCOUNT_ID = UUID("1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11")
OTHER_ACCOUNT_ID = UUID("2d8b6f1f-5a5b-4b2a-8b4f-8c0a1e3b7d22")
USER_ID = UUID("9d1e2f3a-4b5c-6d7e-8f90-1a2b3c4d5e6f")
OTHER_USER_ID = UUID("7a6b5c4d-3e2f-4a1b-8c9d-0e1f2a3b4c5d")
NOW = datetime(2026, 10, 30, 15, 0, tzinfo=UTC)


class FixedClock:
    """Deterministic clock for application and API tests."""

    def __init__(self, now: datetime = NOW, timezone_name: str = "America/Lima") -> None:
        self._now = now
        self._timezone = ZoneInfo(timezone_name)

    def now(self) -> datetime:
        return self._now

    def day_bounds(self) -> tuple[datetime, datetime]:
        local_now = self._now.astimezone(self._timezone)
        local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        return local_start.astimezone(UTC), (local_start + timedelta(days=1)).astimezone(
            UTC
        )


class FakeUserService:
    """Configurable account ownership source."""

    def __init__(self) -> None:
        self._accounts: dict[tuple[UUID, UUID], AccountOwnership] = {}
        self.error: Exception | None = None
        self.calls = 0

    def set_account(
        self,
        account_id: UUID = ACCOUNT_ID,
        user_id: UUID = USER_ID,
        *,
        currency: str = "PEN",
        status: str = "ACTIVE",
        owned: bool = True,
    ) -> None:
        self._accounts[(account_id, user_id)] = AccountOwnership(
            account_id=account_id,
            owner_user_id=user_id,
            currency=currency,
            status=status,
            owned=owned,
        )

    async def get_ownership(
        self, account_id: UUID, user_id: UUID
    ) -> AccountOwnership:
        self.calls += 1
        if self.error is not None:
            raise self.error
        configured = self._accounts.get((account_id, user_id))
        if configured is not None:
            return configured
        return AccountOwnership(
            account_id=account_id,
            owner_user_id=user_id,
            currency="PEN",
            status="ACTIVE",
            owned=True,
        )


class FakeTransactionService:
    """Configurable ledger reporter."""

    def __init__(self) -> None:
        self.failures_remaining = 0
        self.calls = 0
        self.reported: list[Withdrawal] = []

    async def report(self, withdrawal: Withdrawal) -> str:
        self.calls += 1
        if self.failures_remaining > 0:
            self.failures_remaining -= 1
            raise ReportingError("transaction-service is unavailable.")
        self.reported.append(withdrawal)
        return f"tx-{withdrawal.id}"


@pytest.fixture
async def app(tmp_path: Path) -> AsyncIterator[Any]:
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'withdrawal.db'}",
        user_service_url="http://user-service",
        transaction_service_url="http://transaction-service",
        http_backoff_seconds=0,
        business_timezone="America/Lima",
    )
    application = create_app(
        settings,
        user_service=FakeUserService(),
        transaction_service=FakeTransactionService(),
        clock=FixedClock(),
    )
    async with application.state.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield application
    await application.state.engine.dispose()


@pytest.fixture
async def client(app: Any) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as value:
        yield value


@pytest.fixture
async def session(app: Any) -> AsyncIterator[AsyncSession]:
    async with app.state.sessionmaker() as value:
        yield value


@pytest.fixture
def user_service(app: Any) -> FakeUserService:
    return app.state.user_service


@pytest.fixture
def transaction_service(app: Any) -> FakeTransactionService:
    return app.state.transaction_service


def headers(
    user_id: UUID = USER_ID, idempotency_key: str | None = "idem-1"
) -> dict[str, str]:
    values = {"X-User-Id": str(user_id)}
    if idempotency_key is not None:
        values["Idempotency-Key"] = idempotency_key
    return values


def payload(
    account_id: UUID = ACCOUNT_ID, amount: Decimal | str = "250.00"
) -> dict[str, str]:
    return {"account_id": str(account_id), "amount": str(amount)}


def new_id() -> UUID:
    return uuid4()
