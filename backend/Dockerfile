# syntax=docker/dockerfile:1
# Multi-stage, non-root image used for the API, Celery worker/beat and the one-shot migration job.
# (Dev compose reuses it with `uvicorn --reload` and the source mounted over /app.)

FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt && rm -rf /wheels
COPY --chown=app:app . .
USER app
EXPOSE 8000
# Liveness only (does not touch the database); compose also checks /health/ready.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD curl -fsS http://127.0.0.1:8000/health || exit 1
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.main:app"]
