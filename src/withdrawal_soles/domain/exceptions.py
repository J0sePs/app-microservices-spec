"""Domain exceptions mapped to HTTP responses by the API layer."""

from typing import Any


class DomainError(Exception):
    """Base error with a stable code and HTTP status."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class Unauthorized(DomainError):
    def __init__(self, message: str = "Missing or invalid identity.") -> None:
        super().__init__("UNAUTHORIZED", message, 401)


class MissingIdempotencyKey(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "MISSING_IDEMPOTENCY_KEY",
            "The Idempotency-Key header is required.",
            422,
        )


class InvalidAmount(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_AMOUNT", message, 422)


class DailyLimitExceeded(DomainError):
    def __init__(self, accumulated: str, requested: str, limit: str) -> None:
        super().__init__(
            "DAILY_LIMIT_EXCEEDED",
            "The daily withdrawal limit was exceeded.",
            422,
            {"accumulated": accumulated, "requested": requested, "limit": limit},
        )


class AccountNotOwned(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "ACCOUNT_NOT_OWNED",
            "The account does not belong to the authenticated user.",
            403,
        )


class AccountNotFound(DomainError):
    def __init__(self) -> None:
        super().__init__("ACCOUNT_NOT_FOUND", "The account was not found.", 404)


class AccountNotEligible(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__("ACCOUNT_NOT_ELIGIBLE", message, 422)


class IdempotencyConflict(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "IDEMPOTENCY_CONFLICT",
            "The Idempotency-Key was already used with a different request.",
            409,
        )


class IdempotencyInProgress(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "IDEMPOTENCY_IN_PROGRESS",
            "A request with this Idempotency-Key is still in progress.",
            409,
        )


class WithdrawalNotFound(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "WITHDRAWAL_NOT_FOUND", "The withdrawal was not found.", 404
        )


class InvalidState(DomainError):
    def __init__(self, current: str, requested: str) -> None:
        super().__init__(
            "INVALID_STATE",
            f"Cannot transition a withdrawal from {current} to {requested}.",
            409,
            {"current": current, "requested": requested},
        )


class DependencyUnavailable(DomainError):
    def __init__(self, service: str, message: str | None = None) -> None:
        super().__init__(
            "DEPENDENCY_UNAVAILABLE",
            message or f"{service} is unavailable.",
            503,
            {"service": service},
        )


class ReportingError(DomainError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("REPORTING_FAILED", message, 502, details)


class UserNotFound(DomainError):
    def __init__(self) -> None:
        super().__init__("USER_NOT_FOUND", "El usuario no existe.", 404)


class UserInactive(DomainError):
    def __init__(self) -> None:
        super().__init__("USER_INACTIVE", "El usuario no está activo.", 422)


class WalletNotFound(DomainError):
    def __init__(self) -> None:
        super().__init__("WALLET_NOT_FOUND", "The wallet was not found.", 404)


class InsufficientBalance(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "INSUFFICIENT_BALANCE",
            "The wallet balance is lower than the withdrawal amount.",
            422,
        )


class WalletUserInactive(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "USER_INACTIVE",
            "The wallet owner is not active.",
            422,
        )


class WalletConflict(DomainError):
    def __init__(self, message: str = "The wallet rejected a duplicate reference.") -> None:
        super().__init__("WALLET_CONFLICT", message, 409)


class WalletAuthFailed(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "WALLET_AUTH_FAILED",
            "The wallet rejected the service credentials.",
            503,
        )


class WalletAlreadyReversed(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "WALLET_ALREADY_REVERSED",
            "The wallet movement was already reversed.",
            422,
        )


class WalletRejected(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__("WALLET_REJECTED", message, 422)
