# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Optional proxy for restricted networks (e.g. FPT). Pass via --build-arg or
# the HTTP_PROXY env var on the host.  Leave unset for direct downloads (Railway).
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ENV HTTP_PROXY=$HTTP_PROXY \
    HTTPS_PROXY=$HTTPS_PROXY \
    NO_PROXY=$NO_PROXY

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy only the dependency manifest and lockfile first (layer-cache friendly)
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment — no project code needed here
RUN uv sync --frozen --no-dev --no-install-project


# ── Runtime stage ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Security: run as non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY app/ ./app/

# Ownership
RUN chown -R appuser:appgroup /app

USER appuser

# Activate the virtual environment
ENV PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv"

EXPOSE 8080

# Health check wired to the /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
