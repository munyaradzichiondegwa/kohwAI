# KohwAI — Climate Resilience Super-App

A unified offline-first super-app for Zimbabwean smallholder farmers.

## Quick Start

```powershell
# 1. Clone & scaffold (already done if you ran setup.js)
# 2. Copy environment file
Copy-Item .env.example .env
# 3. Start infrastructure
docker compose up -d db redis timescaledb mlflow prometheus grafana
# 4. Set up Python backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
# 5. Start Next.js PWA (new terminal)
cd apps/web && npm run dev
# 6. Start Expo (new terminal)
cd apps/mobile && npx expo start
```

## Architecture
- **USSD** (feature phones): Africa's Talking → FastAPI → Rules Engine
- **PWA**: Next.js 14 → FastAPI REST / WebSocket
- **Native App**: React Native (Expo) → FastAPI + on-device TFLite AI
- **Background**: Celery workers (satellite ingestion, risk model, alerts)
- **Database**: PostgreSQL 16 + PostGIS + TimescaleDB
- **AI Registry**: MLflow + AWS SageMaker + OTA via S3

## Modules
1. Identity & Access
2. Zunde — Agriculture & Early Warning
3. Mvura — Water Security
4. Simba — Energy & Infrastructure
5. Musika — Resilient Marketplace
6. Cross-Pillar Intelligence Engine
7. Community & Validation
8. Livestock Health & Management
9. Analytics & Reporting
10. Settings & Platform Configuration
# kohwAI

## Implementation status (as of this update)

This section is maintained to be an honest, accurate account of what is real
and verified versus what still needs work — not marketing copy.

### ✅ Implemented and verified against a live database

Every backend module now has real service/router logic (previously every
module except USSD was an unimplemented `# TODO` stub with zero endpoints):

- **Identity & Auth** — phone + OTP flow, JWT access/refresh, rate limiting.
  Verified end-to-end via a live Postgres instance (see `backend/tests/manual/`).
- **Zunde** — rules-based crop symptom triage (shared logic with USSD),
  pest sighting reports, advisory cards, and a planting-guidance endpoint
  that reads **real NASA POWER satellite rainfall data** with a disclosed,
  simplified onset-of-rains heuristic (not an official Agritex table —
  see the disclaimer returned in the API response).
- **Livestock** — animal registration, rules-based symptom triage, notifiable
  disease flagging.
- **Mvura** — borehole registry + community status reporting.
- **Musika** — marketplace listings (create/browse/deactivate).
- **Community/Validator** — a unified moderation queue spanning pest
  sightings, borehole reports, and general community reports, with
  role-gated approve/reject.
- **Analytics** — admin dashboard backed by real SQL `COUNT`s — no
  estimated or placeholder figures.
- **Settings** — feature-flag / OTA config store for the admin panel.
- **Simba** — 48-hour battery/solar forecast using real NASA POWER solar
  irradiance data, per the PRD's explicit requirement.
- **Musika: parametric drought insurance** (Phase 2 item) — real enrollment
  and payout *records*, with payout triggering based on a real, disclosed
  drought index computed from live NASA POWER rainfall data. Payout
  disbursement itself is recorded manually (`pending_manual_disbursement` →
  `sent` with a real EcoCash reference) since there's no live EcoCash
  merchant integration — see the caveat below.
