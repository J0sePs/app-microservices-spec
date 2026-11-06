"""Inbound service-token authentication."""

from typing import Annotated, Any

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from withdrawal_soles.core.settings import Settings
from withdrawal_soles.domain.exceptions import Unauthorized

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description=(
        "Service JWT signed with HS256, issuer `billetera-dev`, and subject "
        "`retiros`. The token authenticates the caller; the end-user identity "
        "still travels in `X-User-Id`."
    ),
)


def decode_service_token(settings: Settings, token: str) -> dict[str, Any]:
    """Validate the service token and return its claims."""

    try:
        claims = jwt.decode(
            token,
            settings.auth_jwt_secret,
            algorithms=settings.auth_jwt_algorithm_list,
            issuer=settings.auth_jwt_issuer,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as error:
        raise Unauthorized("The service token is missing or invalid.") from error

    allowed_subjects = settings.auth_jwt_subject_set
    if allowed_subjects and claims.get("sub") not in allowed_subjects:
        raise Unauthorized("The service token subject is not allowed.")

    return claims


async def require_service_token(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> dict[str, Any]:
    """Require a valid bearer token on every business route."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise Unauthorized("The Authorization Bearer token is required.")

    settings: Settings = request.app.state.settings
    return decode_service_token(settings, credentials.credentials)


ServiceClaims = Annotated[dict[str, Any], Depends(require_service_token)]
