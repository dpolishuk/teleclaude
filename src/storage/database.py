"""Database initialization and session management."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models import Base

_engine = None
_session_factory = None


async def init_database(db_path: str) -> None:
    """Initialize database and create tables."""
    global _engine, _session_factory

    # Ensure directory exists
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    _engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
