# ── deps stage ────────────────────────────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app
COPY package.json package-lock.json ./

# Optional proxy for restricted networks (e.g. FPT). Pass via --build-arg or
# the HTTP_PROXY env var on the host.  Leave unset for direct downloads (Railway).
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# When a proxy is provided, configure npm to use it explicitly and disable
# strict-ssl (corporate proxies typically intercept TLS with their own cert).
# When no proxy is set the block is a no-op, so Railway builds are unaffected.
RUN if [ -n "$HTTP_PROXY" ]; then \
      npm config set proxy "$HTTP_PROXY" && \
      npm config set https-proxy "${HTTPS_PROXY:-$HTTP_PROXY}" && \
      npm config set strict-ssl false; \
    fi \
    && npm ci --legacy-peer-deps


# ── development stage (used by docker-compose for hot-reload) ─────────────────
FROM node:20-alpine AS development

WORKDIR /app
# Copy source (node_modules will be mounted as a named volume at runtime)
COPY . .

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

EXPOSE 3000
# Install deps into the mounted volume at startup, then launch dev server.
# This ensures node_modules in the named volume always matches package-lock.json,
# regardless of whether the volume was pre-populated from the image layer.
CMD sh -c ' \
  if [ -n "$HTTP_PROXY" ]; then \
    npm config set proxy "$HTTP_PROXY" && \
    npm config set https-proxy "${HTTPS_PROXY:-$HTTP_PROXY}" && \
    npm config set strict-ssl false; \
  fi \
  && npm ci --legacy-peer-deps \
  && npm run dev \
'


# ── builder stage ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

ARG NEXT_PUBLIC_API_URL=http://localhost:8080
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build


# ── production stage ──────────────────────────────────────────────────────────
FROM node:20-alpine AS production

RUN addgroup --system nodejs && adduser --system --ingroup nodejs nextjs

WORKDIR /app

# Copy only the standalone output and static assets
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
