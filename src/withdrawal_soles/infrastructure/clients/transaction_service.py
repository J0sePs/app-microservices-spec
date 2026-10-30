"""HTTP adapter for transaction-service ledger reporting."""

import httpx

from withdrawal_soles.core.settings import Settings
from withdrawal_soles.domain.exceptions import ReportingError
from withdrawal_soles.domain.models import Withdrawal
from withdrawal_soles.infrastructure.http_retry import request_with_retries


class TransactionServiceClient:
    """Report approved withdrawals through the API gateway."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client or httpx.AsyncClient(
            base_url=settings.transaction_service_url,
            timeout=settings.transaction_service_timeout_seconds,
        )

    async def report(self, withdrawal: Withdrawal) -> str:
        payload = {
            "source_service": "withdrawal-soles",
            "source_operation_id": str(withdrawal.id),
            "account_id": str(withdrawal.account_id),
            "type": "WITHDRAWAL",
            "amount": f"{withdrawal.amount:.2f}",
            "currency": withdrawal.currency,
            "status": "POSTED",
            "occurred_at": withdrawal.updated_at.isoformat(),
        }
        try:
            response = await request_with_retries(
                self._client,
                "POST",
                "/api/v1/transactions",
                max_attempts=self._settings.http_max_attempts,
                backoff_seconds=self._settings.http_backoff_seconds,
                headers={
                    "X-User-Id": str(withdrawal.user_id),
                    "Idempotency-Key": str(withdrawal.id),
                },
                json=payload,
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise ReportingError(
                "transaction-service did not respond in time."
            ) from error

        if response.status_code in {200, 201}:
            try:
                transaction_id = response.json()["transaction_id"]
            except (KeyError, TypeError, ValueError) as error:
                raise ReportingError(
                    "transaction-service returned an invalid payload."
                ) from error
            return str(transaction_id)

        raise ReportingError(
            "transaction-service rejected the report.",
            {"status": response.status_code},
        )

    async def aclose(self) -> None:
        await self._client.aclose()
