"""HTTP adapter for user-service ownership validation."""

from uuid import UUID

import httpx

from withdrawal_soles.core.settings import Settings
from withdrawal_soles.domain.exceptions import (
    AccountNotFound,
    AccountNotOwned,
    DependencyUnavailable,
    Unauthorized,
)
from withdrawal_soles.domain.models import AccountOwnership
from withdrawal_soles.infrastructure.http_retry import request_with_retries


class UserServiceClient:
    """Validate account ownership through the API gateway."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client or httpx.AsyncClient(
            base_url=settings.user_service_url,
            timeout=settings.user_service_timeout_seconds,
        )

    async def get_ownership(
        self, account_id: UUID, user_id: UUID
    ) -> AccountOwnership:
        try:
            response = await request_with_retries(
                self._client,
                "GET",
                f"/api/v1/accounts/{account_id}/ownership",
                max_attempts=self._settings.http_max_attempts,
                backoff_seconds=self._settings.http_backoff_seconds,
                headers={"X-User-Id": str(user_id)},
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise DependencyUnavailable(
                "user-service", "user-service did not respond in time."
            ) from error

        if response.status_code == 401:
            raise Unauthorized()
        if response.status_code == 403:
            raise AccountNotOwned()
        if response.status_code == 404:
            raise AccountNotFound()
        if response.status_code != 200:
            raise DependencyUnavailable(
                "user-service",
                f"user-service returned HTTP {response.status_code}.",
            )

        try:
            payload = response.json()
            return AccountOwnership(
                account_id=UUID(payload["account_id"]),
                owner_user_id=UUID(payload["owner_user_id"]),
                currency=str(payload["currency"]),
                status=str(payload["status"]),
                owned=bool(payload["owned"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise DependencyUnavailable(
                "user-service", "user-service returned an invalid payload."
            ) from error

    async def aclose(self) -> None:
        await self._client.aclose()
