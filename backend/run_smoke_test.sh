#!/bin/bash
set -e
# Assumes Postgres + Redis are already running (e.g. docker compose up -d db redis) and `alembic upgrade head` was run.
cd "$(dirname "$0")"
LOG="${TMPDIR:-/tmp}/kohwai-uvicorn.log"
uvicorn app.main:app --host 127.0.0.1 --port 8000 > "$LOG" 2>&1 &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null" EXIT

for i in $(seq 1 20); do
  if curl -s -o /dev/null http://127.0.0.1:8000/health; then break; fi
  sleep 0.5
done

echo "=== SERVER UP ==="
curl -s http://127.0.0.1:8000/health; echo

bash "$1" || true

echo "=== SERVER LOG (last 40 lines) ==="
tail -40 "$LOG"
