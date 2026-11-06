"""Application use case tests with real persistence and fake ports."""

from decimal import Decimal

import pytest

from tests.conftest import ACCOUNT_ID, USER_ID, FakeTransactionService
from withdrawal_soles.application.dto import CreateWithdrawalCommand
from withdrawal_soles.application.use_cases import (
    CreateWithdrawalUseCase,
    RetryReportUseCase,
)
from withdrawal_soles.domain.enums import WithdrawalStatus
from withdrawal_soles.domain.exceptions import AccountNotOwned, DailyLimitExceeded
from withdrawal_soles.infrastructure.db.repository import (
    SQLAlchemyWithdrawalRepository,
)


def make_use_case(app, session, user_service, transaction_service, wallet_service):
    return CreateWithdrawalUseCase(
        repository=SQLAlchemyWithdrawalRepository(session),
        user_service=user_service,
        transaction_service=transaction_service,
        wallet_service=wallet_service,
        clock=app.state.clock,
        ids=app.state.ids,
    )


async def test_create_withdrawal_completes_and_reports(
    app, session, user_service, transaction_service, wallet_service
) -> None:
    use_case = make_use_case(
        app, session, user_service, transaction_service, wallet_service
    )
    result = await use_case.execute(
        CreateWithdrawalCommand(
            account_id=ACCOUNT_ID,
            amount=Decimal("250.00"),
            user_id=USER_ID,
            idempotency_key="app-1",
        )
    )
    await session.commit()

    assert result.replayed is False
    assert result.withdrawal.status == WithdrawalStatus.COMPLETED
    assert result.withdrawal.transaction_id == f"tx-{result.withdrawal.id}"
    assert result.withdrawal.wallet_movement_id is not None
    assert len(transaction_service.reported) == 1


async def test_create_withdrawal_rejects_non_owned_account(
    app, session, user_service, transaction_service, wallet_service
) -> None:
    user_service.set_account(owned=False)
    use_case = make_use_case(
        app, session, user_service, transaction_service, wallet_service
    )

    with pytest.raises(AccountNotOwned):
        await use_case.execute(
            CreateWithdrawalCommand(
                account_id=ACCOUNT_ID,
                amount=Decimal("250.00"),
                user_id=USER_ID,
                idempotency_key="app-2",
            )
        )


async def test_create_withdrawal_enforces_daily_limit(
    app, session, user_service, transaction_service, wallet_service
) -> None:
    use_case = make_use_case(
        app, session, user_service, transaction_service, wallet_service
    )
    for key, amount in (("limit-1", "5000.00"), ("limit-2", "4900.00")):
        await use_case.execute(
            CreateWithdrawalCommand(
                account_id=ACCOUNT_ID,
                amount=Decimal(amount),
                user_id=USER_ID,
                idempotency_key=key,
            )
        )

    with pytest.raises(DailyLimitExceeded):
        await use_case.execute(
            CreateWithdrawalCommand(
                account_id=ACCOUNT_ID,
                amount=Decimal("200.00"),
                user_id=USER_ID,
                idempotency_key="limit-3",
            )
        )


async def test_report_failure_leaves_withdrawal_approved_and_retry_completes(
    app, session, user_service, transaction_service, wallet_service
) -> None:
    assert isinstance(transaction_service, FakeTransactionService)
    transaction_service.failures_remaining = 1
    create = make_use_case(
        app, session, user_service, transaction_service, wallet_service
    )
    result = await create.execute(
        CreateWithdrawalCommand(
            account_id=ACCOUNT_ID,
            amount=Decimal("250.00"),
            user_id=USER_ID,
            idempotency_key="retry-1",
        )
    )
    assert result.withdrawal.status == WithdrawalStatus.APPROVED

    retry = RetryReportUseCase(
        repository=SQLAlchemyWithdrawalRepository(session),
        transaction_service=transaction_service,
        clock=app.state.clock,
        ids=app.state.ids,
    )
    retried = await retry.execute(result.withdrawal.id, USER_ID)
    await session.commit()

    assert retried.reported is True
    assert retried.withdrawal.status == WithdrawalStatus.COMPLETED


async def test_report_retry_failure_keeps_withdrawal_approved(
    app, session, user_service, transaction_service, wallet_service
) -> None:
    assert isinstance(transaction_service, FakeTransactionService)
    transaction_service.failures_remaining = 2
    create = make_use_case(
        app, session, user_service, transaction_service, wallet_service
    )
    result = await create.execute(
        CreateWithdrawalCommand(
            account_id=ACCOUNT_ID,
            amount=Decimal("250.00"),
            user_id=USER_ID,
            idempotency_key="retry-fails-1",
        )
    )
    assert result.withdrawal.status == WithdrawalStatus.APPROVED

    retry = RetryReportUseCase(
        repository=SQLAlchemyWithdrawalRepository(session),
        transaction_service=transaction_service,
        clock=app.state.clock,
        ids=app.state.ids,
    )
    retried = await retry.execute(result.withdrawal.id, USER_ID)
    await session.commit()

    assert retried.reported is False
    assert retried.withdrawal.status == WithdrawalStatus.APPROVED


async def test_idempotency_replay_returns_same_operation(
    app, session, user_service, transaction_service, wallet_service
) -> None:
    use_case = make_use_case(
        app, session, user_service, transaction_service, wallet_service
    )
    command = CreateWithdrawalCommand(
        account_id=ACCOUNT_ID,
        amount=Decimal("250.00"),
        user_id=USER_ID,
        idempotency_key="replay-1",
    )
    first = await use_case.execute(command)
    second = await use_case.execute(command)
    await session.commit()

    assert second.replayed is True
    assert second.withdrawal.id == first.withdrawal.id
    assert transaction_service.calls == 1
