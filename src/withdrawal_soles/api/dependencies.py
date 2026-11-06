"""FastAPI dependency wiring."""

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from withdrawal_soles.application.use_cases import (
    CancelWithdrawalUseCase,
    CreateWithdrawalUseCase,
    GetWithdrawalUseCase,
    ListWithdrawalsUseCase,
    RetryReportUseCase,
    ReverseWithdrawalUseCase,
)
from withdrawal_soles.domain.exceptions import Unauthorized
from withdrawal_soles.domain.ports import Clock, IdGenerator
from withdrawal_soles.domain.ports import (
    TransactionServicePort as TransactionService,
)
from withdrawal_soles.domain.ports import UserServicePort as UserService
from withdrawal_soles.domain.ports import WalletServicePort as WalletService
from withdrawal_soles.infrastructure.db.repository import (
    SQLAlchemyWithdrawalRepository,
)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Provide one transaction-scoped session per request."""

    session_factory = request.app.state.sessionmaker
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def require_user_id(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> UUID:
    """Trust only the gateway-injected identity header."""

    if not x_user_id:
        raise Unauthorized()
    try:
        return UUID(x_user_id)
    except ValueError as error:
        raise Unauthorized("The X-User-Id header is not a valid UUID.") from error


async def require_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    """Require a non-empty idempotency key on every mutation."""

    if not idempotency_key or not idempotency_key.strip():
        from withdrawal_soles.domain.exceptions import MissingIdempotencyKey

        raise MissingIdempotencyKey()
    return idempotency_key.strip()


def get_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SQLAlchemyWithdrawalRepository:
    return SQLAlchemyWithdrawalRepository(session)


def get_user_service(request: Request) -> UserService:
    return request.app.state.user_service


def get_transaction_service(request: Request) -> TransactionService:
    return request.app.state.transaction_service


def get_wallet_service(request: Request) -> WalletService:
    return request.app.state.wallet_service


def get_clock(request: Request) -> Clock:
    return request.app.state.clock


def get_ids(request: Request) -> IdGenerator:
    return request.app.state.ids


def get_create_use_case(
    repository: Annotated[SQLAlchemyWithdrawalRepository, Depends(get_repository)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    wallet_service: Annotated[WalletService, Depends(get_wallet_service)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdGenerator, Depends(get_ids)],
) -> CreateWithdrawalUseCase:
    return CreateWithdrawalUseCase(
        repository,
        user_service,
        transaction_service,
        wallet_service,
        clock,
        ids,
    )


def get_get_use_case(
    repository: Annotated[SQLAlchemyWithdrawalRepository, Depends(get_repository)],
) -> GetWithdrawalUseCase:
    return GetWithdrawalUseCase(repository)


def get_list_use_case(
    repository: Annotated[SQLAlchemyWithdrawalRepository, Depends(get_repository)],
) -> ListWithdrawalsUseCase:
    return ListWithdrawalsUseCase(repository)


def get_cancel_use_case(
    repository: Annotated[SQLAlchemyWithdrawalRepository, Depends(get_repository)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdGenerator, Depends(get_ids)],
) -> CancelWithdrawalUseCase:
    return CancelWithdrawalUseCase(repository, clock, ids)


def get_retry_report_use_case(
    repository: Annotated[SQLAlchemyWithdrawalRepository, Depends(get_repository)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdGenerator, Depends(get_ids)],
) -> RetryReportUseCase:
    return RetryReportUseCase(repository, transaction_service, clock, ids)


def get_reverse_use_case(
    repository: Annotated[SQLAlchemyWithdrawalRepository, Depends(get_repository)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    wallet_service: Annotated[WalletService, Depends(get_wallet_service)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdGenerator, Depends(get_ids)],
) -> ReverseWithdrawalUseCase:
    return ReverseWithdrawalUseCase(
        repository, user_service, wallet_service, clock, ids
    )


UserId = Annotated[UUID, Depends(require_user_id)]
IdempotencyKey = Annotated[str, Depends(require_idempotency_key)]
