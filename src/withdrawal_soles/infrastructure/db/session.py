"""Async engine and session factory construction."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """Create the service engine with conservative production defaults."""

    return create_async_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
    )


def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory with explicit commit control."""

    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
