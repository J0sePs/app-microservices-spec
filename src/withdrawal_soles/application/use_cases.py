"""Application use cases."""

import logging
from datetime import datetime
from decimal import Decimal
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
    DependencyUnavailable,
    IdempotencyConflict,
    IdempotencyInProgress,
    InsufficientBalance,
    InvalidState,
    ReportingError,
    UserInactive,
    WalletAlreadyReversed,
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
    WalletServicePort,
    WithdrawalRepository,
)
from withdrawal_soles.domain.rules import (
    CURRENCY,
    amount_to_cents,
    ensure_daily_limit,
    request_fingerprint,
    validate_amount,
)

logger = logging.getLogger(__name__)


class CreateWithdrawalUseCase:
    """Create, approve, and report a PEN withdrawal."""

    def __init__(
        self,
        repository: WithdrawalRepository,
        user_service: UserServicePort,
        transaction_service: TransactionServicePort,
        wallet_service: WalletServicePort,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._repository = repository
        self._user_service = user_service
        self._transaction_service = transaction_service
        self._wallet_service = wallet_service
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
        if ownership.id_usuario is None:
            raise DependencyUnavailable(
                "user-service",
                "user-service did not return the wallet id_usuario.",
            )

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

        await self._debit_wallet(withdrawal, ownership.id_usuario, amount)

        try:
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
        except Exception:
            await self._compensate(withdrawal)
            raise

        return CreateWithdrawalResult(withdrawal=withdrawal, replayed=False)

    async def _debit_wallet(
        self,
        withdrawal: Withdrawal,
        id_usuario: int,
        amount: Decimal,
    ) -> None:
        """Debit the exact amount before the operation is reported."""

        user = await self._user_service.get_user(id_usuario)
        if not user.active:
            raise UserInactive()
        wallet = await self._wallet_service.get_wallet(id_usuario)
        amount_cents = amount_to_cents(amount)
        if wallet.balance < amount_cents:
            raise InsufficientBalance()
        movement = await self._wallet_service.debit(
            wallet_id=wallet.id,
            amount_cents=amount_cents,
            external_reference=str(withdrawal.id),
            idempotency_key=str(withdrawal.id),
        )
        withdrawal.wallet_user_id = wallet.id_usuario
        withdrawal.wallet_id = wallet.id
        withdrawal.wallet_movement_id = movement.id
        withdrawal.wallet_debited_at = self._clock.now()

    async def _compensate(self, withdrawal: Withdrawal) -> None:
        """Best-effort reversal when the local write fails after a debit."""

        if withdrawal.wallet_movement_id is None:
            return
        try:
            await self._wallet_service.reverse(
                withdrawal.wallet_movement_id,
                "local persistence failure",
                f"{withdrawal.id}:reverse",
            )
        except Exception:
            logger.exception(
                "Wallet compensation failed for withdrawal %s", withdrawal.id
            )

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


class ReverseWithdrawalUseCase:
    """Reverse the full wallet debit of an annulled withdrawal."""

    def __init__(
        self,
        repository: WithdrawalRepository,
        user_service: UserServicePort,
        wallet_service: WalletServicePort,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._repository = repository
        self._user_service = user_service
        self._wallet_service = wallet_service
        self._clock = clock
        self._ids = ids

    async def execute(
        self, withdrawal_id: UUID, user_id: UUID, reason: str
    ) -> Withdrawal:
        withdrawal = await self._repository.get(withdrawal_id)
        if withdrawal is None or withdrawal.user_id != user_id:
            raise WithdrawalNotFound()
        if (
            withdrawal.status == WithdrawalStatus.REVERSED
            or withdrawal.wallet_reversal_movement_id is not None
        ):
            raise WalletAlreadyReversed()
        if withdrawal.wallet_movement_id is None:
            raise InvalidState(
                withdrawal.status.value, WithdrawalStatus.REVERSED.value
            )

        if withdrawal.wallet_user_id is not None:
            user = await self._user_service.get_user(withdrawal.wallet_user_id)
            if not user.active:
                raise UserInactive()

        movement = await self._wallet_service.reverse(
            withdrawal.wallet_movement_id,
            reason,
            f"{withdrawal.id}:reverse",
        )

        previous = withdrawal.transition_to(
            WithdrawalStatus.REVERSED, self._clock.now()
        )
        withdrawal.wallet_reversal_movement_id = movement.id
        withdrawal.wallet_reversed_at = self._clock.now()
        await self._repository.save(withdrawal)
        await self._repository.add_status_change(
            StatusChange(
                id=self._ids.new_id(),
                withdrawal_id=withdrawal.id,
                from_status=previous,
                to_status=withdrawal.status,
                reason=reason,
                created_at=withdrawal.updated_at,
            )
        )
        return withdrawal


def new_uuid() -> UUID:
    """Default identifier source used by the API wiring."""

    return uuid4()
