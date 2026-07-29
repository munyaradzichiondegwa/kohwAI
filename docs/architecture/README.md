# KohwAI Architecture

## Three-Layer Access Model

| Layer       | Technology              | Users                        |
|-------------|-------------------------|------------------------------|
| USSD        | Africa's Talking *123#  | Feature phone farmers (61%)  |
| PWA         | Next.js 14              | Low-data browsers, Validators|
| Native App  | React Native Expo       | Smartphone farmers, AI users |

## Backend Architecture (Phase 1)
Modular monolith — FastAPI with domain modules.
Single Docker Compose on VPS.

## Background Workers
- `satellite`: Ingest NASA POWER every 6h
- `risk_model`: Daily district livestock risk scoring
- `alerts`: Dispatch SMS/push every 5min
- `insurance`: Daily drought payout check
