"""Shared HTTP retry policy for external service adapters."""

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx


async def request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_attempts: int,
    backoff_seconds: float,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> httpx.Response:
    """Retry transport failures and 5xx responses with exponential backoff."""

    last_exception: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = await client.request(
                method, url, headers=headers, params=params, json=json
            )
        except (httpx.TimeoutException, httpx.TransportError) as error:
            last_exception = error
            if attempt == max_attempts:
                raise
        else:
            if response.status_code < 500 or attempt == max_attempts:
                return response
        await asyncio.sleep(backoff_seconds * (2 ** (attempt - 1)))

    if last_exception is not None:
        raise last_exception
    raise RuntimeError("HTTP retry loop exited without a response")
