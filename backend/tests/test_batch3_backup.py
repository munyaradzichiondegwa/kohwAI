"""Batch 3B: the backup / restore / restore-drill scripts really work (needs age + postgres client tools; skipped otherwise)."""
import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest

from app.core.config import settings

SCRIPTS = Path(__file__).resolve().parents[2] / "infrastructure" / "backup"
pytestmark = pytest.mark.skipif(not all(shutil.which(t) for t in ("age", "age-keygen", "pg_dump", "pg_restore", "psql")),
                                reason="needs age and PostgreSQL client tools")


@pytest.fixture
def env(tmp_path):
    u = urlparse(settings.DATABASE_URL)
    ident = tmp_path / "identity.txt"
    subprocess.run(["age-keygen", "-o", str(ident)], check=True, capture_output=True)
    recipient = tmp_path / "recipient.pub"
    recipient.write_text([l for l in ident.read_text().splitlines() if "public key" in l][0].split(": ")[1] + "\n")
    out = tmp_path / "out"
    e = {**os.environ, "PGHOST": u.hostname, "PGPORT": str(u.port or 5432), "PGUSER": u.username, "PGPASSWORD": u.password or "",
         "PGDATABASE": u.path.lstrip("/"), "BACKUP_DIR": str(out), "BACKUP_AGE_RECIPIENT_FILE": str(recipient)}
    return e, ident, out, tmp_path


def run(cmd, env, **kw):
    return subprocess.run(cmd, env=env, capture_output=True, text=True, **kw)


def test_backup_is_encrypted_and_the_restore_drill_passes(env):
    e, ident, out, _ = env
    r = run([str(SCRIPTS / "backup.sh")], e)
    assert r.returncode == 0, r.stderr
    files = list(out.glob("*.dump.age"))
    assert len(files) == 1 and (out / (files[0].name + ".sha256")).exists() and (out / ".last_success").exists()
    raw = files[0].read_bytes()
    assert b"PGDMP" not in raw and b"audit_logs" not in raw                   # ciphertext, not a readable dump
    d = run([str(SCRIPTS / "verify.sh"), str(out), str(ident), "kohwai_restore_check_t"], e)
    assert d.returncode == 0 and "backup is restorable" in d.stdout, d.stdout + d.stderr


def test_restore_refuses_wrong_key_tamper_and_missing_confirmation(env):
    e, ident, out, tmp = env
    assert run([str(SCRIPTS / "backup.sh")], e).returncode == 0
    f = next(out.glob("*.dump.age"))
    other = tmp / "other.txt"
    subprocess.run(["age-keygen", "-o", str(other)], check=True, capture_output=True)
    assert run([str(SCRIPTS / "restore.sh"), str(f), str(ident), "kohwai_t_x"], e).returncode == 2          # needs --yes
    bad = run([str(SCRIPTS / "restore.sh"), str(f), str(other), "kohwai_t_x", "--yes"], e)
    assert bad.returncode == 4 and "nothing was changed" in bad.stderr                                     # wrong key, DB untouched
    exists = run(["psql", "-Atd", "postgres", "-c", "select count(*) from pg_database where datname='kohwai_t_x'"], e).stdout.strip()
    assert exists == "0"                                                                                   # it never even created the target
    f.write_bytes(f.read_bytes() + b"X")                                                                   # corrupt after checksum was taken
    tam = run([str(SCRIPTS / "restore.sh"), str(f), str(ident), "kohwai_t_x", "--yes"], e)
    assert tam.returncode == 3 and "checksum mismatch" in tam.stderr


def test_backup_fails_loudly_without_a_key(env):
    e, _ident, out, _ = env
    e["BACKUP_AGE_RECIPIENT_FILE"] = "/nonexistent"
    r = run([str(SCRIPTS / "backup.sh")], e)
    assert r.returncode != 0 and not list(out.glob("*.dump.age")) and not (out / ".last_success").exists()
