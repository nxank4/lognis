"""
Async database layer for Lognis.

Exports
-------
engine              Configured async SQLAlchemy engine.
AsyncSessionLocal   Session factory bound to the engine.
get_db              FastAPI dependency — yields an ``AsyncSession`` per request.
init_db             Async function — creates all ORM tables if they don't exist.

Connection strategy for Neon / Supabase
----------------------------------------
* ``pool_pre_ping=True``   Tests each connection before handing it to a
                           request, dropping stale ones silently.
* ``pool_recycle=1800``    Recycles connections after 30 min — important for
                           managed Postgres providers that close idle
                           connections around that threshold.
* ``pool_size=5``          Conservative base; adjust to your Neon plan's
                           max-connection limit.
* ``connect_args``         Passes asyncpg-level timeouts so a hung Neon cold-
                           start never blocks a request indefinitely.

Error handling
--------------
``get_db`` converts ``OperationalError`` / ``InterfaceError`` (connection
refused, auth failure, network partition) and ``asyncio.TimeoutError``
(pool exhaustion, cold-start lag) into HTTP 503 responses so callers receive
a meaningful status code rather than a raw 500.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Guard: surface a clear error when DATABASE_URL is absent
# ---------------------------------------------------------------------------

if not settings.DATABASE_URL:
    logger.warning(
        "DATABASE_URL is not configured. All database operations will fail. "
        "Set DATABASE_URL in your .env file before starting the server."
    )

# ---------------------------------------------------------------------------
# asyncpg connection arguments
# ---------------------------------------------------------------------------

# SSL is already handled by sslmode=require in the URL; SQLAlchemy's asyncpg
# dialect maps it to an SSLContext automatically — no duplication needed here.
_CONNECT_ARGS: dict[str, Any] = {
    "timeout": 10,  # seconds to establish a connection to Neon
    "command_timeout": 60,  # seconds allowed for any single SQL statement
}

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.DATABASE_URL or "postgresql+asyncpg://localhost/placeholder",
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args=_CONNECT_ARGS,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep ORM objects usable after commit
    autoflush=False,
    autocommit=False,
)

# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a fully managed ``AsyncSession`` for a single request lifecycle.

    Behaviour
    ---------
    * Commits the session automatically when the route handler returns
      successfully.
    * Rolls back and re-raises on any exception inside the handler, so
      partial writes never reach the database.
    * Wraps connection-level failures (``OperationalError``, ``TimeoutError``)
      in HTTP 503 so clients receive actionable status codes.

    Usage
    -----
    .. code-block:: python

        @router.post("/")
        async def my_route(db: AsyncSession = Depends(get_db)) -> ...:
            db.add(MyModel(...))
    """
    try:
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise  # propagate to the outer except or FastAPI's handler

    except (OperationalError, InterfaceError) as exc:
        logger.error(
            "Database connection error during request: %s",
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Please try again later.",
        ) from exc

    except asyncio.TimeoutError as exc:
        logger.error("Database connection timed out during request.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection timed out.",
        ) from exc


# ---------------------------------------------------------------------------
# Table initialisation
# ---------------------------------------------------------------------------


async def init_db() -> None:
    """Create all ORM-mapped tables that do not yet exist in the database.

    This is **not** a full migration system — it uses
    ``Base.metadata.create_all`` which is safe for initial setup and
    additive schema changes (new tables) but will **not** alter existing
    tables.  Use Alembic for production schema migrations.

    The import of ``database_models`` is intentionally deferred to this
    function body.  This avoids a circular import between ``database.py``
    (which owns the engine / Base) and ``database_models.py`` (which
    imports Base to define ORM classes).
    """
    # Deferred import — registers all ORM models on Base.metadata.
    from app.models.database_models import Base  # noqa: F401

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified / created successfully.")

    except (OperationalError, InterfaceError) as exc:
        logger.critical("Failed to initialise database tables: %s", exc, exc_info=True)
        raise

    except asyncio.TimeoutError:
        logger.critical("Database initialisation timed out.")
        raise
