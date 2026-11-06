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
from withdrawal_soles.domain.exceptions import (
    InsufficientBalance,
    ReportingError,
    WalletAlreadyReversed,
    WalletNotFound,
)
from withdrawal_soles.domain.models import (
    AccountOwnership,
    WalletBalance,
    WalletMovement,
    Withdrawal,
)
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
        id_usuario: int | None = 15,
    ) -> None:
        self._accounts[(account_id, user_id)] = AccountOwnership(
            account_id=account_id,
            owner_user_id=user_id,
            currency=currency,
            status=status,
            owned=owned,
            id_usuario=id_usuario,
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
            id_usuario=15,
        )


class FakeWalletService:
    """In-memory wallet with the same observable contract as the adapter."""

    def __init__(self) -> None:
        self.wallets: dict[int, WalletBalance] = {
            15: WalletBalance(
                id=UUID("a212968a-21d1-40f1-a47d-5f87c5b36a84"),
                id_usuario=15,
                currency="PEN",
                balance=1_000_000,
                created_at=NOW,
            ),
            16: WalletBalance(
                id=UUID("dadf4b90-cb5f-48ac-8046-5acb3726a7a9"),
                id_usuario=16,
                currency="PEN",
                balance=1500,
                created_at=NOW,
            ),
            18: WalletBalance(
                id=UUID("0b8b5c3f-b373-495f-80ef-555fc824ec8b"),
                id_usuario=18,
                currency="PEN",
                balance=500000,
                created_at=NOW,
            ),
        }
        self.movements: dict[UUID, WalletMovement] = {}
        self.reversed: set[UUID] = set()
        self.get_error: Exception | None = None
        self.debit_error: Exception | None = None
        self.reverse_error: Exception | None = None
        self.get_calls = 0
        self.debit_calls = 0
        self.reverse_calls = 0

    def wallet_for(self, id_usuario: int) -> WalletBalance:
        return self.wallets[id_usuario]

    def set_balance(self, id_usuario: int, balance: int) -> None:
        current = self.wallets[id_usuario]
        self.wallets[id_usuario] = WalletBalance(
            id=current.id,
            id_usuario=current.id_usuario,
            currency=current.currency,
            balance=balance,
            created_at=current.created_at,
        )

    async def get_wallet(self, id_usuario: int) -> WalletBalance:
        self.get_calls += 1
        if self.get_error is not None:
            raise self.get_error
        wallet = self.wallets.get(id_usuario)
        if wallet is None:
            raise WalletNotFound()
        return wallet

    async def debit(
        self,
        wallet_id: UUID,
        amount_cents: int,
        external_reference: str,
        idempotency_key: str,
    ) -> WalletMovement:
        self.debit_calls += 1
        if self.debit_error is not None:
            raise self.debit_error
        wallet = next(
            (value for value in self.wallets.values() if value.id == wallet_id),
            None,
        )
        if wallet is None:
            raise WalletNotFound()
        if wallet.balance < amount_cents:
            raise InsufficientBalance()
        movement = WalletMovement(
            id=uuid4(),
            wallet_id=wallet.id,
            amount=amount_cents,
            currency="PEN",
            direction="DEBIT",
            type="PAYMENT",
            external_reference=external_reference,
            created_at=NOW,
        )
        self.movements[movement.id] = movement
        self.wallets[wallet.id_usuario] = WalletBalance(
            id=wallet.id,
            id_usuario=wallet.id_usuario,
            currency=wallet.currency,
            balance=wallet.balance - amount_cents,
            created_at=wallet.created_at,
        )
        return movement

    async def reverse(
        self,
        movement_id: UUID,
        reason: str,
        idempotency_key: str,
    ) -> WalletMovement:
        self.reverse_calls += 1
        if self.reverse_error is not None:
            raise self.reverse_error
        original = self.movements.get(movement_id)
        if original is None:
            raise WalletNotFound()
        if movement_id in self.reversed:
            raise WalletAlreadyReversed()
        wallet = next(
            (value for value in self.wallets.values() if value.id == original.wallet_id),
            None,
        )
        if wallet is None:
            raise WalletNotFound()
        self.reversed.add(movement_id)
        reversal = WalletMovement(
            id=uuid4(),
            wallet_id=original.wallet_id,
            amount=original.amount,
            currency="PEN",
            direction="CREDIT",
            type="REVERSAL",
            reversal_of=movement_id,
            created_at=NOW,
        )
        self.movements[reversal.id] = reversal
        self.wallets[wallet.id_usuario] = WalletBalance(
            id=wallet.id,
            id_usuario=wallet.id_usuario,
            currency=wallet.currency,
            balance=wallet.balance + original.amount,
            created_at=wallet.created_at,
        )
        return reversal


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
        wallet_service=FakeWalletService(),
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


@pytest.fixture
def wallet_service(app: Any) -> FakeWalletService:
    return app.state.wallet_service


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
