"""
Lognis - FastAPI application entry point.

Middleware stack (outermost → innermost, i.e. first-added runs last on request):
  1. CORSMiddleware          – added first → runs second on the way in.
  2. RapidAPIProxySecretMiddleware – added second → runs first on the way in,
                                     guarding every route before CORS touches it.

This ordering ensures:
  * CORS ``OPTIONS`` preflight requests are already exempted inside the proxy
    middleware so browsers never receive spurious 403s.
  * All real API traffic is gated by the proxy-secret check before any
    application logic executes.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.rate_limit import limiter, rate_limit_handler
from app.core.security import RapidAPIProxySecretMiddleware

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Application lifespan — runs once at startup and once at shutdown.

    Startup
    -------
    Calls :func:`~app.core.database.init_db` to create any missing ORM tables.
    Failure is logged as a warning (not a crash) so the app still starts in
    environments where the database is temporarily unavailable; history
    persistence will be degraded until connectivity is restored.
    """
    from app.core.database import init_db  # deferred to keep startup clean

    if not settings.DATABASE_URL:
        logger.warning(
            "DATABASE_URL is not set — skipping database initialisation. "
            "History persistence will be unavailable until DATABASE_URL is configured."
        )
    else:
        try:
            await init_db()
        except Exception:
            logger.warning(
                "Database initialisation failed at startup — "
                "history persistence will be unavailable until connectivity is restored.",
                exc_info=True,
            )

    yield  # application is running


# ── Application factory ───────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Lognis - Intelligent log analysis service.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Rate limiter ──────────────────────────────────────────────────────────────
# Attach the limiter to app.state so slowapi can resolve it from request context,
# and register the 429 handler that adds the Retry-After header.

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)  # type: ignore[arg-type]

# ── Middleware registration ────────────────────────────────────────────────────
# Order matters: last-added middleware wraps the outermost layer of the stack.

# 1. CORS — must sit outside the proxy check so preflight OPTIONS flows freely.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. RapidAPI proxy-secret gate — added after CORS so it runs first on inbound
#    requests, before any route handler or the CORS middleware sees the request.
app.add_middleware(RapidAPIProxySecretMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(api_v1_router, prefix="/api/v1")


# ── Infrastructure endpoints ──────────────────────────────────────────────────


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Return service liveness status.

    Exempted from the proxy-secret check so that load-balancer health probes
    and container orchestrators (K8s, ECS) always get a clean 200.
    """
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
