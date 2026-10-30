"""Application use cases."""

from datetime import datetime
from uuid import UUID, uuid4

from withdrawal_soles.application.dto import (
    CreateWithdrawalCommand,
    CreateWithdrawalResult,
    RetryReportResult,
)
from withdrawal_soles.application.serializers import serialize_withdrawal
from withdrawal_soles.domain.enums import (
    COUNTED_DAILY_STATUSES,
    ReportStatus,
    WithdrawalStatus,
)
from withdrawal_soles.domain.exceptions import (
    AccountNotEligible,
    AccountNotOwned,
    IdempotencyConflict,
    IdempotencyInProgress,
    InvalidState,
    ReportingError,
    WithdrawalNotFound,
)
from withdrawal_soles.domain.models import (
    IdempotencyRecord,
    ReportingAttempt,
    StatusChange,
    Withdrawal,
    WithdrawalPage,
)
from withdrawal_soles.domain.ports import (
    Clock,
    IdGenerator,
    TransactionServicePort,
    UserServicePort,
    WithdrawalRepository,
)
from withdrawal_soles.domain.rules import (
    CURRENCY,
    ensure_daily_limit,
    request_fingerprint,
    validate_amount,
)


class CreateWithdrawalUseCase:
    """Create, approve, and report a PEN withdrawal."""

    def __init__(
        self,
        repository: WithdrawalRepository,
        user_service: UserServicePort,
        transaction_service: TransactionServicePort,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._repository = repository
        self._user_service = user_service
        self._transaction_service = transaction_service
        self._clock = clock
        self._ids = ids

    async def execute(
        self, command: CreateWithdrawalCommand
    ) -> CreateWithdrawalResult:
        key = command.idempotency_key.strip()
        fingerprint = request_fingerprint(
            command.account_id, command.user_id, command.amount
        )

        existing = await self._repository.get_idempotency(key)
        if existing is not None:
            if existing.request_hash != fingerprint:
                raise IdempotencyConflict()
            if existing.response_snapshot is None:
                raise IdempotencyInProgress()
            current = await self._repository.get(existing.withdrawal_id)
            if current is None:
                raise IdempotencyConflict()
            return CreateWithdrawalResult(withdrawal=current, replayed=True)

        amount = validate_amount(command.amount)
        ownership = await self._user_service.get_ownership(
            command.account_id, command.user_id
        )
        if not ownership.owned:
            raise AccountNotOwned()
        if ownership.currency != CURRENCY:
            raise AccountNotEligible("The account currency must be PEN.")
        if ownership.status != "ACTIVE":
            raise AccountNotEligible("The account must be ACTIVE.")

        await self._repository.acquire_account_lock(command.account_id)
        start, end = self._clock.day_bounds()
        accumulated = await self._repository.daily_total(
            command.account_id, start, end, COUNTED_DAILY_STATUSES
        )
        ensure_daily_limit(accumulated, amount)

        now = self._clock.now()
        withdrawal = Withdrawal(
            id=self._ids.new_id(),
            account_id=command.account_id,
            user_id=command.user_id,
            amount=amount,
            currency=CURRENCY,
            status=WithdrawalStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        await self._repository.add(withdrawal)
        await self._record(
            withdrawal.id,
            None,
            WithdrawalStatus.PENDING,
            "created",
            now,
        )

        previous = withdrawal.transition_to(WithdrawalStatus.APPROVED, self._clock.now())
        await self._record(
            withdrawal.id,
            previous,
            withdrawal.status,
            "ownership and limits validated",
            withdrawal.updated_at,
        )

        await self._report(withdrawal, required=False)
        await self._repository.save(withdrawal)

        await self._repository.save_idempotency(
            IdempotencyRecord(
                id=self._ids.new_id(),
                key=key,
                request_hash=fingerprint,
                withdrawal_id=withdrawal.id,
                response_snapshot=serialize_withdrawal(withdrawal),
                created_at=self._clock.now(),
            )
        )
        return CreateWithdrawalResult(withdrawal=withdrawal, replayed=False)

    async def _report(self, withdrawal: Withdrawal, *, required: bool) -> bool:
        try:
            transaction_id = await self._transaction_service.report(withdrawal)
        except ReportingError as error:
            attempt_number = await self._repository.next_report_attempt_number(
                withdrawal.id
            )
            await self._repository.add_reporting_attempt(
                ReportingAttempt(
                    id=self._ids.new_id(),
                    withdrawal_id=withdrawal.id,
                    attempt_number=attempt_number,
                    status=ReportStatus.FAILED,
                    transaction_id=None,
                    error_message=error.message,
                    created_at=self._clock.now(),
                )
            )
            if required:
                raise
            return False

        previous = withdrawal.transition_to(
            WithdrawalStatus.COMPLETED, self._clock.now()
        )
        withdrawal.transaction_id = transaction_id
        await self._repository.add_reporting_attempt(
            ReportingAttempt(
                id=self._ids.new_id(),
                withdrawal_id=withdrawal.id,
                attempt_number=await self._repository.next_report_attempt_number(
                    withdrawal.id
                ),
                status=ReportStatus.SENT,
                transaction_id=transaction_id,
                error_message=None,
                created_at=self._clock.now(),
            )
        )
        await self._record(
            withdrawal.id,
            previous,
            withdrawal.status,
            "transaction reported",
            withdrawal.updated_at,
        )
        return True

    async def _record(
        self,
        withdrawal_id: UUID,
        previous: WithdrawalStatus | None,
        current: WithdrawalStatus,
        reason: str,
        at: datetime,
    ) -> None:
        await self._repository.add_status_change(
            StatusChange(
                id=self._ids.new_id(),
                withdrawal_id=withdrawal_id,
                from_status=previous,
                to_status=current,
                reason=reason,
                created_at=at,
            )
        )


class GetWithdrawalUseCase:
    """Read one withdrawal owned by the caller."""

    def __init__(self, repository: WithdrawalRepository) -> None:
        self._repository = repository

    async def execute(self, withdrawal_id: UUID, user_id: UUID) -> Withdrawal:
        withdrawal = await self._repository.get(withdrawal_id)
        if withdrawal is None or withdrawal.user_id != user_id:
            raise WithdrawalNotFound()
        return withdrawal


class ListWithdrawalsUseCase:
    """List withdrawals owned by the caller."""

    def __init__(self, repository: WithdrawalRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        user_id: UUID,
        account_id: UUID | None,
        status: WithdrawalStatus | None,
        limit: int,
        offset: int,
    ) -> WithdrawalPage:
        return await self._repository.list_for_user(
            user_id, account_id, status, limit, offset
        )


class CancelWithdrawalUseCase:
    """Cancel a pending withdrawal; rejections are naturally idempotent."""

    def __init__(
        self,
        repository: WithdrawalRepository,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._ids = ids

    async def execute(self, withdrawal_id: UUID, user_id: UUID) -> Withdrawal:
        withdrawal = await self._repository.get(withdrawal_id)
        if withdrawal is None or withdrawal.user_id != user_id:
            raise WithdrawalNotFound()
        if withdrawal.status == WithdrawalStatus.REJECTED:
            return withdrawal
        if withdrawal.status != WithdrawalStatus.PENDING:
            raise InvalidState(withdrawal.status.value, WithdrawalStatus.REJECTED.value)

        previous = withdrawal.transition_to(
            WithdrawalStatus.REJECTED, self._clock.now()
        )
        await self._repository.save(withdrawal)
        await self._repository.add_status_change(
            StatusChange(
                id=self._ids.new_id(),
                withdrawal_id=withdrawal.id,
                from_status=previous,
                to_status=withdrawal.status,
                reason="cancelled by owner",
                created_at=withdrawal.updated_at,
            )
        )
        return withdrawal


class RetryReportUseCase:
    """Retry ledger reporting for an approved withdrawal."""

    def __init__(
        self,
        repository: WithdrawalRepository,
        transaction_service: TransactionServicePort,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._repository = repository
        self._transaction_service = transaction_service
        self._clock = clock
        self._ids = ids

    async def execute(
        self, withdrawal_id: UUID, user_id: UUID
    ) -> RetryReportResult:
        withdrawal = await self._repository.get(withdrawal_id)
        if withdrawal is None or withdrawal.user_id != user_id:
            raise WithdrawalNotFound()
        if withdrawal.status == WithdrawalStatus.COMPLETED:
            return RetryReportResult(withdrawal=withdrawal, reported=True)
        if withdrawal.status != WithdrawalStatus.APPROVED:
            raise InvalidState(withdrawal.status.value, WithdrawalStatus.APPROVED.value)

        attempt_number = await self._repository.next_report_attempt_number(
            withdrawal.id
        )
        try:
            transaction_id = await self._transaction_service.report(withdrawal)
        except ReportingError as error:
            await self._repository.add_reporting_attempt(
                ReportingAttempt(
                    id=self._ids.new_id(),
                    withdrawal_id=withdrawal.id,
                    attempt_number=attempt_number,
                    status=ReportStatus.FAILED,
                    transaction_id=None,
                    error_message=error.message,
                    created_at=self._clock.now(),
                )
            )
            return RetryReportResult(withdrawal=withdrawal, reported=False)

        previous = withdrawal.transition_to(
            WithdrawalStatus.COMPLETED, self._clock.now()
        )
        withdrawal.transaction_id = transaction_id
        await self._repository.save(withdrawal)
        await self._repository.add_status_change(
            StatusChange(
                id=self._ids.new_id(),
                withdrawal_id=withdrawal.id,
                from_status=previous,
                to_status=withdrawal.status,
                reason="transaction reported after retry",
                created_at=withdrawal.updated_at,
            )
        )
        await self._repository.add_reporting_attempt(
            ReportingAttempt(
                id=self._ids.new_id(),
                withdrawal_id=withdrawal.id,
                attempt_number=attempt_number,
                status=ReportStatus.SENT,
                transaction_id=transaction_id,
                error_message=None,
                created_at=self._clock.now(),
            )
        )
        return RetryReportResult(withdrawal=withdrawal, reported=True)


def new_uuid() -> UUID:
    """Default identifier source used by the API wiring."""

    return uuid4()
