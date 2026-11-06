"""HTTP adapter for the PEN wallet balance owner."""

import time
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
import jwt

from withdrawal_soles.core.settings import Settings
from withdrawal_soles.domain.exceptions import (
    DependencyUnavailable,
    InsufficientBalance,
    WalletAlreadyReversed,
    WalletAuthFailed,
    WalletConflict,
    WalletNotFound,
    WalletRejected,
    WalletUserInactive,
)
from withdrawal_soles.domain.models import WalletBalance, WalletMovement
from withdrawal_soles.infrastructure.http_retry import request_with_retries


class WalletServiceClient:
    """Consume the wallet contract published by the wallet team."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client or httpx.AsyncClient(
            base_url=settings.wallet_service_url,
            timeout=settings.wallet_service_timeout_seconds,
        )

    def _token(self) -> str:
        issued_at = int(time.time())
        claims = {
            "sub": self._settings.wallet_jwt_subject,
            "iss": self._settings.wallet_jwt_issuer,
            "iat": issued_at,
            "exp": issued_at + self._settings.wallet_jwt_ttl_seconds,
            "jti": str(uuid4()),
        }
        return jwt.encode(
            claims,
            self._settings.wallet_jwt_secret,
            algorithm="HS256",
        )

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._token()}",
            "Accept": "application/json",
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        idempotency_key: str | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        try:
            return await request_with_retries(
                self._client,
                method,
                path,
                max_attempts=self._settings.http_max_attempts,
                backoff_seconds=self._settings.http_backoff_seconds,
                headers=self._headers(idempotency_key),
                params=params,
                json=json,
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            raise DependencyUnavailable(
                "billetera", "The wallet did not respond in time."
            ) from error

    async def get_wallet(self, id_usuario: int) -> WalletBalance:
        response = await self._request(
            "GET", "/v1/wallets", params={"idUsuario": id_usuario}
        )
        self._raise_for_wallet_error(response)
        try:
            payload = response.json()
            return WalletBalance(
                id=UUID(str(payload["id"])),
                id_usuario=int(payload["idUsuario"]),
                currency=str(payload["currency"]),
                balance=int(payload["balance"]),
                created_at=_parse_datetime(payload.get("createdAt")),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise DependencyUnavailable(
                "billetera", "The wallet returned an invalid wallet payload."
            ) from error

    async def debit(
        self,
        wallet_id: UUID,
        amount_cents: int,
        external_reference: str,
        idempotency_key: str,
    ) -> WalletMovement:
        response = await self._request(
            "POST",
            f"/v1/wallets/{wallet_id}/payments",
            idempotency_key=idempotency_key,
            json={
                "amount": int(amount_cents),
                "currency": "PEN",
                "externalReference": external_reference,
            },
        )
        self._raise_for_wallet_error(response, operation="payment")
        if response.status_code not in {200, 201}:
            raise DependencyUnavailable(
                "billetera",
                f"The wallet returned HTTP {response.status_code} for the payment.",
            )
        return _parse_movement(response)

    async def reverse(
        self,
        movement_id: UUID,
        reason: str,
        idempotency_key: str,
    ) -> WalletMovement:
        response = await self._request(
            "POST",
            f"/v1/movements/{movement_id}/reverse",
            idempotency_key=idempotency_key,
            json={"reason": reason},
        )
        self._raise_for_wallet_error(response, operation="reversal")
        if response.status_code not in {200, 201}:
            raise DependencyUnavailable(
                "billetera",
                f"The wallet returned HTTP {response.status_code} for the reversal.",
            )
        return _parse_reversal(response)

    def _raise_for_wallet_error(
        self, response: httpx.Response, *, operation: str | None = None
    ) -> None:
        status = response.status_code
        detail = _detail(response)

        if status in {401, 403}:
            raise WalletAuthFailed()
        if status == 404:
            raise WalletNotFound()
        if status == 409:
            raise WalletConflict(detail or "The wallet reported a conflict.")
        if status == 422:
            lowered = detail.lower()
            if "saldo" in lowered or "balance" in lowered:
                raise InsufficientBalance()
            if "activo" in lowered or "inactive" in lowered:
                raise WalletUserInactive()
            if "revers" in lowered:
                raise WalletAlreadyReversed()
            raise WalletRejected(detail or "The wallet rejected the operation.")
        if status in {200, 201}:
            return
        if operation is not None and status >= 500:
            raise DependencyUnavailable(
                "billetera",
                f"The wallet returned HTTP {status} for the {operation}.",
            )
        raise DependencyUnavailable(
            "billetera", f"The wallet returned HTTP {status}."
        )

    async def aclose(self) -> None:
        await self._client.aclose()


def _detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
        title = payload.get("title")
        if isinstance(title, str):
            return title
    return ""


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_movement(response: httpx.Response) -> WalletMovement:
    try:
        payload = response.json()
        return WalletMovement(
            id=UUID(str(payload["id"])),
            wallet_id=UUID(str(payload["walletId"])),
            amount=int(payload["amount"]),
            currency=str(payload["currency"]),
            direction=str(payload["direction"]),
            type=str(payload["type"]),
            external_reference=_optional_str(payload.get("externalReference")),
            reversal_of=_optional_uuid(payload.get("reversalOf")),
            created_at=_parse_datetime(payload.get("createdAt")),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise DependencyUnavailable(
            "billetera", "The wallet returned an invalid payment payload."
        ) from error


def _parse_reversal(response: httpx.Response) -> WalletMovement:
    try:
        payload = response.json()
        movements = payload.get("movements") if isinstance(payload, dict) else None
        movement = movements[0] if isinstance(movements, list) and movements else payload
        return WalletMovement(
            id=UUID(str(movement["id"])),
            wallet_id=UUID(str(movement["walletId"])),
            amount=int(movement["amount"]),
            currency=str(movement["currency"]),
            direction=str(movement["direction"]),
            type=str(movement["type"]),
            external_reference=_optional_str(movement.get("externalReference")),
            reversal_of=_optional_uuid(movement.get("reversalOf")),
            created_at=_parse_datetime(movement.get("createdAt")),
        )
    except (KeyError, TypeError, ValueError, IndexError) as error:
        raise DependencyUnavailable(
            "billetera", "The wallet returned an invalid reversal payload."
        ) from error


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None


def _optional_uuid(value: Any) -> UUID | None:
    return UUID(str(value)) if value is not None else None
