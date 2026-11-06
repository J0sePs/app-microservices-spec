"""Signing helpers for the platform service tokens."""

import time
from uuid import uuid4

import jwt


def sign_service_token(
    *,
    secret: str,
    issuer: str,
    subject: str,
    ttl_seconds: int,
) -> str:
    """Create an HS256 token with the agreed platform claims."""

    issued_at = int(time.time())
    claims = {
        "sub": subject,
        "iss": issuer,
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
        "jti": str(uuid4()),
    }
    return jwt.encode(claims, secret, algorithm="HS256")
