"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from withdrawal_soles.api.errors import install_error_handlers
from withdrawal_soles.api.routes import health, withdrawals
from withdrawal_soles.core.settings import Settings, get_settings
from withdrawal_soles.infrastructure.clients.transaction_service import (
    TransactionServiceClient,
)
from withdrawal_soles.infrastructure.clients.user_service import UserServiceClient
from withdrawal_soles.infrastructure.clock import SystemClock, Uuid4Generator
from withdrawal_soles.infrastructure.db.session import build_engine, build_sessionmaker


def create_app(
    settings: Settings | None = None,
    *,
    user_service: Any | None = None,
    transaction_service: Any | None = None,
    clock: Any | None = None,
    ids: Any | None = None,
    engine: AsyncEngine | None = None,
    sessionmaker: async_sessionmaker[AsyncSession] | None = None,
) -> FastAPI:
    """Build the application with injectable adapters for tests."""

    resolved_settings = settings or get_settings()
    resolved_engine = engine or build_engine(resolved_settings.database_url)
    resolved_sessionmaker = sessionmaker or build_sessionmaker(resolved_engine)
    resolved_user_service = user_service or UserServiceClient(resolved_settings)
    resolved_transaction_service = transaction_service or TransactionServiceClient(
        resolved_settings
    )
    resolved_clock = clock or SystemClock(resolved_settings.business_timezone)
    resolved_ids = ids or Uuid4Generator()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        for adapter in (resolved_user_service, resolved_transaction_service):
            close = getattr(adapter, "aclose", None)
            if close is not None:
                await close()
        await resolved_engine.dispose()

    app = FastAPI(
        title="withdrawal-soles",
        version="0.1.0",
        description="PEN withdrawal service for the banking platform.",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.engine = resolved_engine
    app.state.sessionmaker = resolved_sessionmaker
    app.state.user_service = resolved_user_service
    app.state.transaction_service = resolved_transaction_service
    app.state.clock = resolved_clock
    app.state.ids = resolved_ids

    install_error_handlers(app)
    app.include_router(withdrawals.router)
    app.include_router(health.router)
    return app


app = create_app()
