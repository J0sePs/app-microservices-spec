"""HTTP adapter for user-service ownership and wallet-owner validation."""

from typing import Any
from uuid import UUID

import httpx

from withdrawal_soles.core.settings import Settings
from withdrawal_soles.domain.exceptions import (
    AccountNotFound,
    AccountNotOwned,
    DependencyUnavailable,
    Unauthorized,
    UserInactive,
    UserNotFound,
)
from withdrawal_soles.domain.models import AccountOwnership, UserIdentity
from withdrawal_soles.infrastructure.http_retry import request_with_retries
from withdrawal_soles.infrastructure.service_jwt import sign_service_token


class UserServiceClient:
    """Validate account ownership and the wallet owner through the users API."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
        users_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client or httpx.AsyncClient(
            base_url=settings.user_service_url,
            timeout=settings.user_service_timeout_seconds,
        )
        self._users_client = users_client or httpx.AsyncClient(
            base_url=settings.users_base_url,
            timeout=settings.users_service_timeout_seconds,
        )

    def _users_token(self) -> str:
        return sign_service_token(
            secret=self._settings.users_jwt_secret,
            issuer=self._settings.users_jwt_issuer,
            subject=self._settings.users_jwt_subject,
            ttl_seconds=self._settings.users_jwt_ttl_seconds,
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
            id_usuario = payload.get("id_usuario", payload.get("idUsuario"))
            return AccountOwnership(
                account_id=UUID(payload["account_id"]),
                owner_user_id=UUID(payload["owner_user_id"]),
                currency=str(payload["currency"]),
                status=str(payload["status"]),
                owned=bool(payload["owned"]),
                id_usuario=int(id_usuario) if id_usuario is not None else None,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise DependencyUnavailable(
                "user-service", "user-service returned an invalid payload."
            ) from error

    async def get_user(self, id_usuario: int) -> UserIdentity:
        """Apply the published `GET /usuarios/{idUsuario}` contract."""

        try:
            response = await request_with_retries(
                self._users_client,
                "GET",
                f"/usuarios/{id_usuario}",
                max_attempts=1,
                backoff_seconds=0,
                headers={
                    "Authorization": f"Bearer {self._users_token()}",
                    "Accept": "application/json",
                },
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise DependencyUnavailable(
                "users-service", "El servicio de usuarios no responde."
            ) from error

        if response.status_code == 404:
            raise UserNotFound()
        if response.status_code != 200:
            raise DependencyUnavailable(
                "users-service", "El servicio de usuarios no responde."
            )

        payload = _json_object(response)
        body_id = payload.get("idUsuario", payload.get("id_usuario"))
        try:
            matches = int(body_id) == int(id_usuario)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            matches = False
        if not matches:
            raise UserNotFound()

        if payload.get("estado") is not True:
            raise UserInactive()

        return UserIdentity(id_usuario=int(id_usuario), active=True)

    async def aclose(self) -> None:
        await self._client.aclose()
        await self._users_client.aclose()


def _json_object(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as error:
        raise DependencyUnavailable(
            "users-service", "El servicio de usuarios devolvió una respuesta inválida."
        ) from error
    if not isinstance(payload, dict):
        raise DependencyUnavailable(
            "users-service", "El servicio de usuarios devolvió una respuesta inválida."
        )
    return payload
