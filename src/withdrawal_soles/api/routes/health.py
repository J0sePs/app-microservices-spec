"""Health route used by Traefik and orchestration probes."""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> Any:
    """Report database readiness without authentication."""

    try:
        async with request.app.state.sessionmaker() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable"},
        )
    return {"status": "ok"}
