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
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="KohwAI API",
    description="Climate Resilience Super-App — REST + WebSocket API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
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


# ── WebSocket hub (real-time alerts) ──────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}  # district → sockets

    async def connect(self, ws: WebSocket, district: str):
        await ws.accept()
        self.connections.setdefault(district, []).append(ws)

    def disconnect(self, ws: WebSocket, district: str):
        if district in self.connections:
            self.connections[district].remove(ws)

    async def broadcast_to_district(self, district: str, message: dict):
        for ws in self.connections.get(district, []):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass


manager = ConnectionManager()


@app.websocket("/ws/alerts/{district}")
async def websocket_alerts(ws: WebSocket, district: str):
    await manager.connect(ws, district)
    try:
        while True:
            await ws.receive_text()  # Keep alive
    except WebSocketDisconnect:
        manager.disconnect(ws, district)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
