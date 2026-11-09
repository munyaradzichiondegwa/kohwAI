"""Gunicorn settings for the production container (uvicorn workers => async FastAPI, several processes).

The API is only reachable from the reverse proxy (internal Docker network), which sets X-Forwarded-For, so trusting
forwarded headers from any address inside that network is safe — and required: the USSD IP allow-list must see the real
caller, not the proxy. NEVER publish the API container's port directly."""
import multiprocessing
import os

bind = "0.0.0.0:8000"
worker_class = "uvicorn.workers.UvicornWorker"
workers = int(os.getenv("WEB_CONCURRENCY", min(4, multiprocessing.cpu_count() * 2 + 1)))
timeout = 60
graceful_timeout = 30
keepalive = 5
max_requests = 2000          # recycle workers occasionally to bound memory growth
max_requests_jitter = 200
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
accesslog = "-"
errorlog = "-"
worker_tmp_dir = "/dev/shm"
