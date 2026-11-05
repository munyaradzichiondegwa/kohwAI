"""Test fixtures: migrate the isolated test database once per session."""
import os
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

from app.core.config import settings


@pytest.fixture(scope="session", autouse=True)
def _migrated_db():
    assert settings.DATABASE_URL.endswith("_test"), (
        f"Refusing to run tests against non-test database: {settings.DATABASE_URL}"
    )
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── helpers shared by the Batch 2 tests ──────────────────────────────────
import itertools
import uuid as _uuid
from datetime import datetime, timezone

from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.models.user import User

_phone_counter = itertools.count(1)
DOMAIN_TABLES = ["payout_records", "insurance_enrollments", "satellite_readings", "borehole_reports", "boreholes",
                 "market_listings", "pest_sightings", "community_reports", "validator_assignments",
                 "cross_pillar_insights", "alerts", "diagnosis_reports", "treatment_records", "livestock_profiles"]


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def clean(db):
    """Empty every domain table (never users / audit_logs) so a test sees only its own data."""
    db.execute(text("TRUNCATE " + ", ".join(DOMAIN_TABLES) + " CASCADE"))
    db.commit()
    yield


def make_user(db, district="Chipinge", roles=("farmer",), phone=None) -> User:
    n = next(_phone_counter)
    phone = phone or f"+2637{_uuid.uuid4().int % 10**8:08d}"
    u = User(phone=phone, district=district, roles=list(roles), language="en")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id), extra={'roles': user.roles})}"}
