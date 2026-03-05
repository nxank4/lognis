"""
Application configuration - loaded once at startup via pydantic-settings.
"""

from functools import lru_cache
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object.  Values are read from environment variables
    or a ``.env`` file present in the project root."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application metadata
    APP_NAME: str = "Lognis"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # Security
    SECRET_KEY: str = "change-me-in-production"
    API_KEY_HEADER: str = "X-API-Key"
    API_KEY: str = "dev-api-key"

    # RapidAPI proxy secret ─ set this in production via the environment.
    # When left empty the middleware logs a warning and skips enforcement,
    # which is convenient for local development but must never reach prod.
    RAPIDAPI_PROXY_SECRET: str = ""

    # CORS — list every origin that should be allowed to call the API.
    # Browsers reject credentialed cross-origin requests when the server
    # responds with Access-Control-Allow-Origin: * (wildcard + credentials
    # is invalid per the CORS spec).  Always enumerate origins explicitly.
    # Example: ["https://your-app.vercel.app", "http://localhost:3000"]
    ALLOWED_ORIGINS: list[str] = []

    # ---------------------------------------------------------------------------
    # Risk Scoring Engine
    # ---------------------------------------------------------------------------

    # Dimension weights for the composite formula:
    #   S_total = min(10, ω_H * Φ(H) + ω_Z * Ψ(Z) + Σ Kj)
    # Both weights are in [0, 1]; their sum is intentionally < 1 so that
    # heuristic penalties (Σ Kj) can dominate when credentials are present.
    WEIGHT_ENTROPY: float = 0.3  # ω_H — scales the normalised entropy factor
    WEIGHT_ZSCORE: float = 0.3  # ω_Z — scales the Z-score anomaly factor

    # Entropy normalisation bounds for Φ(H):
    #   Φ(H) = clamp((H - ENTROPY_BASE) / (ENTROPY_MAX - ENTROPY_BASE), 0, 1) * 10
    # Scores below ENTROPY_BASE map to 0; scores above ENTROPY_MAX map to 10.
    ENTROPY_BASE: float = 3.0  # bits — typical human-readable log entropy floor
    ENTROPY_MAX: float = 8.0  # bits — theoretical ceiling for 256-char alphabet

    # Heuristic penalties Kj (additive, pre-cap).
    # These are intentionally large so that a single credential leak can
    # push the score toward the Critical band even without high entropy.
    PENALTY_SECRET: float = 5.0  # API key / token / password detected
    PENALTY_SQLI: float = 7.0  # SQL injection pattern detected
    PENALTY_CRITICAL_LEVEL: float = 3.0  # Log level is ERROR or CRITICAL

    # Database ─ accepts postgres://, postgresql://, or postgresql+asyncpg://
    # The validator below normalises any variant to postgresql+asyncpg:// and
    # strips parameters not understood by asyncpg (channel_binding).
    DATABASE_URL: str = ""

    # Redis ─ used for distributed rate limiting (slowapi / limits library).
    # Format: redis://[:password@]host[:port][/db-number]
    #         rediss://...   for TLS (Railway Redis uses plain redis://)
    # When empty the rate limiter falls back to in-process memory storage,
    # which is fine for development but not suitable for multi-worker deploys.
    REDIS_URL: str = ""

    # ---------------------------------------------------------------------------
    # Validators
    # ---------------------------------------------------------------------------

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalise_db_url(cls, raw: str) -> str:
        """Normalise DATABASE_URL to the postgresql+asyncpg:// scheme required
        by SQLAlchemy's async engine.

        Steps
        -----
        1. Rewrite the scheme:
           ``postgres://``    → ``postgresql+asyncpg://``
           ``postgresql://``  → ``postgresql+asyncpg://``
           ``postgresql+asyncpg://`` → unchanged (idempotent)
        2. Strip ``channel_binding`` from the query string — asyncpg does not
           recognise this Neon/PostgreSQL wire-protocol parameter and would
           raise an ``invalid connection option`` error at connect time.
        3. Preserve ``sslmode`` and all other query parameters; SQLAlchemy's
           asyncpg dialect maps ``sslmode=require`` to an SSL context
           automatically.

        Empty strings are returned as-is so that non-database deployments do
        not fail validation.
        """
        if not raw:
            return raw

        # ── 1. Normalise scheme ──────────────────────────────────────────────
        _SCHEME_MAP = {
            "postgres://": "postgresql+asyncpg://",
            "postgresql://": "postgresql+asyncpg://",
        }
        for old_scheme, new_scheme in _SCHEME_MAP.items():
            if raw.startswith(old_scheme):
                raw = new_scheme + raw[len(old_scheme) :]
                break

        # ── 2. Strip channel_binding from query string ───────────────────────
        parsed = urlparse(raw)
        if parsed.query:
            params: dict[str, list[str]] = parse_qs(
                parsed.query, keep_blank_values=True
            )
            params.pop("channel_binding", None)
            new_query = urlencode({k: v[0] for k, v in params.items()}, doseq=False)
            raw = urlunparse(parsed._replace(query=new_query))

        return raw


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()


settings: Settings = get_settings()