- **Cross-Pillar Intelligence Engine** (Phase 2 item, previously an
  untouched stub — this module wasn't wired in at all in the prior pass) —
  real correlation rules over actual data across pillars: a drought-symptom
  crop diagnosis checked against real borehole status in the same district;
  a sick livestock diagnosis nudging toward Community reporting and Vet
  Services; and a district-wide pest-outbreak escalation that counts real,
  independent `PestSighting` reports and raises a community alert once
  they cluster past a disclosed threshold. Also added a simplified,
  disclosed **geospatial drought risk score** (`GET /zunde/risk-score`)
  built on the same real satellite data — explicitly not a calibrated
  meteorological index (e.g. SPI), which needs long-term historical
  baselines this system doesn't have.

The Next.js PWA now has real pages (not placeholders) for every pillar,
each wired to the backend with an offline-first fallback (IndexedDB via
Dexie) so the app remains usable with no backend deployed.

### 🔧 Real bugs found and fixed along the way

- `useAuth.ts` imported `useEffect` from `next/navigation` instead of `react`
  — would have broken the entire frontend build.
- Auth tokens were only ever written to `localStorage`, but the Next.js
  middleware reads a cookie — every login would have redirect-looped back
  to `/login`. Fixed by syncing a cookie on every auth state change.
- `apiClient`'s axios interceptor read plain `localStorage` keys
  (`access_token`/`refresh_token`), but the zustand auth store only wrote a
  single JSON blob under `kohwai-auth` — so the Authorization header was
  **never actually attached** to any API request. Fixed by mirroring tokens
  into the plain keys the interceptor expects.
- `passlib==1.7.4` is incompatible with `bcrypt>=4.1` (a known upstream
  issue) — every password/OTP hash call threw a 500. Pinned `bcrypt==4.0.1`.
- Alembic was missing `script.py.mako`, so migration generation silently
  failed with no version scripts ever created.
- The `alerts_router.py` endpoint existed but was never mounted in the main
  API router — every `AlertCarousel` call would 404.
- `axios` was imported by the frontend but missing from `package.json`.
- `next@14.2.3` carried a disclosed **critical** vulnerability per `npm audit`
  — bumped to the latest same-major patch, `14.2.35`.
- A monorepo hoisting quirk left `react` and `react-dom` as two physically
  distinct module copies (same semver, different instances), which broke
  React's internal SSR state during the production build. Fixed with a
  root-level `overrides` pin forcing a single deduplicated copy.
- The Next.js middleware redirected unauthenticated requests for `sw.js`
  (the PWA service worker) to `/login` — meaning the service worker could
  never register for a first-time, logged-out visitor, breaking
  installability at the moment it matters most.
- `.env.example`'s `DATABASE_URL`/`REDIS_URL` pointed at `localhost`, but
  inside `docker-compose` each container needs to reach others by **service
  name** (`db`, `redis`, `timescaledb`) — `localhost` inside a container
  refers to itself. Fixed, with a comment for local (non-Docker) development.
- Generated the PWA install icons (`icon-192.png`, `icon-512.png`,
  maskable variant, apple-touch-icon, favicon) — these were entirely
  missing, which would have blocked "Add to Home Screen" installability.

### ⚠️ Explicitly not implemented (would need external accounts/credentials)

- **EcoCash payment integration** (Musika P2P sales, parametric insurance
  payouts, Simba P2P energy trading) — requires a live EcoCash merchant
  account. The data layer/endpoints for listings exist; actual money
  movement does not, and nothing pretends otherwise.
- **Real SMS delivery** — requires Africa's Talking credentials. OTP works
  end-to-end in development via a clearly-labelled dev-mode fallback that
  returns the code directly in the API response when no gateway is configured.
- **On-device photo-based AI diagnosis (TFLite)** — requires a trained
  model and labelled image data neither of which exist here. The symptom-based
  rules engine (shared with USSD) is real and works today; it is explicitly
  not the computer-vision feature described in the PRD's more advanced scope.
- **React Native mobile app** (`apps/mobile`) — exists as a separate Expo
  project but was not the focus of this pass; the PWA satisfies "installable
  on a phone, opens normally on desktop" without it. If you work on it,
  install its dependencies separately, since the root-level React version
  override (added to fix the web build) may not match React Native's
  expected peer version.

### How to actually run it

```bash
cp .env.example .env        # then fill in real secrets before any real deployment
docker compose up -d db redis timescaledb
cd backend && pip install -r requirements.txt && alembic upgrade head
python scripts/seed_admin.py +263771234567   # bootstrap your own admin account
uvicorn app.main:app --reload
# new terminal
cd apps/web && npm install && npm run build && npm run start
```

Then open the app in a browser and use "Add to Home Screen" (mobile) or
just keep the browser tab open (desktop) — both are the same installable PWA.
