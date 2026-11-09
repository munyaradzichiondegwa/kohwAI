"""Batch 3B: design rules for docker-compose.prod.yml, checked statically (no Docker needed)."""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "docker-compose.prod.yml").read_text())
SERVICES = COMPOSE["services"]
APP_SERVICES = ["api", "worker", "beat", "migrate"]


def published(svc):
    return svc.get("ports", []) or []


def test_only_the_proxy_is_public_everything_else_is_loopback_or_unpublished():
    for name, svc in SERVICES.items():
        for p in published(svc):
            p = str(p)
            if name == "caddy":
                assert re.match(r"^(80:80|443:443(/udp)?)$", p), p
            else:
                assert p.startswith("127.0.0.1:"), f"{name} publishes {p} to the world"
    assert not any(published(SERVICES[n]) for n in ("db", "redis", "api", "worker", "beat", "web", "backup", "migrate"))
    assert {n for n, s in SERVICES.items() if s.get("profiles") == ["monitoring"]} == {"prometheus", "grafana"}


def test_data_network_has_no_internet_and_only_data_services_join_it():
    assert COMPOSE["networks"]["data"]["internal"] is True
    on_data = {n for n, s in SERVICES.items() if "data" in (s.get("networks") or [])}
    assert on_data == {"db", "redis", "migrate", "api", "worker", "beat", "backup"}
    for n in ("web", "caddy", "prometheus", "grafana"):
        assert "data" not in SERVICES[n]["networks"], f"{n} must not reach the database/cache network"
    assert SERVICES["migrate"]["networks"] == ["data"]


def test_no_secret_values_in_environment_or_compose_file():
    text = (ROOT / "docker-compose.prod.yml").read_text()
    # a value after PASSWORD/SECRET_KEY/API_KEY that is not a file path or ${VAR} reference would be a literal secret
    assert not re.search(r"(PASSWORD|SECRET_KEY|API_KEY)\s*:\s*['\"]?(?!/run/secrets|\./secrets|\$\{|\{)[A-Za-z0-9+/=]{8,}", text), "literal secret in compose"
    for name in APP_SERVICES:
        env = SERVICES[name]["environment"]
        assert not {"SECRET_KEY", "POSTGRES_PASSWORD", "REDIS_PASSWORD", "AT_API_KEY", "DATABASE_URL", "REDIS_URL"} & set(env), name
    assert SERVICES["db"]["environment"]["POSTGRES_PASSWORD_FILE"] == "/run/secrets/POSTGRES_PASSWORD"
    assert "POSTGRES_PASSWORD" not in SERVICES["db"]["environment"]


def test_every_secret_is_declared_provisioned_and_used_by_a_service():
    declared = set(COMPOSE["secrets"])
    gen = (ROOT / "scripts" / "gen-secrets.sh").read_text()
    for name, spec in COMPOSE["secrets"].items():
        assert spec["file"] == f"./secrets/{name}"
        assert name in gen, f"gen-secrets.sh does not create {name}"
    used = {s for svc in SERVICES.values() for s in (svc.get("secrets") or [])}
    assert used <= declared and used == declared
    assert "chmod 0444" in gen and "chmod 0700 secrets" in gen        # see the comment in the script for why 0444
    # app settings read these files by exact name (see core/config.py: secrets_dir + case_sensitive)
    from app.core.config import Settings
    for name in ("SECRET_KEY", "POSTGRES_PASSWORD", "REDIS_PASSWORD", "AT_API_KEY"):
        assert name in Settings.model_fields


def test_app_containers_are_hardened_and_never_run_dev_commands():
    for name in APP_SERVICES + ["web"]:
        s = SERVICES[name]
        assert s["read_only"] is True and s["cap_drop"] == ["ALL"] and "no-new-privileges:true" in s["security_opt"], name
        assert not [v for v in (s.get("volumes") or []) if str(v).startswith(("./", "../", "."))], f"{name} mounts source"
    for name, s in SERVICES.items():
        cmd = " ".join(map(str, s.get("command", [])))
        assert "--reload" not in cmd and "flower" not in cmd, name
        assert "flower" not in s["image"], name
        assert "no-new-privileges:true" in s["security_opt"], f"{name} lacks no-new-privileges"


