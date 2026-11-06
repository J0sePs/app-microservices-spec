"""HTTP API contract tests."""

from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from tests.conftest import (
    OTHER_ACCOUNT_ID,
    OTHER_USER_ID,
    USER_ID,
    FakeTransactionService,
    FakeUserService,
    FixedClock,
    headers,
    payload,
    service_token,
)
from withdrawal_soles.core.settings import Settings
from withdrawal_soles.domain.enums import WithdrawalStatus
from withdrawal_soles.domain.models import Withdrawal
from withdrawal_soles.infrastructure.db.repository import (
    SQLAlchemyWithdrawalRepository,
)
from withdrawal_soles.main import create_app


async def create(client, *, key: str, amount: str = "250.00", user_id=USER_ID):
    return await client.post(
        "/api/v1/withdrawals",
        json=payload(amount=amount),
        headers=headers(user_id=user_id, idempotency_key=key),
    )


async def test_create_and_get_withdrawal(client) -> None:
    response = await create(client, key="api-1")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["currency"] == "PEN"
    assert body["amount"] == "250.00"
    assert body["transaction_id"].startswith("tx-")

    fetched = await client.get(
        f"/api/v1/withdrawals/{body['id']}", headers=headers()
    )
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


async def test_missing_identity_returns_401(client) -> None:
    response = await client.post(
        "/api/v1/withdrawals",
        json=payload(),
        headers={"Idempotency-Key": "missing-user"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


async def test_missing_token_returns_401(client) -> None:
    response = await client.post(
        "/api/v1/withdrawals",
        json=payload(),
        headers={
            "X-User-Id": str(USER_ID),
            "Idempotency-Key": "missing-token",
        },
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"
    assert response.headers["www-authenticate"] == "Bearer"


async def test_missing_user_with_valid_token_returns_401(client) -> None:
    response = await client.get(
        "/api/v1/withdrawals",
        headers={"Authorization": f"Bearer {service_token()}"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize(
    "token",
    [
        service_token(secret="wrong-secret"),
        service_token(issuer="other-issuer"),
        service_token(subject="billetera-service"),
        service_token(expires_in=-60),
    ],
)
async def test_invalid_token_returns_401(client, token: str) -> None:
    response = await client.get(
        "/api/v1/withdrawals", headers=headers(token=token)
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


async def test_missing_idempotency_returns_422(client) -> None:
    response = await client.post(
        "/api/v1/withdrawals",
        json=payload(),
        headers={
            "Authorization": f"Bearer {service_token()}",
            "X-User-Id": str(USER_ID),
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "MISSING_IDEMPOTENCY_KEY"


@pytest.mark.parametrize("amount", ["9.99", "5000.01"])
async def test_amount_outside_limits_returns_422(client, amount: str) -> None:
    response = await create(client, key=f"amount-{amount}", amount=amount)
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_AMOUNT"


async def test_idempotency_replay_returns_original(client) -> None:
    first = await create(client, key="replay-api")
    second = await create(client, key="replay-api")
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    listing = await client.get(
        "/api/v1/withdrawals", headers=headers()
    )
    assert listing.json()["total"] == 1


async def test_idempotency_conflict_returns_409(client) -> None:
    await create(client, key="conflict-key", amount="250.00")
    response = await create(client, key="conflict-key", amount="300.00")
    assert response.status_code == 409
    assert response.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_non_owned_account_returns_403(client, user_service) -> None:
    user_service.set_account(owned=False)
    response = await create(client, key="not-owned")
    assert response.status_code == 403
    assert response.json()["code"] == "ACCOUNT_NOT_OWNED"


async def test_usd_account_returns_422(client, user_service) -> None:
    user_service.set_account(currency="USD")
    response = await create(client, key="usd-account")
    assert response.status_code == 422
    assert response.json()["code"] == "ACCOUNT_NOT_ELIGIBLE"


async def test_user_service_unavailable_returns_503(
    client, user_service
) -> None:
    from withdrawal_soles.domain.exceptions import DependencyUnavailable

    user_service.error = DependencyUnavailable("user-service")
    response = await create(client, key="user-down")
    assert response.status_code == 503
    assert response.json()["code"] == "DEPENDENCY_UNAVAILABLE"


async def test_report_failure_then_retry(client, transaction_service) -> None:
    transaction_service.failures_remaining = 1
    created = await create(client, key="report-retry")
    assert created.status_code == 201
    assert created.json()["status"] == "APPROVED"

    withdrawal_id = created.json()["id"]
    retried = await client.post(
        f"/api/v1/withdrawals/{withdrawal_id}/report",
        headers=headers(idempotency_key="report-retry-2"),
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "COMPLETED"


async def test_report_retry_failure_returns_202(
    client, transaction_service
) -> None:
    transaction_service.failures_remaining = 2
    created = await create(client, key="report-retry-fails")
    assert created.status_code == 201
    assert created.json()["status"] == "APPROVED"

    retried = await client.post(
        f"/api/v1/withdrawals/{created.json()['id']}/report",
        headers=headers(idempotency_key="report-retry-fails-2"),
    )
    assert retried.status_code == 202
    assert retried.json()["status"] == "APPROVED"


async def test_other_user_cannot_read(client) -> None:
    created = await create(client, key="private")
    response = await client.get(
        f"/api/v1/withdrawals/{created.json()['id']}",
        headers=headers(user_id=OTHER_USER_ID),
    )
    assert response.status_code == 404


async def test_list_filters_and_pagination(client) -> None:
    await create(client, key="list-1", amount="100.00")
    await create(client, key="list-2", amount="200.00", user_id=USER_ID)
    response = await client.get(
        "/api/v1/withdrawals",
        params={"status": "COMPLETED", "limit": 1, "offset": 0},
        headers=headers(),
    )
    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 2
    assert body["limit"] == 1
    assert len(body["items"]) == 1


async def test_cancel_pending_is_idempotent(client, session) -> None:
    pending = Withdrawal(
        id=uuid4(),
        account_id=OTHER_ACCOUNT_ID,
        user_id=USER_ID,
        amount=Decimal("100.00"),
        currency="PEN",
        status=WithdrawalStatus.PENDING,
        created_at=FixedClock().now(),
        updated_at=FixedClock().now(),
    )
    repository = SQLAlchemyWithdrawalRepository(session)
    await repository.add(pending)
    await session.commit()

    first = await client.post(
        f"/api/v1/withdrawals/{pending.id}/cancel",
        headers=headers(idempotency_key="cancel-1"),
    )
    second = await client.post(
        f"/api/v1/withdrawals/{pending.id}/cancel",
        headers=headers(idempotency_key="cancel-2"),
    )
    assert first.status_code == 200
    assert first.json()["status"] == "REJECTED"
    assert second.status_code == 200
    assert second.json()["status"] == "REJECTED"


async def test_root_returns_service_links(client) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "withdrawal-soles"
    assert body["docs"] == "/docs"
    assert body["health"] == "/health"


async def test_health_ok(client) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_unavailable(tmp_path) -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:////definitely-missing-dir/db.sqlite",
        user_service_url="http://user-service",
        transaction_service_url="http://transaction-service",
        http_backoff_seconds=0,
    )
    application = create_app(
        settings,
        user_service=FakeUserService(),
        transaction_service=FakeTransactionService(),
        clock=FixedClock(),
    )
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as value:
        response = await value.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    await application.state.engine.dispose()


async def test_daily_limit_via_api(client) -> None:
    assert (await create(client, key="daily-1", amount="5000.00")).status_code == 201
    assert (await create(client, key="daily-2", amount="4900.00")).status_code == 201
    response = await create(client, key="daily-3", amount="200.00")
    assert response.status_code == 422
    assert response.json()["code"] == "DAILY_LIMIT_EXCEEDED"


async def test_create_debits_wallet_and_exposes_movement(
    client, wallet_service
) -> None:
    before = wallet_service.wallet_for(15).balance
    response = await create(client, key="wallet-debit", amount="10.00")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["wallet_id"] == str(wallet_service.wallet_for(15).id)
    assert body["wallet_movement_id"]
    assert wallet_service.wallet_for(15).balance == before - 1000
    assert wallet_service.debit_calls == 1


async def test_wallet_replay_does_not_debit_twice(client, wallet_service) -> None:
    first = await create(client, key="wallet-replay", amount="10.00")
    after_first = wallet_service.wallet_for(15).balance
    second = await create(client, key="wallet-replay", amount="10.00")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert wallet_service.debit_calls == 1
    assert wallet_service.wallet_for(15).balance == after_first


async def test_insufficient_balance_creates_no_withdrawal(
    client, user_service, wallet_service
) -> None:
    user_service.set_account(id_usuario=16)
    response = await create(client, key="wallet-insufficient", amount="20.00")

    assert response.status_code == 422
    assert response.json()["code"] == "INSUFFICIENT_BALANCE"
    assert wallet_service.debit_calls == 0
    listing = await client.get("/api/v1/withdrawals", headers=headers())
    assert listing.json()["total"] == 0


async def test_missing_wallet_returns_404_and_no_withdrawal(
    client, user_service
) -> None:
    user_service.set_account(id_usuario=19)
    response = await create(client, key="wallet-missing", amount="10.00")

    assert response.status_code == 404
    assert response.json()["code"] == "WALLET_NOT_FOUND"
    listing = await client.get("/api/v1/withdrawals", headers=headers())
    assert listing.json()["total"] == 0


async def test_inactive_wallet_user_returns_422_and_no_withdrawal(
    client, user_service, wallet_service
) -> None:
    from withdrawal_soles.domain.exceptions import UserInactive

    user_service.user_error = UserInactive()
    response = await create(client, key="user-inactive", amount="10.00")

    assert response.status_code == 422
    assert response.json()["code"] == "USER_INACTIVE"
    assert wallet_service.get_calls == 0
    assert wallet_service.debit_calls == 0
    listing = await client.get("/api/v1/withdrawals", headers=headers())
    assert listing.json()["total"] == 0


async def test_unknown_wallet_user_returns_404_and_no_withdrawal(
    client, user_service, wallet_service
) -> None:
    from withdrawal_soles.domain.exceptions import UserNotFound

    user_service.user_error = UserNotFound()
    response = await create(client, key="user-missing", amount="10.00")

    assert response.status_code == 404
    assert response.json()["code"] == "USER_NOT_FOUND"
    assert wallet_service.debit_calls == 0
    listing = await client.get("/api/v1/withdrawals", headers=headers())
    assert listing.json()["total"] == 0


async def test_users_unavailable_returns_503_and_no_withdrawal(
    client, user_service, wallet_service
) -> None:
    from withdrawal_soles.domain.exceptions import DependencyUnavailable

    user_service.user_error = DependencyUnavailable("users-service")
    response = await create(client, key="users-down", amount="10.00")

    assert response.status_code == 503
    assert response.json()["code"] == "DEPENDENCY_UNAVAILABLE"
    assert wallet_service.debit_calls == 0
    listing = await client.get("/api/v1/withdrawals", headers=headers())
    assert listing.json()["total"] == 0


async def test_wallet_unavailable_creates_no_withdrawal(
    client, wallet_service
) -> None:
    from withdrawal_soles.domain.exceptions import DependencyUnavailable

    wallet_service.get_error = DependencyUnavailable("billetera")
    response = await create(client, key="wallet-down", amount="10.00")

    assert response.status_code == 503
    assert response.json()["code"] == "DEPENDENCY_UNAVAILABLE"
    listing = await client.get("/api/v1/withdrawals", headers=headers())
    assert listing.json()["total"] == 0


async def test_report_failure_keeps_debit_and_approved_status(
    client, transaction_service, wallet_service
) -> None:
    transaction_service.failures_remaining = 1
    before = wallet_service.wallet_for(15).balance
    response = await create(client, key="wallet-report-fail", amount="10.00")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["wallet_movement_id"]
    assert wallet_service.wallet_for(15).balance == before - 1000


async def test_reverse_restores_balance_and_is_rejected_twice(
    client, wallet_service
) -> None:
    created = await create(client, key="wallet-reverse", amount="10.00")
    assert created.status_code == 201
    after_debit = wallet_service.wallet_for(15).balance

    response = await client.post(
        f"/api/v1/withdrawals/{created.json()['id']}/reverse",
        json={"reason": "retiro anulado"},
        headers=headers(idempotency_key="wallet-reverse-1"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REVERSED"
    assert body["wallet_reversal_movement_id"]
    assert wallet_service.wallet_for(15).balance == after_debit + 1000

    second = await client.post(
        f"/api/v1/withdrawals/{created.json()['id']}/reverse",
        json={"reason": "retiro anulado"},
        headers=headers(idempotency_key="wallet-reverse-2"),
    )
    assert second.status_code == 422
    assert second.json()["code"] == "WALLET_ALREADY_REVERSED"


async def test_reverse_without_debit_returns_409(client, session) -> None:
    withdrawal = Withdrawal(
        id=uuid4(),
        account_id=OTHER_ACCOUNT_ID,
        user_id=USER_ID,
        amount=Decimal("100.00"),
        currency="PEN",
        status=WithdrawalStatus.COMPLETED,
        created_at=FixedClock().now(),
        updated_at=FixedClock().now(),
    )
    repository = SQLAlchemyWithdrawalRepository(session)
    await repository.add(withdrawal)
    await session.commit()

    response = await client.post(
        f"/api/v1/withdrawals/{withdrawal.id}/reverse",
        json={"reason": "retiro anulado"},
        headers=headers(idempotency_key="no-debit-reverse"),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATE"
