# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Optional proxy for restricted networks (e.g. FPT). Pass via --build-arg or
# the HTTP_PROXY env var on the host.  Leave unset for direct downloads (Railway).
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Install dependencies into an isolated prefix so the final image stays lean
COPY requirements.txt .
# When a proxy is provided, route pip through it and trust PyPI hosts
# (corporate proxies often break TLS verification).
# When no proxy is set the else branch runs normally — Railway builds unaffected.
RUN if [ -n "$HTTP_PROXY" ]; then \
      pip install --upgrade pip --proxy "$HTTP_PROXY" \
      && pip install --prefix=/install --no-cache-dir --proxy "$HTTP_PROXY" \
           --trusted-host pypi.org --trusted-host files.pythonhosted.org \
           -r requirements.txt; \
    else \
      pip install --upgrade pip \
      && pip install --prefix=/install --no-cache-dir -r requirements.txt; \
    fi


# ── Runtime stage ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Security: run as non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ ./app/

# Ownership
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

# Health check wired to the /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