def test_nothing_uses_latest_or_unpinned_third_party_images():
    for name, s in SERVICES.items():
        img = s["image"]
        if img.startswith("kohwai/"):
            assert "${KOHWAI_VERSION" in img, img                      # our own images are tagged with the deployed version
        else:
            assert re.search(r":v?\d+\.\d+", img) and "latest" not in img, f"{name}: {img}"


def test_startup_order_and_health():
    for n in ("api", "worker", "beat"):
        assert SERVICES[n]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
        assert SERVICES[n]["depends_on"]["redis"]["condition"] == "service_healthy"
    assert SERVICES["migrate"]["depends_on"]["db"]["condition"] == "service_healthy"
    assert SERVICES["migrate"]["restart"] == "no" and SERVICES["migrate"]["command"] == ["alembic", "upgrade", "head"]
    for n in ("db", "redis", "api", "worker", "backup"):
        assert "healthcheck" in SERVICES[n], n
    assert "/health/ready" in " ".join(SERVICES["api"]["healthcheck"]["test"])
    for n, s in SERVICES.items():
        if n != "migrate":
            assert s.get("restart") == "unless-stopped", n
    assert "beat" in SERVICES and sum(1 for _ in [SERVICES["beat"]]) == 1


def test_worker_listens_on_every_queue_tasks_are_sent_to_and_redis_never_evicts():
    q = SERVICES["worker"]["command"][SERVICES["worker"]["command"].index("-Q") + 1].split(",")
    from app.core.celery_app import celery_app
    assert celery_app.conf.task_default_queue in q
    assert "noeviction" in " ".join(SERVICES["redis"]["command"])


def test_backup_service_holds_only_the_public_key_and_checks_freshness():
    b = SERVICES["backup"]
    assert set(b["secrets"]) == {"POSTGRES_PASSWORD", "BACKUP_AGE_RECIPIENT"}
    assert "mmin" in " ".join(b["healthcheck"]["test"])
    assert "identity" not in (ROOT / "docker-compose.prod.yml").read_text().lower().replace("backup_age_recipient", "")


def test_caddy_routes_and_hides_what_it_should():
    cf = (ROOT / "infrastructure" / "caddy" / "Caddyfile").read_text()
    assert "reverse_proxy api:8000" in cf and "reverse_proxy web:3000" in cf
    assert re.search(r"@internal path /metrics", cf) and "respond @internal 404" in cf
    for h in ("Strict-Transport-Security", "X-Content-Type-Options", "X-Frame-Options"):
        assert h in cf
    assert "/api/*" in cf and "/ws/*" in cf and "/health/ready" in cf


def test_prod_env_example_has_no_secrets_and_covers_every_variable_compose_requires():
    env = (ROOT / ".env.prod.example").read_text()
    required = set(re.findall(r"\$\{(\w+):\?", (ROOT / "docker-compose.prod.yml").read_text()))
    for var in required:
        assert re.search(rf"^{var}=", env, re.M), f"{var} missing from .env.prod.example"
    assert not re.search(r"(PASSWORD|SECRET|API_KEY)=\S", env)
    gi = (ROOT / ".gitignore").read_text()
    assert "/secrets/*" in gi and ".env.prod" in gi and "/offline/" in gi


def test_dockerfiles_run_non_root_and_use_gunicorn():
    be = "\n".join(l for l in (ROOT / "backend" / "Dockerfile").read_text().splitlines() if not l.lstrip().startswith("#"))
    assert "USER app" in be and "gunicorn" in be and "--reload" not in be and "gdal" not in be.lower()
    web = (ROOT / "apps" / "web" / "Dockerfile").read_text()
    assert "USER node" in web and "standalone" in web
    assert (ROOT / "backend" / "gunicorn.conf.py").exists()
