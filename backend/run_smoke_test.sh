#!/bin/bash
set -e
service postgresql start > /dev/null 2>&1 || true
service redis-server start > /dev/null 2>&1 || true
sleep 2
cd /home/claude/kohwAI/backend
/home/claude/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 > /home/claude/uvicorn.log 2>&1 &
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
tail -40 /home/claude/uvicorn.log
