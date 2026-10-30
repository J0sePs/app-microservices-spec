"""Withdrawal HTTP routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from withdrawal_soles.api.dependencies import (
    IdempotencyKey,
    UserId,
    get_cancel_use_case,
    get_create_use_case,
    get_get_use_case,
    get_list_use_case,
    get_retry_report_use_case,
)
from withdrawal_soles.api.schemas import (
    ErrorResponse,
    WithdrawalCreate,
    WithdrawalListResponse,
    WithdrawalResponse,
)
from withdrawal_soles.application.dto import CreateWithdrawalCommand
from withdrawal_soles.application.use_cases import (
    CancelWithdrawalUseCase,
    CreateWithdrawalUseCase,
    GetWithdrawalUseCase,
    ListWithdrawalsUseCase,
    RetryReportUseCase,
)
from withdrawal_soles.domain.enums import WithdrawalStatus

router = APIRouter(tags=["withdrawals"])

ERROR_RESPONSES = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


@router.post(
    "/api/v1/withdrawals",
    response_model=WithdrawalResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
async def create_withdrawal(
    payload: WithdrawalCreate,
    response: Response,
    user_id: UserId,
    idempotency_key: IdempotencyKey,
    use_case: Annotated[CreateWithdrawalUseCase, Depends(get_create_use_case)],
) -> WithdrawalResponse:
    result = await use_case.execute(
        CreateWithdrawalCommand(
            account_id=payload.account_id,
            amount=payload.amount,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )
    )
    if result.replayed:
        response.status_code = status.HTTP_200_OK
    return WithdrawalResponse.from_domain(result.withdrawal)


@router.get(
    "/api/v1/withdrawals",
    response_model=WithdrawalListResponse,
    responses=ERROR_RESPONSES,
)
async def list_withdrawals(
    user_id: UserId,
    use_case: Annotated[ListWithdrawalsUseCase, Depends(get_list_use_case)],
    account_id: Annotated[UUID | None, Query()] = None,
    withdrawal_status: Annotated[
        WithdrawalStatus | None, Query(alias="status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WithdrawalListResponse:
    page = await use_case.execute(
        user_id, account_id, withdrawal_status, limit, offset
    )
    return WithdrawalListResponse(
        items=[WithdrawalResponse.from_domain(item) for item in page.items],
        total=page.total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/api/v1/withdrawals/{withdrawal_id}",
    response_model=WithdrawalResponse,
    responses=ERROR_RESPONSES,
)
async def get_withdrawal(
    withdrawal_id: UUID,
    user_id: UserId,
    use_case: Annotated[GetWithdrawalUseCase, Depends(get_get_use_case)],
) -> WithdrawalResponse:
    withdrawal = await use_case.execute(withdrawal_id, user_id)
    return WithdrawalResponse.from_domain(withdrawal)


@router.post(
    "/api/v1/withdrawals/{withdrawal_id}/cancel",
    response_model=WithdrawalResponse,
    responses=ERROR_RESPONSES,
)
async def cancel_withdrawal(
    withdrawal_id: UUID,
    user_id: UserId,
    idempotency_key: IdempotencyKey,
    use_case: Annotated[CancelWithdrawalUseCase, Depends(get_cancel_use_case)],
) -> WithdrawalResponse:
    del idempotency_key
    withdrawal = await use_case.execute(withdrawal_id, user_id)
    return WithdrawalResponse.from_domain(withdrawal)


@router.post(
    "/api/v1/withdrawals/{withdrawal_id}/report",
    response_model=WithdrawalResponse,
    responses=ERROR_RESPONSES,
)
async def retry_report(
    withdrawal_id: UUID,
    response: Response,
    user_id: UserId,
    idempotency_key: IdempotencyKey,
    use_case: Annotated[RetryReportUseCase, Depends(get_retry_report_use_case)],
) -> WithdrawalResponse:
    del idempotency_key
    result = await use_case.execute(withdrawal_id, user_id)
    if not result.reported:
        response.status_code = status.HTTP_202_ACCEPTED
    return WithdrawalResponse.from_domain(result.withdrawal)
