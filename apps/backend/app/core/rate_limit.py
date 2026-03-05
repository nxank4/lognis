"""
Rate limiting — multi-tier strategy using slowapi + limits + Redis.

Tiers
-----
Anonymous  (no identity header)       : 5 requests / minute  — keyed by client IP
Authenticated (Clerk user ID present) : 60 requests / minute — keyed by Clerk user ID

Identity resolution (in priority order)
----------------------------------------
1. ``X-Clerk-User-Id`` header — explicit Clerk user ID forwarded by the Next.js
   frontend after Clerk auth resolves.
2. ``Authorization: Bearer <jwt>`` header — Clerk session JWT.  The ``sub``
   claim (Clerk user ID) is extracted from the payload without cryptographic
   verification; this is acceptable for rate-limit bucketing only.  Full JWT
   verification is done separately for auth-sensitive endpoints.
3. Client IP address — anonymous fallback.

Storage
-------
When ``REDIS_URL`` is configured the ``limits`` library stores counters in Redis
(shared across all worker processes/instances).  When it is empty the limiter
falls back to in-process memory storage, which is suitable for development but
NOT for multi-worker deployments (each worker gets its own independent counter).

Resilience
----------
``swallow_errors=True`` ensures that a Redis outage degrades gracefully — rate
limit enforcement is skipped rather than crashing the application.
"""

import base64
import json
import logging
import time
from contextvars import ContextVar

from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── ContextVar for passing request to dynamic_limit ───────────────────────────
# slowapi calls dynamic limit callables with zero arguments, so we store the
# current request in a ContextVar that _key_func populates before returning.
_request_cv: ContextVar[Request | None] = ContextVar("_request_cv", default=None)

# ── Storage backend ────────────────────────────────────────────────────────────

_storage_uri: str = settings.REDIS_URL if settings.REDIS_URL else "memory://"

if not settings.REDIS_URL:
    logger.warning(
        "REDIS_URL is not configured — rate limiter is using in-process memory "
        "storage.  This is unsuitable for multi-worker or multi-instance deploys."
    )

# ── JWT payload extraction (no verification) ──────────────────────────────────


def _user_id_from_bearer(auth_header: str) -> str | None:
    """Extract the ``sub`` claim from a Clerk Bearer JWT without verification.

    Used exclusively for rate-limit bucketing — not for authentication.
    Returns ``None`` on any parse error so callers can fall back gracefully.
    """
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        # Add padding so base64.b64decode doesn't choke on un-padded input
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        sub = payload.get("sub")
        return str(sub) if sub else None
    except Exception:  # noqa: BLE001
        return None


# ── Identity helper ───────────────────────────────────────────────────────────


def _resolve_user_id(request: Request) -> str | None:
    """Return the Clerk user ID for this request, or ``None`` if anonymous.

    Checks ``X-Clerk-User-Id`` first; falls back to decoding the ``sub``
    claim from an ``Authorization: Bearer <jwt>`` header.
    """
    uid = request.headers.get("X-Clerk-User-Id")
    if uid:
        return uid
    auth = request.headers.get("Authorization", "")
    return _user_id_from_bearer(auth)


# ── Key function ──────────────────────────────────────────────────────────────


def _key_func(request: Request) -> str:
    """Return the rate-limit bucket key for this request.

    Authenticated requests are bucketed by Clerk user ID; anonymous requests
    are bucketed by client IP address.  Also stores the request in
    ``_request_cv`` so that ``dynamic_limit`` (called with zero args by
    slowapi) can access it.
    """
    _request_cv.set(request)
    user_id = _resolve_user_id(request)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


# ── Dynamic limit string ──────────────────────────────────────────────────────


def dynamic_limit() -> str:
    """Return the rate-limit string appropriate for the caller.

    slowapi calls dynamic limit callables with zero arguments.  The current
    request is retrieved from ``_request_cv``, which ``_key_func`` populates
    before returning (slowapi always calls the key function first).

    * Authenticated (Clerk user ID resolvable): ``"60/minute"``
    * Anonymous: ``"5/minute"``
    """
    request = _request_cv.get()
    return "60/minute" if (request and _resolve_user_id(request)) else "5/minute"


# ── Limiter instance ──────────────────────────────────────────────────────────

limiter = Limiter(
    key_func=_key_func,
    storage_uri=_storage_uri,
    swallow_errors=True,  # degrade gracefully if Redis is temporarily unreachable
)

# ── 429 exception handler ─────────────────────────────────────────────────────


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return HTTP 429 with a ``Retry-After`` header.

    All our rate-limit windows are 1 minute wide, so a fixed ``Retry-After: 60``
    is a safe conservative value.  When the ``X-RateLimit-Reset`` header is
    available (injected by the limiter), we derive a tighter value from the
    actual window reset timestamp.
    """
    retry_after = 60  # conservative fallback — matches our longest window
    response = JSONResponse(
        {"detail": "Too Many Requests"},
        status_code=429,
    )
    response.headers["Retry-After"] = str(retry_after)

    # Inject standard X-RateLimit-* headers and refine Retry-After if possible
    try:
        view_rate_limit = getattr(request.state, "view_rate_limit", None)
        if view_rate_limit is not None:
            response = request.app.state.limiter._inject_headers(
                response, view_rate_limit
            )
            reset_header = response.headers.get("X-RateLimit-Reset")
            if reset_header:
                reset_ts = int(float(reset_header))
                computed = max(1, reset_ts - int(time.time()))
                response.headers["Retry-After"] = str(computed)
    except Exception:  # noqa: BLE001 — best-effort, never crash the handler
        pass

    return response
