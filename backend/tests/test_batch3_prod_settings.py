"""Batch 3B: secrets from files, URL assembly, refusal to start unsafely."""
import pytest
from pydantic import ValidationError

from app.core.config import Settings

GOOD = dict(ENVIRONMENT="production", SECRET_KEY="x" * 48, DATABASE_URL="postgresql://kohwai:Str0ngPw@db:5432/kohwai",
            ALLOWED_ORIGINS=["https://kohwai.example.org"], REDIS_URL="redis://:pw@redis:6379/0",
            AT_API_KEY="k", USSD_ALLOWED_IPS="196.1.1.1", VET_SERVICES_CONTACT="1", AGRITEX_CONTACT="2")


SETTING_ENV = ["ENVIRONMENT", "SECRET_KEY", "DEBUG", "EXPOSE_DEV_OTP", "DATABASE_URL", "REDIS_URL", "CELERY_BROKER_URL",
               "CELERY_RESULT_BACKEND", "AT_API_KEY", "AT_USERNAME", "USSD_ALLOWED_IPS", "POSTGRES_HOST", "POSTGRES_PASSWORD",
               "REDIS_HOST", "REDIS_PASSWORD", "VET_SERVICES_CONTACT", "AGRITEX_CONTACT", "ALLOWED_ORIGINS", "SENTRY_DSN"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """pytest.ini sets test values as env vars (which rightly outrank defaults); these tests need a blank slate."""
    for k in SETTING_ENV:
        monkeypatch.delenv(k, raising=False)


def s(**kw):
    base = {**GOOD, **kw}
    return Settings(_env_file=None, _secrets_dir=None, **base)


def test_development_never_blocks():
    assert Settings(_env_file=None, _secrets_dir=None, ENVIRONMENT="development").production_problems() == ([], [])


def test_a_correct_production_config_has_no_errors_or_warnings():
    assert s().production_problems() == ([], [])


@pytest.mark.parametrize("override,needle", [
    ({"SECRET_KEY": "changeme"}, "SECRET_KEY"),
    ({"SECRET_KEY": "short-key"}, "SECRET_KEY"),
    ({"DEBUG": True}, "DEBUG"),
    ({"EXPOSE_DEV_OTP": True}, "EXPOSE_DEV_OTP"),
    ({"DATABASE_URL": "postgresql://kohwai:secret@db:5432/kohwai"}, "default password"),
    ({"ALLOWED_ORIGINS": ["http://localhost:3000"]}, "ALLOWED_ORIGINS"),
    ({"ALLOWED_ORIGINS": ["*"]}, "ALLOWED_ORIGINS"),
])
def test_unsafe_production_settings_are_errors(override, needle):
    errors, _ = s(**override).production_problems()
    assert any(needle in e for e in errors), errors


def test_softer_problems_are_warnings_not_errors():
    errors, warnings = s(AT_API_KEY="", USSD_ALLOWED_IPS="", REDIS_URL="redis://redis:6379/0", VET_SERVICES_CONTACT="").production_problems()
    assert errors == [] and len(warnings) == 4


async def test_app_refuses_to_boot_on_errors_and_boots_when_clean(monkeypatch):
    from app.main import app, lifespan
    from app.core import config
    monkeypatch.setattr(config.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(config.settings, "SECRET_KEY", "changeme")
    with pytest.raises(RuntimeError, match="Refusing to start"):
        async with lifespan(app):
            pass
    for k, v in {**GOOD, "EXPOSE_DEV_OTP": False, "DEBUG": False}.items():     # pytest.ini turns the dev OTP echo on
        monkeypatch.setattr(config.settings, k, v)
    async with lifespan(app):
        pass


def test_urls_are_assembled_from_parts_with_escaping():
    cfg = Settings(_env_file=None, _secrets_dir=None, POSTGRES_HOST="db", POSTGRES_PASSWORD="p@ss/w:rd#1", REDIS_HOST="redis", REDIS_PASSWORD="r@/x")
    assert cfg.DATABASE_URL == "postgresql://kohwai:p%40ss%2Fw%3Ard%231@db:5432/kohwai"
    assert cfg.REDIS_URL == "redis://:r%40%2Fx@redis:6379/0"
    assert cfg.CELERY_BROKER_URL.endswith("/0") and cfg.CELERY_RESULT_BACKEND.endswith("/1")
    from sqlalchemy.engine import make_url
    u = make_url(cfg.DATABASE_URL)
    assert u.password == "p@ss/w:rd#1" and u.host == "db"                    # round-trips exactly


def test_explicit_urls_win_over_parts():
    cfg = Settings(_env_file=None, _secrets_dir=None, POSTGRES_HOST="db", POSTGRES_PASSWORD="x", DATABASE_URL="postgresql://u:p@elsewhere/db")
    assert cfg.DATABASE_URL == "postgresql://u:p@elsewhere/db"


def test_secrets_are_read_from_files(tmp_path):
    (tmp_path / "SECRET_KEY").write_text("k" * 50 + "\n")                    # trailing newline from `echo` must not matter
    (tmp_path / "POSTGRES_PASSWORD").write_text("s3cr3t-from-file\n")
    (tmp_path / "AT_API_KEY").write_text("at-key\n")
    cfg = Settings(_env_file=None, _secrets_dir=str(tmp_path), POSTGRES_HOST="db")
    assert cfg.SECRET_KEY == "k" * 50 and cfg.AT_API_KEY == "at-key"
    assert "s3cr3t-from-file" in cfg.DATABASE_URL


def test_alembic_accepts_percent_encoded_passwords(monkeypatch, tmp_path):
    """configparser interpolation used to choke on %XX in the URL."""
    from alembic.config import Config
    cfg = Config()
    cfg.set_main_option("sqlalchemy.url", "postgresql://u:p%40ss@db/x".replace("%", "%%"))
    assert cfg.get_main_option("sqlalchemy.url") == "postgresql://u:p%40ss@db/x"
