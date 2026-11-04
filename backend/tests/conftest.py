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
