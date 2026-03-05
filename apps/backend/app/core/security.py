"""
Security layer for Lognis.

Contents
--------
RapidAPIProxySecretMiddleware
    Starlette ``BaseHTTPMiddleware`` that validates every inbound request
    against the ``X-RapidAPI-Proxy-Secret`` header.  Applied globally in
    ``app/main.py`` so no individual route needs to opt-in.

verify_api_key
    FastAPI ``Security`` dependency kept for per-route granular checks that
    are independent of the proxy-secret gate.

Design notes
------------
* ``hmac.compare_digest`` is used for all secret comparisons to prevent
  timing-oracle attacks (avoids early-exit string equality).
* ``OPTIONS`` requests and a small set of infrastructure paths
  (``/health``, ``/docs``, ``/redoc``, ``/openapi.json``) are exempted so
  that CORS preflight and developer tooling are never blocked.
* When ``RAPIDAPI_PROXY_SECRET`` is **not configured** (empty string) the
  middleware emits a startup warning and skips enforcement.  This keeps
  local development frictionless while making the production misconfiguration
  obvious in logs.
"""

import hmac
import logging
from typing import Final

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Header name required by RapidAPI's proxy layer.
PROXY_SECRET_HEADER: Final[str] = "X-RapidAPI-Proxy-Secret"

#: Paths that bypass the proxy-secret check entirely.
#: Includes CORS preflight (OPTIONS is handled separately) and dev tooling.
_EXEMPT_PATHS: Final[frozenset[str]] = frozenset(
    {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)

#: HTTP methods that are always exempted (browser CORS preflight).
_EXEMPT_METHODS: Final[frozenset[str]] = frozenset({"OPTIONS"})

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class RapidAPIProxySecretMiddleware(BaseHTTPMiddleware):
    """Global middleware that enforces the RapidAPI proxy-secret contract.

    Lifecycle
    ---------
    1. Requests to ``_EXEMPT_PATHS`` or using ``OPTIONS`` pass through
       unconditionally.
    2. ``RAPIDAPI_PROXY_SECRET`` is resolved once at construction time from
       ``settings``; if it is empty the middleware warns and skips enforcement
       on every request (dev-mode convenience).
    3. All other requests must carry an ``X-RapidAPI-Proxy-Secret`` header
       whose value matches the configured secret.  A mismatch or absent header
       results in ``403 Forbidden``.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._secret: str = settings.RAPIDAPI_PROXY_SECRET
        if not self._secret:
            logger.warning(
                "RAPIDAPI_PROXY_SECRET is not configured. "
                "Proxy-secret enforcement is DISABLED. "
                "Set this variable before deploying to production."
            )

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        """Validate the proxy secret before forwarding the request."""
        # ── Exempt paths / methods ──────────────────────────────────────────
        if request.method in _EXEMPT_METHODS or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        # ── Secret not configured → skip enforcement (dev mode) ─────────────
        if not self._secret:
            return await call_next(request)

        # ── Validate header ─────────────────────────────────────────────────
        incoming: str = request.headers.get(PROXY_SECRET_HEADER, "")

        # hmac.compare_digest is constant-time; both args must be the same type.
        if not hmac.compare_digest(incoming, self._secret):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": (
                        f"Forbidden: invalid or missing '{PROXY_SECRET_HEADER}' header."
                    )
                },
            )

        return await call_next(request)


# ---------------------------------------------------------------------------
# Per-route API-key dependency (granular, opt-in)
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(
    name=settings.API_KEY_HEADER,
    auto_error=True,
)


async def verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    """FastAPI dependency — validates the ``X-API-Key`` header.

    Raises ``403 Forbidden`` when the key is absent or incorrect.
    Attach with ``Depends(verify_api_key)`` on any route that requires an
    additional layer of key-based auth on top of the proxy-secret gate.
    """
    if not hmac.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key.",
        )
    return api_key
