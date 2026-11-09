# syntax=docker/dockerfile:1
# Build context = repository ROOT (monorepo):  docker build -f apps/web/Dockerfile .
FROM node:20-alpine AS deps
WORKDIR /repo
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY apps/mobile/package.json apps/mobile/package.json
RUN npm ci --legacy-peer-deps --no-audit --no-fund --workspace=apps/web --include-workspace-root

FROM node:20-alpine AS build
WORKDIR /repo
COPY --from=deps /repo/node_modules ./node_modules
COPY package.json package-lock.json ./
COPY apps/web ./apps/web
COPY shared ./shared
# NEXT_PUBLIC_* values are baked into the JavaScript at build time. Empty API URL = same-origin (/api/v1 via the proxy).
ARG NEXT_PUBLIC_API_URL=""
ARG NEXT_PUBLIC_TERMS_URL=""
ARG NEXT_PUBLIC_PRIVACY_URL=""
ARG NEXT_PUBLIC_VET_CONTACT=""
ARG NEXT_PUBLIC_AGRITEX_CONTACT=""
ARG NEXT_PUBLIC_TILE_URL=""
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL NEXT_PUBLIC_TERMS_URL=$NEXT_PUBLIC_TERMS_URL \
    NEXT_PUBLIC_PRIVACY_URL=$NEXT_PUBLIC_PRIVACY_URL NEXT_PUBLIC_VET_CONTACT=$NEXT_PUBLIC_VET_CONTACT \
    NEXT_PUBLIC_AGRITEX_CONTACT=$NEXT_PUBLIC_AGRITEX_CONTACT NEXT_PUBLIC_TILE_URL=$NEXT_PUBLIC_TILE_URL \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build --workspace=apps/web

FROM node:20-alpine AS run
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
COPY --from=build --chown=node:node /repo/apps/web/.next/standalone ./
COPY --from=build --chown=node:node /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=build --chown=node:node /repo/apps/web/public ./apps/web/public
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD wget -qO- http://127.0.0.1:3000/login >/dev/null || exit 1
CMD ["node", "apps/web/server.js"]
