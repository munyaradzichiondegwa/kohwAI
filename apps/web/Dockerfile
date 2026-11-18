# syntax=docker/dockerfile:1

# Build context must be the repository root:
# docker build -f apps/web/Dockerfile .

# ==================================================
# STAGE 1: INSTALL DEPENDENCIES
# ==================================================
FROM node:22-alpine AS deps

WORKDIR /repo

# Copy root and workspace package manifests.
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY apps/mobile/package.json apps/mobile/package.json

# Install dependencies with retries for transient registry failures.
RUN --mount=type=cache,target=/root/.npm \
    npm ci \
    --legacy-peer-deps \
    --no-audit \
    --no-fund \
    --fetch-retries=5 \
    --fetch-retry-mintimeout=20000 \
    --fetch-retry-maxtimeout=120000 \
    --fetch-timeout=600000 \
    --maxsockets=5 \
    --workspace=apps/web \
    --include-workspace-root

# ==================================================
# STAGE 2: BUILD NEXT.JS APPLICATION
# ==================================================
FROM node:22-alpine AS build

WORKDIR /repo

# Copy root dependencies.
COPY --from=deps /repo/node_modules ./node_modules

# Copy package manifests.
COPY package.json package-lock.json ./

# Copy application source and shared source.
COPY apps/web ./apps/web
COPY shared ./shared

# Copy workspace-specific dependencies.
COPY --from=deps /repo/apps/web/node_modules ./apps/web/node_modules

# Public environment variables are embedded at build time.
# Defaults remain empty so production can use same-origin reverse-proxy routing.
# Local Docker builds should explicitly pass the host-accessible API and WS URLs.
ARG NEXT_PUBLIC_API_URL=""
ARG NEXT_PUBLIC_WS_URL=""
ARG NEXT_PUBLIC_TERMS_URL=""
ARG NEXT_PUBLIC_PRIVACY_URL=""
ARG NEXT_PUBLIC_VET_CONTACT=""
ARG NEXT_PUBLIC_AGRITEX_CONTACT=""
ARG NEXT_PUBLIC_TILE_URL=""

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL \
    NEXT_PUBLIC_TERMS_URL=$NEXT_PUBLIC_TERMS_URL \
    NEXT_PUBLIC_PRIVACY_URL=$NEXT_PUBLIC_PRIVACY_URL \
    NEXT_PUBLIC_VET_CONTACT=$NEXT_PUBLIC_VET_CONTACT \
    NEXT_PUBLIC_AGRITEX_CONTACT=$NEXT_PUBLIC_AGRITEX_CONTACT \
    NEXT_PUBLIC_TILE_URL=$NEXT_PUBLIC_TILE_URL \
    NEXT_TELEMETRY_DISABLED=1

# Build the production application.
RUN npm run build --workspace=apps/web

# ==================================================
# STAGE 3: PRODUCTION RUNTIME
# ==================================================
FROM node:22-alpine AS run

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /app

# Copy standalone Next.js production output.
COPY --from=build --chown=node:node /repo/apps/web/.next/standalone ./

# Copy static assets.
COPY --from=build --chown=node:node /repo/apps/web/.next/static ./apps/web/.next/static

# Copy public assets.
COPY --from=build --chown=node:node /repo/apps/web/public ./apps/web/public

# Run as an unprivileged user.
USER node

EXPOSE 3000

# Verify application availability.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD wget -qO- http://127.0.0.1:3000/login >/dev/null || exit 1

# Start the standalone Next.js server.
CMD ["node", "apps/web/server.js"]
