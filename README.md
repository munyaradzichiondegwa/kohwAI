# 🌍 KohwAI - Climate Resilience Super-App

<p align="center">
  <img src="https://img.shields.io/badge/KohwAI-Climate%20Resilience%20Super--App-1A7A4A?style=for-the-badge&logo=leaf&logoColor=white" />
</p>

<p align="center">
  <b>An offline-first climate intelligence platform for Zimbabwean smallholder farmers.</b>
</p>

<p align="center">
  Connecting farmers, communities, markets, and institutions through rules-based agricultural intelligence, real satellite data, USSD, and resilient digital infrastructure.
</p>

---

## 📖 Overview

**KohwAI** is a climate resilience super-app for Zimbabwean smallholder farmers operating in environments affected by climate variability, drought, water insecurity, livestock disease, limited connectivity, and market access challenges.

The platform combines four channels into one FastAPI backend:

- 📱 **USSD** (`*123#` via Africa's Talking) for feature phones
- 🌐 **Progressive Web App** for smartphones and desktops
- 📲 **Native mobile app** (React Native/Expo) with on-device AI in progress
- 🏘 **Community validation** and an admin dashboard

Every number the app shows a farmer traces back to something real: live NASA POWER satellite readings, a database row a validator approved, or a plainly disclosed rule-of-thumb heuristic, never a placeholder. That "no pretend data" discipline runs through the whole codebase and is the main thing this README tries to reflect accurately.

---

## Table of Contents

- [Quick Start](#-quick-start)
- [Access Channels](#-access-channels)
- [Core Modules](#-core-modules)
- [Real-Time Alerts](#-real-time-alerts)
- [Background Jobs](#-background-jobs-celery)
- [AI & Machine Learning](#-ai--machine-learning)
- [Implementation Status](#-implementation-status)
- [Technology Stack](#-technology-stack)
- [Repository Structure](#-repository-structure)
- [API Reference](#-api-reference)
- [Testing](#-testing)
- [Offline-First Design](#-offline-first-design)
- [Security & Privacy](#-security--privacy)
- [Deployment](#-deployment)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🏗 Architecture

KohwAI's backend is a **modular monolith**, not microservices: one FastAPI app, one Docker Compose stack, eleven domain modules under `/api/v1`.

```
                              Farmers
                                 |
        -------------------------------------------------
        |                       |                        |
      USSD                     PWA                  Native Mobile
 Africa's Talking            Next.js 14            React Native + Expo
 Feature phones          Browsers, low-data      Smartphones, offline-first
        |                       |                        |
        -------------------------------------------------
                                 |
                         FastAPI backend
                  modular monolith  ·  /api/v1
                                 |
   -------------------------------------------------------------------
   |        |        |        |        |          |          |       |
 Identity  Zunde   Mvura    Simba   Musika    Livestock  Community Analytics
  /auth   /zunde  /mvura   /simba  /musika   /livestock /community /analytics
                                 |
                Cross-Pillar Intelligence  ·  /intelligence
                                 |
          PostgreSQL + PostGIS   ·   TimescaleDB   ·   Redis
```

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop + Docker Compose
- Python 3.11+ (the backend Docker image uses 3.12)
- Node.js 20+ and npm
- Git
- PowerShell (Windows) or Bash

### Clone

```bash
git clone https://github.com/munyaradzichiondegwa/kohwAI.git
cd kohwAI
```

### Environment variables

```bash
cp .env.example .env          # required: docker-compose's api/celery services read this file
cp .env.example backend/.env  # only if running the API on the host (then edit hosts/ports below)
```

When running the backend on your **host** (not in Docker), edit `backend/.env` so `DATABASE_URL`/`REDIS_URL`
point at `localhost` and the published ports (Postgres `5434`, Redis `6382`) instead of the compose service names.
Set `EXPOSE_DEV_OTP=true` to have `/auth/otp/request` echo the code locally (honoured only when `ENVIRONMENT=development`).
Outside development the API refuses to start with the default `SECRET_KEY`.

| Variable | Purpose | Local default / example |
|---|---|---|
| `DATABASE_URL` | Main Postgres connection | `postgresql://kohwai:secret@localhost:5434/kohwai` |
| `TIMESCALE_URL` | TimescaleDB connection | `postgresql://kohwai:secret@localhost:5435/kohwai_ts` |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis / Celery | `redis://localhost:6382/...` (see note on ports below) |
| `SECRET_KEY` | JWT signing key | any long random string in production |
| `AT_API_KEY`, `AT_USERNAME`, `AT_SHORTCODE` | Africa's Talking (USSD + SMS) | blank is fine for local dev |
| `ECOCASH_API_KEY`, `ECOCASH_API_SECRET` | EcoCash | not used yet, see [Implementation Status](#-implementation-status) |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_MODEL_BUCKET` | Model storage for OTA delivery | blank until you're training/shipping models |
| `MLFLOW_TRACKING_URI` | MLflow server | `http://localhost:5050` |
| `NASA_POWER_BASE_URL` | Climate data, no key required | `https://power.larc.nasa.gov/api/temporal/daily/point` |
| `SENTRY_DSN` | Optional error tracking | blank to disable |
| `ALLOWED_ORIGINS` | CORS | must include `http://localhost:3010` (the web app's real dev port, see below) |

The full list with sensible defaults lives in `backend/app/core/config.py`. 

### Start infrastructure

```bash
docker compose up -d db timescaledb redis mlflow prometheus grafana
```

Actual host ports, straight from `docker-compose.yml` 
| Service | Host port | Container port |
|---|---|---|
| PostgreSQL (`db`) | 5434 | 5432 |
| TimescaleDB | 5435 | 5432 |
| Redis | **6382** | 6379 |
| MLflow | 5050 | 5000 |
| Prometheus | 9090 | 9090 |
| Grafana | **3012** | 3000 |
| Celery Flower (task monitor) | 5555 | 5555 |

The `api`, `celery_worker`, `celery_beat`, and `celery_flower` services are also defined in `docker-compose.yml` and can be brought up the same way (`docker compose up -d api celery_worker celery_beat celery_flower`) if you'd rather run everything in containers. The steps below run the API and web app locally instead, which is faster for day-to-day development.

### Backend setup

```bash
cd backend
python -m venv .venv
```

Windows:
```powershell
.venv\Scripts\Activate.ps1
```
Linux/macOS:
```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_admin.py +263771234567   # promotes a phone number to admin+validator
uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- To run the Celery worker and beat scheduler locally instead of via Docker, in separate terminals from `backend/`:
  ```bash
  celery -A app.core.celery_app worker --loglevel=info -Q default,satellite,alerts,insurance,risk_model
  celery -A app.core.celery_app beat --loglevel=info
  ```

### Web application

```bash
cd apps/web
npm install --legacy-peer-deps
npm run dev
```

Open `http://localhost:3010`.

### Mobile application

```bash
cd apps/mobile
npm install --legacy-peer-deps
npx expo start
```

Set `EXPO_PUBLIC_API_URL` (used in `src/services/api.ts` and the OTA updater) so the app can reach your backend: `http://localhost:8000` works for iOS simulator, but the Android emulator needs `http://10.0.2.2:8000`, and a physical device needs your machine's LAN IP.

---

## 📱 Access Channels

### USSD (`*123#`)

Built on a real FastAPI callback (`POST /api/v1/ussd/callback`) wired to Africa's Talking, Stateless (Africa's Talking sends the cumulative input), `0=Back / 9=Main Menu`, and every reachable screen is **tested to be ≤160 characters** (`backend/tests/test_ussd.py` walks the whole menu tree). Every number shown comes from the database: recent weather, planting guide and solar screens read the persisted NASA POWER readings; boreholes, listings and insurance status read real records; and when data does not exist the screen says so. Pest/borehole reports and listings are created as *pending* records (same rules as the web app) and need a registered phone — registration with consent is on USSD under *5. My account*. English only for now (no Shona/Ndebele copy has been written, so there is no fake "change language" option). Outside development, set `USSD_ALLOWED_IPS` (Africa's Talking doesn't sign callbacks); an empty list rejects all USSD traffic. *The menu diagram in `docs/ussd-flows/main-menu.md` predates this rewrite — treat the code and `backend/app/modules/ussd/menus.py` as authoritative.*

```
*123# -> MAIN MENU
  1. Zunde - Agriculture
     1. Weather Forecast
     2. Sick Crop -> symptom -> crop -> diagnosis + disclaimer
     3. Sick Animal -> symptom -> animal -> diagnosis + disclaimer
     4. Planting Guide
     5. Report Sighting
  2. Mvura - Water
     1. Nearest Borehole
     2. Report Borehole Status
     3. Water Saving Tips
  3. Simba - Solar Energy
     1. 48h Solar Forecast
     2. Battery Calculator
  4. Musika - Marketplace
     1. Browse Seeds/Produce
     2. List My Produce
     3. Insurance Status
  0. Help / My Data
```

Diagnosis is served by a rules-based decision tree (`app/modules/ussd/rules_engine.py`) covering common crop and livestock conditions, with a safe fallback ("Unknown condition, contact Agritex/Vet Services") for anything outside the current rule set, rather than guessing.

### Progressive Web App

Next.js 14 + TypeScript + Tailwind, with Dexie (IndexedDB) for offline storage and `next-pwa` for installability. Real pages exist for every pillar (`/zunde`, `/mvura`, `/simba`, `/musika`, `/livestock`), auth (`/login`, `/register`), and an admin section (`/admin`, `/admin/analytics`, `/admin/settings`, `/admin/validators`, `/admin/ota`) plus a `/validator` queue page.

### Native Mobile

React Native + Expo, with WatermelonDB for offline storage, Zustand for state, and an Axios client that attaches JWTs automatically. Screens exist for the dashboard, auth, and every pillar, plus dedicated crop and livestock diagnosis flows.

On-device AI is written but not yet wired up: `CropDiagnostics.ts` and `LivestockDiagnostics.ts` implement TFLite inference (the livestock one runs a vision model first and only escalates to an audio model when confidence is low and the top guess looks respiratory), and `OTAModelUpdater.ts` handles background model downloads from S3. `@tensorflow/tfjs-react-native` is deliberately left out of `package.json` for now (a compatibility note there flags an `expo-camera` version conflict), so this code doesn't currently run in a build. See [AI & Machine Learning](#-ai--machine-learning) for the rest of that picture.

---

## 🌱 Core Modules

All endpoints are versioned under `/api/v1`. Diagnosis features across the app are **rules-based decision trees today**, not trained ML models; that's called out per module below and isn't hidden in fine print.

### Identity & Access (`/auth`)
Phone number + OTP login, JWT access/refresh tokens, role-based access (`farmer`, `validator`, `admin`) enforced via FastAPI dependencies. New users can be promoted to admin/validator with `scripts/seed_admin.py`, deliberately not exposed as an API endpoint so privilege escalation is never reachable over HTTP.

### 🌾 Zunde - Agriculture (`/zunde`)
- Rules-based crop symptom triage (`POST /diagnose`) with reference lists for symptoms and crop types
- Pest sighting reports that feed the community validation queue
- An advisory card library, filterable by language and category
- A planting calendar (`GET /planting-calendar`) built on real NASA POWER rainfall data plus a disclosed, simplified "onset of rains" heuristic (cumulative 5-day rainfall vs. a threshold), explicitly not an official Agritex planting calendar
- A district drought risk score (`GET /risk-score`), also NASA POWER-driven and explicitly labeled as a simplified 0-100 indicator, not a calibrated meteorological index like SPI

### 💧 Mvura - Water Security (`/mvura`)
Borehole registry (list, admin-only creation) and community-submitted status reports per borehole.

### ⚡ Simba - Energy Resilience (`/simba`)
One real, well-built endpoint: a 48-hour battery/solar forecast (`GET /battery-forecast`) driven by real NASA POWER solar irradiance data, with a disclosed fallback to a seasonal average when the live feed is unreachable and an explicit disclaimer that it's a simplified energy-balance estimate, not a professional solar sizing calculation. USSD exposes this as two menu items (forecast and battery calculator) that both call the same logic. Broader "energy infrastructure monitoring" is not yet built.

### 🛒 Musika - Marketplace & Insurance (`/musika`)
- Produce and livestock listings (create, browse, deactivate)
- **Parametric drought insurance**: enrollment, payout history, and an admin-triggered payout evaluation (`POST /insurance/evaluate-payout`) that checks a district's real drought index and creates a payout record once it exceeds the threshold for 5+ consecutive days. Enrollment and payout *records* are fully real and persisted; actual EcoCash disbursement is manual today, an admin marks a payout `sent` (`POST /insurance/payouts/{id}/mark-sent`) with a real transaction reference after paying out through their own merchant channel outside the app.

### 🐄 Livestock Health (`/livestock`)
Rules-based symptom triage (shares the same decision-tree approach as Zunde) and animal profile registration.

### 🏘 Community & Validation (`/community`)
A pending-items queue that validators and admins can approve or reject, a general community report endpoint, and a validator/admin listing. Validators only see reports from districts an admin assigned them (`POST /community/validators`), can never review their own reports, must give a reason to reject, and a borehole report only changes the public status once approved. Logins, registrations, validator decisions, settings changes and payout changes are written to an append-only audit log (database triggers block UPDATE/DELETE/TRUNCATE). Not every endpoint is audited yet.

### 📊 Analytics (`/analytics`)
An admin overview endpoint backed by real database counts, no simulated or placeholder figures.

### ⚙️ Settings (`/settings`)
Platform-wide feature flags any authenticated client can read and only admins can change, currently used for things like the PWA's minimum-version gate (surfaced in the web app's `/admin/ota` page).

### 🧠 Cross-Pillar Intelligence (`/intelligence`)
Rule-based correlation logic that reads real rows across the other modules, deliberately not a trained predictive model, and the code says so in its own docstring. Current rules: a recent crop diagnosis suggesting drought stress cross-checked against the real drought index, and pest outbreak clustering (3+ independent sightings of the same pest in the same district within 7 days). Insights dedupe per district for 24 hours and can be dismissed by the user.

---

## 🔴 Real-Time Alerts

A WebSocket endpoint (`/ws/alerts/{district}`) exists in `main.py`, but **nothing publishes to it yet and it is not authenticated** — the web app polls `/alerts/active` instead. Treat WebSocket delivery as not implemented.

---

## ⏱ Background Jobs (Celery)

Scheduled via Celery Beat, timezone `Africa/Harare`, monitored through Flower on port 5555:

| Task | Schedule | What it does | Status |
|---|---|---|---|
| `ingest-satellite-data` | every 6h | Pulls the last ~45 days of NASA POWER weather per district and upserts daily rows (rainfall, temps, solar, trailing-30-day drought index) into `satellite_readings`; missing/`-999` days are skipped | Implemented (in PostgreSQL; the TimescaleDB hypertable is not used) |
| `run-risk-model` | daily 02:00 | Scores districts 0-100 for livestock disease risk | Reads cached weather; loading historical outbreak data is still a TODO |
| `check-insurance-triggers` | daily 02:30 | Creates pending payouts when the rules in `insurance_service.py` hold: inside the Nov–Mar season, index ≥ threshold for N consecutive days, enrolled ≥14 days before the dry spell, one payout per enrolment | Implemented and tested; enrolment is OFF until an admin enables the `musika_insurance_enrollment` flag (a licensed underwriter is required before real payouts) |
| `dispatch-alerts` | every 5 min | Sends queued SMS/push/WebSocket alerts | Scheduled and logging, but the actual DB query and send calls are still a TODO |

---

## 🤖 AI & Machine Learning

This is the area where the gap between ambition and current state is largest, and the codebase is refreshingly upfront about it, so this README will be too.

**What's real:** complete, runnable training pipelines in `ai/models/` for three models: a MobileNetV3-Small crop vision classifier, an EfficientNetV2-S livestock vision classifier, and a mel-spectrogram CNN for livestock audio, all built in **TensorFlow/Keras** (not PyTorch). Each script does transfer learning, logs to MLflow, enforces an accuracy gate (crop and livestock vision require 85% top-3 accuracy before export), and exports an int8-quantized TFLite model. `ai/labeling/label_tool.py` audits a trained model's predictions against folder-labeled data, and `ai/ota/deploy.py` handles checksummed, canary-rollout deployment of new models to S3.

**What's missing:** no dataset has been collected or labeled yet, so no model has actually been trained; there are no `.tflite`, `.h5`, or other model artifacts anywhere in the repo (correctly gitignored, but also just not there yet). The livestock audio script still has a TODO for loading and windowing `.wav` files. And as noted above, the mobile app's on-device inference code exists but its TensorFlow dependency isn't currently installed.

**What actually diagnoses things today:** the rules-based decision trees described under [Core Modules](#-core-modules), not machine learning. That's a deliberate, disclosed design choice in the code, not an oversight.

Requirements: `requirements-ml.txt` has scikit-learn, numpy, pandas, and mlflow; TensorFlow and `tflite-runtime` are commented out there as separate, larger installs. No AWS SageMaker usage was found; `boto3` is used for S3 (model storage and OTA delivery).

---

## ✅ Implementation Status

### Implemented and real
- Phone + OTP auth, JWT sessions, role-based access, append-only audit logging (partial coverage)
- Zunde: crop triage, pest sightings, advisory cards, planting calendar, drought risk score (all with disclosed heuristics)
- Livestock: triage, animal registration
- Mvura: borehole registry and status reporting
- Musika: marketplace listings; insurance enrollment and payout *records* (real, persisted, drought-index-triggered)
- Community: reports and validator approve/reject queue
- Analytics: real DB-backed admin overview
- Cross-pillar intelligence: rule-based correlation engine over live data
- Settings; USSD for all four pillars with real data (see above)
- Satellite ingestion: live NASA POWER calls every 6 hours, Redis-cached
- AI training pipelines: complete and runnable, awaiting a labeled dataset

### Partially implemented
- WebSocket alerts: endpoint exists but nothing broadcasts and it is unauthenticated
- USSD: no PIN login yet (identity is the SIM/phone number), English only
- Triage rules (`ussd/rules_engine.py` → `shared/rules/rules.json`) are **not yet signed off by Agritex / Veterinary Services**; coverage is maize+sorghum and cattle+poultry only
- Helpline numbers must be set (`VET_SERVICES_CONTACT`, `AGRITEX_CONTACT`) — none are shipped
- Map tiles default to openstreetmap.org (no offline tiles); set `NEXT_PUBLIC_TILE_URL` for production
- Alert dispatch worker runs on schedule but the send logic (SMS/push/WebSocket) is still a TODO
- Risk model worker is missing historical outbreak data
- Satellite data isn't yet persisted to TimescaleDB, only cached in Redis
- On-device mobile AI code is written but not currently buildable (TensorFlow dependency deferred)

### Not yet live, by design
- EcoCash: no live merchant integration. Payout and transaction *records* are real; actual money movement is manual and admin-confirmed today.
- Production SMS/USSD needs real Africa's Talking credentials in `.env`

### Repo housekeeping worth knowing about
- **No `LICENSE` file is currently committed**, even though this README (and the original one) describe the project as MIT-licensed. If MIT is the intent, add a `LICENSE` file; the reference below to "see LICENSE" isn't accurate until one exists.
- `.env.example` is committed at the repo root; `.env` itself stays gitignored.

---

## 🛠 Technology Stack

### Frontend
| Component | Technology |
|---|---|
| Web | Next.js 14, TypeScript, Tailwind CSS |
| State | Zustand |
| Offline storage (web) | Dexie (IndexedDB) |
| PWA | next-pwa, Workbox |
| Mobile | React Native 0.74, Expo SDK 51 |
| Offline storage (mobile) | WatermelonDB |

### Backend
| Component | Technology |
|---|---|
| Framework | FastAPI 0.111, Uvicorn |
| ORM / migrations | SQLAlchemy 2, Alembic |
| Validation | Pydantic 2 |
| Auth | JWT (python-jose), OTP (pyotp) |
| Background jobs | Celery 5, Redis broker, Flower for monitoring |
| Realtime | Native FastAPI WebSockets |

### Database
| Component | Technology |
|---|---|
| Primary | PostgreSQL 16 + PostGIS 3.4 |
| Time series | TimescaleDB (pg16 base) |
| Cache / broker | Redis 7 |

### AI / ML
| Component | Technology |
|---|---|
| Training | TensorFlow / Keras (not PyTorch) |
| Classical ML | scikit-learn |
| Edge inference | TensorFlow Lite, int8 quantized |
| Experiment tracking | MLflow |
| Model delivery | Amazon S3 (via boto3), checksummed OTA with canary rollout |
| Climate data | NASA POWER API |

### Infrastructure
| Component | Technology |
|---|---|
| Containers | Docker, Docker Compose |
| Orchestration (available, optional) | Kubernetes manifests in `infrastructure/k8s` |
| Reverse proxy | Nginx |
| Monitoring | Prometheus, Grafana, Sentry |

---

## 📁 Repository Structure

```
kohwAI/
├── apps/
│   ├── web/            Next.js 14 PWA
│   └── mobile/          React Native + Expo app
├── backend/
│   ├── app/
│   │   ├── api/v1/      Router registration
│   │   ├── core/        Config, DB, Redis, Celery, security
│   │   ├── models/      SQLAlchemy models
│   │   ├── modules/      11 domain modules (identity, zunde, mvura, simba,
│   │   │                musika, livestock, community, analytics, ussd,
│   │   │                settings_module, intelligence)
│   │   ├── utils/       Shared risk/audit/SMS/satellite helpers
│   │   └── workers/      Celery tasks
│   ├── alembic/          Migrations
│   ├── scripts/          seed_admin.py
│   └── tests/            pytest + manual smoke-test scripts
├── ai/
│   ├── models/           Training scripts (crop_vision, livestock_vision, livestock_audio)
│   ├── labeling/          Prediction-audit tool
│   └── ota/               S3 model deployment
├── infrastructure/
│   ├── docker/            nginx.conf
│   ├── k8s/                Namespace, API/Celery deployments, ingress
│   └── monitoring/         Prometheus + Grafana config
├── docs/
│   ├── architecture/       Architecture notes
│   └── ussd-flows/         USSD menu map
├── shared/                Cross-app TypeScript types and constants
├── docker-compose.yml
└── README.md
```

---

## 📡 API Reference

All routes are prefixed `/api/v1` unless noted. Full interactive docs at `/docs` once the backend is running.

| Module | Prefix | Key endpoints |
|---|---|---|
| Identity | `/auth` | `POST /otp/request`, `POST /otp/verify`, `POST /refresh`, `GET/PATCH /me` |
| Alerts | `/alerts` | `GET /active`, `POST /` (admin) |
| Zunde | `/zunde` | `POST /diagnose`, `POST /pest-sightings`, `GET /advisory-cards`, `GET /planting-calendar`, `GET /risk-score` |
| Mvura | `/mvura` | `GET/POST /boreholes`, `POST /boreholes/{id}/report` |
| Simba | `/simba` | `GET /battery-forecast` |
| Musika | `/musika` | `GET/POST /listings`, `DELETE /listings/{id}`, `POST /insurance/enroll`, `GET /insurance/my-enrollment`, `GET /insurance/my-payouts`, `POST /insurance/evaluate-payout` (admin), `POST /insurance/payouts/{id}/mark-sent` (admin) |
| Livestock | `/livestock` | `POST /diagnose`, `GET/POST /profiles` |
| Community | `/community` | `GET /queue`, `POST /queue/{kind}/{id}/approve`, `POST /queue/{kind}/{id}/reject`, `POST /reports`, `GET /validators` |
| Analytics | `/analytics` | `GET /overview` (admin) |
| USSD | `/ussd` | `POST /callback` |
| Settings | `/settings` | `GET /`, `PUT /{key}` (admin) |
| Intelligence | `/intelligence` | `GET /insights`, `POST /insights/{id}/dismiss`, `POST /evaluate/district` (admin) |
| Realtime | `/ws/alerts/{district}` | WebSocket, outside `/api/v1` |
| Health | `/health` | Outside `/api/v1` |

---

## 🧪 Testing

Backend tests run against a **separate** database and need Postgres + Redis running:

```bash
createdb -h localhost -p 5434 -U kohwai kohwai_test      # once (see backend/pytest.ini for the URL it uses)
cd backend && pip install -r requirements.txt && python -m pytest
```

CI (`.github/workflows/ci.yml`) runs the same backend tests plus web/mobile type-checks and the web build.

```bash
cd backend
pytest
```

Automated pytest coverage currently spans `tests/test_identity.py` and `tests/test_ussd.py`, not the full module surface yet. Broader end-to-end coverage exists as manual smoke-test shell scripts in `tests/manual/`: `test_auth_flow.sh`, `test_zunde_flow.sh`, `test_insurance_intelligence.sh`, and `test_all_modules.sh` (there's also a `run_smoke_test.sh` at the backend root).

```bash
cd apps/web && npm run lint
cd apps/mobile && npx tsc --noEmit
```

---

## 📶 Offline-First Design

- **Web PWA**: service worker caching (`next-pwa`/Workbox), Dexie/IndexedDB for local data, background sync
- **Mobile**: WatermelonDB for local storage and offline queues, background sync
- **USSD**: works on any feature phone with no data connection at all, by design

---

## 🔐 Security & Privacy

- JWT access/refresh tokens, OTP-based login
- Role-based access (`farmer`, `validator`, `admin`) enforced at the endpoint level via FastAPI dependencies
- Immutable audit log: every sensitive action records user, action, entity, before/after state, IP, and timestamp, with no updates or deletes ever issued against that table
- Admin/validator promotion is a server-side script (`seed_admin.py`), never an HTTP endpoint, so privilege escalation isn't network-reachable

---

## 🚀 Deployment

The architecture doc in `docs/architecture/README.md` describes the near-term real target plainly: a single Docker Compose stack on one VPS, matching the FastAPI modular monolith design rather than a distributed microservices setup. Kubernetes manifests exist in `infrastructure/k8s/` (namespace, API deployment, Celery deployment, ingress, a secrets template) for whenever there's a reason to outgrow that.

```bash
docker compose up
```

---

## 🗺 Roadmap

**Phase 1, Foundation** (mostly done): modular backend, auth, PWA, database architecture, offline support, rules-based diagnostics across all pillars.

**Phase 2, Intelligence expansion** (in progress): collect and label training data, train the crop/livestock vision and audio models the pipeline already supports, re-enable `@tensorflow/tfjs-react-native` in the mobile app once compatible with the current Expo SDK, wire up alert dispatch and TimescaleDB persistence.

**Phase 3, Ecosystem expansion** (future): live EcoCash merchant integration, broader financial services, drone imagery, regional expansion beyond the current pilot districts.

---

## 🤝 Contributing

Contributions are welcome from developers, agronomists, climate researchers, data scientists, and UX designers.

```bash
git checkout -b feature/new-feature
git commit -m "Add new feature"
git push origin feature/new-feature
```

Then open a pull request.

---

## 📄 License

Intended to be MIT, but no `LICENSE` file is currently committed to the repository. Add one (`LICENSE` at the repo root with the standard MIT text) to make that official; until then, standard copyright applies by default.

---

## 🙏 Acknowledgements

NASA POWER for climate data, Africa's Talking for USSD/SMS infrastructure, and the open-source Python and JavaScript communities whose tools this is built on.

---

<p align="center">Built for Zimbabwe. Designed for Africa.</p>
