from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import sentry_sdk
from app.core.config import settings
from app.api.v1.router import api_router
import json, asyncio

# Initialise Sentry
if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT, traces_sample_rate=0.2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: refuse to run outside development with the default JWT secret
    # (anyone could forge admin tokens).
    if settings.ENVIRONMENT != "development" and settings.SECRET_KEY in ("changeme", ""):
        raise RuntimeError("SECRET_KEY must be set to a strong random value when ENVIRONMENT != 'development'")
    yield
    # Shutdown


app = FastAPI(
    title="KohwAI API",
    description="Climate Resilience Super-App — REST + WebSocket API",
    version="1.0.0",
    lifespan=lifespan,
    # API docs are for development only: in production they advertise every endpoint to attackers.
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT == "development" else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)

# API router
app.include_router(api_router, prefix="/api/v1")


# ── WebSocket: real-time alerts ───────────────────────────────────────────────
# Auth: the FIRST message must be {"token": "<access token>"} within 5 s (keeps tokens out of URLs/logs).
# A user may only listen to their own district (admins: any). Messages come from Redis pub/sub
# (published by workers/alerts.py), so this works across any number of API workers.
WS_AUTH_TIMEOUT_SECONDS = 5


def _ws_user(token: str):
    from app.core.database import SessionLocal
    from app.core.security import decode_token
    from app.models.user import User
    payload = decode_token(token or "")
    if not payload or payload.get("type") == "refresh":
        return None
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == payload.get("sub")).first()
        return (u.district, list(u.roles or []), u.is_active) if u else None
    finally:
        db.close()


@app.websocket("/ws/alerts/{district}")
async def websocket_alerts(ws: WebSocket, district: str):
    import redis.asyncio as aioredis
    from fastapi.concurrency import run_in_threadpool
    await ws.accept()
    try:
        first = await asyncio.wait_for(ws.receive_json(), WS_AUTH_TIMEOUT_SECONDS)
        who = await run_in_threadpool(_ws_user, first.get("token", "") if isinstance(first, dict) else "")
    except Exception:  # noqa: BLE001  (timeout, bad JSON, disconnect)
        await ws.close(code=4401)
        return
    if not who or not who[2] or (district != who[0] and "admin" not in who[1]):
        await ws.close(code=4403)
        return

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"alerts:{district}")
    await ws.send_text(json.dumps({"type": "subscribed", "district": district}))

    async def pump():
        async for msg in pubsub.listen():
            if msg.get("type") == "message":
                await ws.send_text(msg["data"])

    task = asyncio.create_task(pump())
    try:
        while True:
            await ws.receive_text()      # clients may send pings; anything else is ignored
    except WebSocketDisconnect:
        pass
    finally:
        task.cancel()
        await pubsub.unsubscribe()
        await pubsub.close()
        await r.close()


@app.get("/health")
async def health_check():
    """Liveness: the process is up. (Used by the load balancer; does not touch dependencies.)"""
    return {"status": "ok", "version": "1.0.0"}


@app.get("/health/ready")
async def readiness_check():
    """Readiness: can we actually serve requests? Checks PostgreSQL and Redis. 503 if either is down."""
    from fastapi.concurrency import run_in_threadpool
    from fastapi.responses import JSONResponse
    from sqlalchemy import text
    from app.core.database import SessionLocal
    from app.core.redis_client import redis_client

    def probe() -> dict:
        checks = {}
        try:
            db = SessionLocal()
            try:
                db.execute(text("SELECT 1"))
            finally:
                db.close()
            checks["database"] = "ok"
        except Exception:  # noqa: BLE001
            checks["database"] = "down"
        try:
            redis_client.ping()
            checks["redis"] = "ok"
        except Exception:  # noqa: BLE001
            checks["redis"] = "down"
        return checks

    checks = await run_in_threadpool(probe)
    ok = all(v == "ok" for v in checks.values())
    return JSONResponse({"status": "ready" if ok else "degraded", **checks}, status_code=200 if ok else 503)
