"""Regression tests for the Batch 1 'make it operational' fixes."""
import json
import time
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import settings
from app.core.database import SessionLocal


# ── A1/A2: Celery must be able to publish AND the default queue must match the worker ──
def test_kombu_is_compatible_with_installed_redis_client():
    """kombu 5.7 requires redis-py>=6.1; we pin redis 5.0.5 so kombu must stay on 5.4.x."""
    import kombu, redis
    k = tuple(int(x) for x in kombu.__version__.split(".")[:2])
    r = tuple(int(x) for x in redis.__version__.split(".")[:2])
    assert k < (5, 7) or r >= (6, 1), f"kombu {kombu.__version__} incompatible with redis {redis.__version__}"


def test_celery_can_publish_and_uses_default_queue():
    import redis
    from app.core.celery_app import celery_app
    assert celery_app.conf.task_default_queue == "default"
    rc = redis.Redis.from_url(settings.CELERY_BROKER_URL)
    rc.delete("default", "celery")
    celery_app.send_task("app.workers.alerts.dispatch_pending_alerts")
    assert rc.llen("default") == 1 and rc.llen("celery") == 0
    rc.delete("default")


def test_every_beat_task_is_registered():
    from app.core.celery_app import celery_app
    celery_app.loader.import_default_modules()
    for entry in celery_app.conf.beat_schedule.values():
        assert entry["task"] in celery_app.tasks, entry["task"]


# ── A4: CORS for the web app's real dev origin ──
async def test_cors_allows_web_dev_origin(client):
    r = await client.options("/api/v1/auth/otp/request", headers={
        "Origin": "http://localhost:3010", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:3010"


# ── OTP exposure is explicit opt-in and development-only ──
async def test_dev_otp_only_when_explicitly_enabled_in_development(client, monkeypatch):
    r = await client.post("/api/v1/auth/otp/request", json={"phone": "+263771000001"})
    assert r.json()["dev_otp"]
    monkeypatch.setattr(settings, "EXPOSE_DEV_OTP", False)
    r = await client.post("/api/v1/auth/otp/request", json={"phone": "+263771000002"})
    assert r.json()["dev_otp"] is None
    monkeypatch.setattr(settings, "EXPOSE_DEV_OTP", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    r = await client.post("/api/v1/auth/otp/request", json={"phone": "+263771000003"})
    assert r.json()["dev_otp"] is None


async def test_startup_refuses_default_secret_outside_development(monkeypatch):
    from app.main import app, lifespan
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", "changeme")
    with pytest.raises(RuntimeError):
        async with lifespan(app):
            pass


# ── A7: audit log — real timestamps, append-only, actually written ──
def test_audit_log_timestamps_are_real_and_append_only():
    import uuid
    tag = uuid.uuid4().hex[:8]          # the table is append-only, so rows from earlier runs stay: use unique names
    a1, a2 = f"T1-{tag}", f"T2-{tag}"
    db = SessionLocal()
    try:
        db.execute(text("INSERT INTO audit_logs (id, action, entity_type) VALUES (gen_random_uuid(), :a, 't')"), {"a": a1})
        db.commit(); time.sleep(1.2)
        db.execute(text("INSERT INTO audit_logs (id, action, entity_type) VALUES (gen_random_uuid(), :a, 't')"), {"a": a2})
        db.commit()
        rows = dict(db.execute(text("SELECT action, timestamp FROM audit_logs WHERE action IN (:a, :b)"), {"a": a1, "b": a2}).all())
        assert rows[a2] > rows[a1], "timestamps are frozen (default evaluated at migration time)"
        for stmt in ("UPDATE audit_logs SET action='x'", "DELETE FROM audit_logs", "TRUNCATE audit_logs"):
            with pytest.raises(DBAPIError):
                db.execute(text(stmt)); db.commit()
            db.rollback()
    finally:
        db.close()


async def test_login_is_audited(client):
    import uuid
    phone = f"+2637{uuid.uuid4().int % 10**8:08d}"      # brand-new number every run: the test must not depend on leftover DB state
    j = (await client.post("/api/v1/auth/otp/request", json={"phone": phone})).json()
    r = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": j["dev_otp"], "accept_terms": True})   # new accounts need consent
    assert r.status_code == 200
    uid = r.json()["user"]["id"]
    bad = await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "000000"})
    db = SessionLocal()
    try:
        actions = [a for (a,) in db.execute(text("SELECT action FROM audit_logs WHERE entity_id IN (:u,:p)"), {"u": uid, "p": phone})]
        assert "auth.register" in actions and "auth.otp_failed" in actions
    finally:
        db.close()
