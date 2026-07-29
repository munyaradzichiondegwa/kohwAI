"""Celery worker: ingests NASA POWER satellite data every 6 hours."""
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.core.redis_client import set_cached
import requests, logging
from datetime import date

logger = logging.getLogger(__name__)

DISTRICTS = {
    "Chipinge": (-20.19, 32.62), "Gokwe": (-18.22, 28.94),
    "Matopos":  (-20.47, 28.50), "Binga":  (-17.62, 27.34),
    "Nyanga":   (-18.22, 32.75), "Harare": (-17.83, 31.05),
}


@celery_app.task(name="app.workers.satellite.ingest_nasa_power", bind=True, max_retries=3)
def ingest_nasa_power(self):
    """Fetch today's NASA POWER weather data for all districts."""
    today = date.today().isoformat().replace("-", "")
    for district, (lat, lon) in DISTRICTS.items():
        try:
            url = (
                f"{settings.NASA_POWER_BASE_URL}"
                f"?parameters=T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN"
                f"&community=AG&longitude={lon}&latitude={lat}"
                f"&start={today}&end={today}&format=JSON"
            )
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()["properties"]["parameter"]
            set_cached(f"weather:{district}", data, ttl_seconds=6 * 3600)
            logger.info(f"NASA POWER data ingested for {district}")
            # TODO: Persist to TimescaleDB hypertable
        except Exception as exc:
            logger.error(f"Failed to ingest NASA POWER for {district}: {exc}")
            self.retry(exc=exc, countdown=300)
