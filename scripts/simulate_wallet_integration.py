"""End-to-end simulation of the withdrawal <-> wallet integration.

Run the real FastAPI use cases and the real wallet adapter against either the
local simulator or the published wallet:

    .venv/bin/python scripts/simulate_wallet_integration.py --mode simulate
    .venv/bin/python scripts/simulate_wallet_integration.py --mode live

The live run debits S/ 10.00 and reverses it before exiting, so the seeded
wallet balance is restored.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import UUID, uuid4

import httpx

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mock_dependencies import app as mock_wallet_app  # noqa: E402
from withdrawal_soles.core.settings import Settings  # noqa: E402
from withdrawal_soles.domain.exceptions import (  # noqa: E402
    DependencyUnavailable,
    UserInactive,
    UserNotFound,
)
from withdrawal_soles.domain.models import (  # noqa: E402
    AccountOwnership,
    UserIdentity,
    WalletBalance,
    WalletMovement,
    Withdrawal,
)
from withdrawal_soles.infrastructure.clients.wallet_service import (  # noqa: E402
    WalletServiceClient,
)
from withdrawal_soles.infrastructure.clock import SystemClock  # noqa: E402
from withdrawal_soles.infrastructure.db.base import Base  # noqa: E402
from withdrawal_soles.infrastructure.service_jwt import (  # noqa: E402
    sign_service_token,
)
from withdrawal_soles.main import create_app  # noqa: E402

ACCOUNT_ID = UUID("1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11")
USER_ID = UUID("9d1e2f3a-4b5c-6d7e-8f90-1a2b3c4d5e6f")
LIVE_BASE_URL = "http://18.228.136.200"
SEED_USERS = {15: True, 16: True, 17: False, 18: True, 19: True}


class SimulationUserService:
    """Ownership and users-contract source for the simulation."""

    def __init__(self) -> None:
        self.id_usuario = 15
        self.status = "ACTIVE"
        self.get_user_calls = 0

    async def get_ownership(
        self, account_id: UUID, user_id: UUID
    ) -> AccountOwnership:
        return AccountOwnership(
            account_id=account_id,
            owner_user_id=user_id,
            currency="PEN",
            status=self.status,
            owned=True,
            id_usuario=self.id_usuario,
        )

    async def get_user(self, id_usuario: int) -> UserIdentity:
        self.get_user_calls += 1
        active = SEED_USERS.get(id_usuario)
        if active is None:
            raise UserNotFound()
        if not active:
            raise UserInactive()
        return UserIdentity(id_usuario=id_usuario, active=True)


class SimulationTransactionService:
    """Ledger reporter that can fail once to exercise the APPROVED path."""

    def __init__(self) -> None:
        self.fail_next = False
        self.calls = 0

    async def report(self, withdrawal: Withdrawal) -> str:
        self.calls += 1
        if self.fail_next:
            self.fail_next = False
            from withdrawal_soles.domain.exceptions import ReportingError

            raise ReportingError("simulated ledger failure")
        return f"tx-{withdrawal.id}"


class WalletProxy:
    """Wallet adapter wrapper that can simulate a dependency outage."""

    def __init__(self, inner: WalletServiceClient) -> None:
        self.inner = inner
        self.fail_next_get = False

    async def get_wallet(self, id_usuario: int) -> WalletBalance:
        if self.fail_next_get:
            raise DependencyUnavailable("billetera", "simulated wallet outage")
        return await self.inner.get_wallet(id_usuario)

    async def debit(
        self,
        wallet_id: UUID,
        amount_cents: int,
        external_reference: str,
        idempotency_key: str,
    ) -> WalletMovement:
        return await self.inner.debit(
            wallet_id, amount_cents, external_reference, idempotency_key
        )

    async def reverse(
        self, movement_id: UUID, reason: str, idempotency_key: str
    ) -> WalletMovement:
        return await self.inner.reverse(movement_id, reason, idempotency_key)

    async def aclose(self) -> None:
        await self.inner.aclose()


class Results:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def check(self, name: str, passed: bool, detail: str) -> bool:
        self.rows.append({"check": name, "pass": passed, "detail": detail})
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
        return passed

    @property
    def passed(self) -> int:
        return sum(1 for row in self.rows if row["pass"])

    @property
    def failed(self) -> int:
        return len(self.rows) - self.passed


def headers(key: str | None = None) -> dict[str, str]:
    token = sign_service_token(
        secret="dev-only-change-me",
        issuer="billetera-dev",
        subject="retiros",
        ttl_seconds=3600,
    )
    values = {
        "Authorization": f"Bearer {token}",
        "X-User-Id": str(USER_ID),
        "Content-Type": "application/json",
    }
    if key is not None:
        values["Idempotency-Key"] = key
    return values


async def list_total(client: httpx.AsyncClient) -> int:
    response = await client.get("/api/v1/withdrawals", headers=headers())
    response.raise_for_status()
    return int(response.json()["total"])


async def create_withdrawal(
    client: httpx.AsyncClient,
    *,
    key: str,
    amount: str,
) -> httpx.Response:
    return await client.post(
        "/api/v1/withdrawals",
        headers=headers(key),
        json={"account_id": str(ACCOUNT_ID), "amount": amount},
    )


async def run(mode: str, amount: str, id_usuario: int) -> int:
    results = Results()
    temporary = TemporaryDirectory(prefix="wallet-simulation-")
    database_url = f"sqlite+aiosqlite:///{temporary.name}/simulation.db"

    if mode == "simulate":
        wallet_http = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=mock_wallet_app),
            base_url="http://wallet-simulator",
        )
        wallet_base_url = "http://wallet-simulator"
    else:
        wallet_http = httpx.AsyncClient(
            base_url=LIVE_BASE_URL,
            timeout=5.0,
        )
        wallet_base_url = LIVE_BASE_URL

    settings = Settings(
        database_url=database_url,
        user_service_url="http://user-simulator",
        transaction_service_url="http://transaction-simulator",
        wallet_service_url=wallet_base_url,
        wallet_service_timeout_seconds=2.0,
        wallet_jwt_secret="dev-only-change-me",
        wallet_jwt_issuer="billetera-dev",
        wallet_jwt_subject="retiros",
        wallet_jwt_ttl_seconds=60,
        http_max_attempts=2,
        http_backoff_seconds=0.0,
        business_timezone="America/Lima",
    )
    wallet_client = WalletServiceClient(settings, client=wallet_http)
    wallet = WalletProxy(wallet_client)
    user_service = SimulationUserService()
    user_service.id_usuario = id_usuario
    transaction_service = SimulationTransactionService()

    application = create_app(
        settings,
        user_service=user_service,
        transaction_service=transaction_service,
        wallet_service=wallet,
        clock=SystemClock("America/Lima"),
    )
    async with application.state.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    withdrawal_id: str | None = None
    wallet_movement_id: str | None = None
    reversed_ok = False
    try:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://withdrawal-soles", timeout=10.0
        ) as client:
            print(
                f"=== Withdrawal <-> wallet integration ({mode}) "
                f"idUsuario={id_usuario} amount=S/ {amount} ==="
            )
            before = await wallet_client.get_wallet(id_usuario)
            results.check(
                "wallet before",
                True,
                f"walletId={before.id} balance={before.balance} cents "
                f"(S/ {before.balance / 100:.2f})",
            )

            total_before = await list_total(client)
            key = f"sim-{uuid4()}"
            created = await create_withdrawal(client, key=key, amount=amount)
            body = created.json()
            withdrawal_id = body.get("id")
            wallet_movement_id = body.get("wallet_movement_id")
            cents = int(Decimal(amount) * 100)
            results.check(
                "create debits wallet",
                created.status_code == 201
                and body.get("status") == "COMPLETED"
                and bool(body.get("wallet_movement_id")),
                f"HTTP {created.status_code} status={body.get('status')} "
                f"wallet_movement_id={body.get('wallet_movement_id')}",
            )

            after_debit = await wallet_client.get_wallet(id_usuario)
            results.check(
                "balance after debit",
                after_debit.balance == before.balance - cents,
                f"{before.balance} -> {after_debit.balance} (expected "
                f"{before.balance - cents})",
            )
            results.check(
                "withdrawal counted",
                await list_total(client) == total_before + 1,
                f"total {total_before} -> {total_before + 1}",
            )

            replay = await create_withdrawal(client, key=key, amount=amount)
            after_replay = await wallet_client.get_wallet(id_usuario)
            results.check(
                "idempotent replay",
                replay.status_code == 200
                and replay.json().get("id") == withdrawal_id
                and after_replay.balance == after_debit.balance,
                f"HTTP {replay.status_code} same_id="
                f"{replay.json().get('id') == withdrawal_id} "
                f"balance={after_replay.balance}",
            )

            # Insufficient balance: user 16 has S/ 15.00 in both environments.
            user_service.id_usuario = 16
            total_before_failure = await list_total(client)
            insufficient = await create_withdrawal(
                client, key=f"sim-insufficient-{uuid4()}", amount="20.00"
            )
            results.check(
                "insufficient balance",
                insufficient.status_code == 422
                and insufficient.json().get("code") == "INSUFFICIENT_BALANCE"
                and await list_total(client) == total_before_failure,
                f"HTTP {insufficient.status_code} "
                f"code={insufficient.json().get('code')}",
            )

            # Missing wallet: user 19 is active but has no wallet (simulator only).
            if mode == "simulate":
                user_service.id_usuario = 19
                missing = await create_withdrawal(
                    client, key=f"sim-missing-{uuid4()}", amount=amount
                )
                results.check(
                    "missing wallet",
                    missing.status_code == 404
                    and missing.json().get("code") == "WALLET_NOT_FOUND"
                    and await list_total(client) == total_before_failure,
                    f"HTTP {missing.status_code} code={missing.json().get('code')}",
                )

                # Inactive wallet user: user 17 fails before any wallet call.
                user_service.id_usuario = 17
                inactive = await create_withdrawal(
                    client, key=f"sim-inactive-{uuid4()}", amount=amount
                )
                results.check(
                    "inactive user",
                    inactive.status_code == 422
                    and inactive.json().get("code") == "USER_INACTIVE"
                    and await list_total(client) == total_before_failure,
                    f"HTTP {inactive.status_code} "
                    f"code={inactive.json().get('code')}",
                )

                # Unknown wallet user: user 99 does not exist.
                user_service.id_usuario = 99
                unknown = await create_withdrawal(
                    client, key=f"sim-unknown-{uuid4()}", amount=amount
                )
                results.check(
                    "unknown user",
                    unknown.status_code == 404
                    and unknown.json().get("code") == "USER_NOT_FOUND"
                    and await list_total(client) == total_before_failure,
                    f"HTTP {unknown.status_code} "
                    f"code={unknown.json().get('code')}",
                )

            # Wallet outage: no local withdrawal is committed.
            user_service.id_usuario = id_usuario
            wallet.fail_next_get = True
            try:
                outage = await create_withdrawal(
                    client, key=f"sim-outage-{uuid4()}", amount=amount
                )
            finally:
                wallet.fail_next_get = False
            results.check(
                "wallet outage",
                outage.status_code == 503
                and outage.json().get("code") == "DEPENDENCY_UNAVAILABLE"
                and await list_total(client) == total_before_failure,
                f"HTTP {outage.status_code} code={outage.json().get('code')}",
            )

            if mode == "simulate":
                # Ledger failure keeps the debit and the APPROVED state.
                transaction_service.fail_next = True
                pending = await create_withdrawal(
                    client, key=f"sim-report-fail-{uuid4()}", amount=amount
                )
                pending_body = pending.json()
                results.check(
                    "report failure keeps debit",
                    pending.status_code == 201
                    and pending_body.get("status") == "APPROVED"
                    and bool(pending_body.get("wallet_movement_id")),
                    f"HTTP {pending.status_code} "
                    f"status={pending_body.get('status')}",
                )
                pending_reverse = await client.post(
                    f"/api/v1/withdrawals/{pending_body['id']}/reverse",
                    headers=headers(f"sim-reverse-pending-{uuid4()}"),
                    json={"reason": "simulated report failure"},
                )
                results.check(
                    "reverse approved withdrawal",
                    pending_reverse.status_code == 200
                    and pending_reverse.json().get("status") == "REVERSED",
                    f"HTTP {pending_reverse.status_code} "
                    f"status={pending_reverse.json().get('status')}",
                )

            # Reverse the main debit and verify the original balance.
            reverse_key = f"sim-reverse-{uuid4()}"
            reversed_response = await client.post(
                f"/api/v1/withdrawals/{withdrawal_id}/reverse",
                headers=headers(reverse_key),
                json={"reason": "integration simulation"},
            )
            reversed_body = reversed_response.json()
            restored = await wallet_client.get_wallet(id_usuario)
            reversed_ok = (
                reversed_response.status_code == 200
                and reversed_body.get("status") == "REVERSED"
                and bool(reversed_body.get("wallet_reversal_movement_id"))
                and restored.balance == before.balance
            )
            results.check(
                "reverse restores balance",
                reversed_ok,
                f"HTTP {reversed_response.status_code} "
                f"status={reversed_body.get('status')} balance={restored.balance} "
                f"(expected {before.balance})",
            )

            second = await client.post(
                f"/api/v1/withdrawals/{withdrawal_id}/reverse",
                headers=headers(f"sim-reverse-again-{uuid4()}"),
                json={"reason": "integration simulation"},
            )
            results.check(
                "second reverse rejected",
                second.status_code == 422
                and second.json().get("code") == "WALLET_ALREADY_REVERSED",
                f"HTTP {second.status_code} code={second.json().get('code')}",
            )

            if mode == "simulate":
                history = await wallet_client.get_movements(before.id)
                history_ids = {str(movement.id) for movement in history}
                results.check(
                    "wallet history",
                    str(wallet_movement_id) in history_ids
                    and str(reversed_body.get("wallet_reversal_movement_id"))
                    in history_ids,
                    f"{len(history)} movements include the debit and the reversal",
                )
    finally:
        # Safety net for the live wallet: never leave a debited balance behind.
        if wallet_movement_id is not None and not reversed_ok:
            try:
                await wallet_client.reverse(
                    UUID(wallet_movement_id),
                    "safety reversal after simulation error",
                    f"{withdrawal_id}:reverse",
                )
            except Exception as error:  # noqa: BLE001
                print(f"[WARN] safety reversal failed: {error}", file=sys.stderr)
        await wallet_client.aclose()
        await application.state.engine.dispose()
        temporary.cleanup()

    print()
    print(
        f"Summary: {results.passed}/{len(results.rows)} checks passed"
        + (f", {results.failed} failed" if results.failed else "")
    )
    print(json.dumps(results.rows, indent=2))
    return 1 if results.failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["simulate", "live"],
        default="simulate",
        help="Use the local wallet simulator or the published wallet.",
    )
    parser.add_argument(
        "--amount",
        default="10.00",
        help="Withdrawal amount in PEN. Defaults to 10.00.",
    )
    parser.add_argument(
        "--id-usuario",
        type=int,
        default=15,
        help="Wallet user for the happy path. Defaults to 15 (Ana).",
    )
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(run(args.mode, args.amount, args.id_usuario))
    )


if __name__ == "__main__":
    main()
