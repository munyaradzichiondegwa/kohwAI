"""Persist NASA POWER daily readings and the trailing-30-day drought index per day.

Storing a daily history is what makes "N consecutive days above threshold" (insurance)
and trend charts possible; a single live number cannot answer either."""
from datetime import date, datetime, timedelta

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.satellite import SatelliteReading
from app.utils.risk import index_for_date, WINDOW_DAYS
from app.utils.satellite import clean_series

SOURCE = "nasa_power"


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y%m%d").date()


def store_readings(db: Session, district: str, data: dict) -> int:
    """Upsert one row per date from a (fill-value-free) NASA POWER payload, then recompute
    the drought index for each of those dates from stored history. Returns rows written."""
    rain = {_d(k): v for k, v in clean_series(data.get("PRECTOTCORR")).items() if v >= 0}
    tmax = {_d(k): v for k, v in clean_series(data.get("T2M_MAX")).items()}
    tmin = {_d(k): v for k, v in clean_series(data.get("T2M_MIN")).items()}
    sol  = {_d(k): v for k, v in clean_series(data.get("ALLSKY_SFC_SW_DWN")).items() if v >= 0}
    dates = sorted(set(rain) | set(tmax) | set(tmin) | set(sol))
    if not dates:
        return 0

    rows = [{"district": district, "reading_date": d, "source": SOURCE, "rainfall_mm": rain.get(d),
             "temp_max_c": tmax.get(d), "temp_min_c": tmin.get(d), "solar_kwh_m2": sol.get(d)} for d in dates]
    stmt = insert(SatelliteReading).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_reading_district_date_source",
        set_={c: stmt.excluded[c] for c in ("rainfall_mm", "temp_max_c", "temp_min_c", "solar_kwh_m2")})
    db.execute(stmt)
    db.commit()

    # Recompute drought_index for these dates using everything we have stored (incl. older ingests).
    since = min(dates) - timedelta(days=WINDOW_DAYS)
    stored = db.query(SatelliteReading.reading_date, SatelliteReading.rainfall_mm).filter(
        SatelliteReading.district == district, SatelliteReading.source == SOURCE,
        SatelliteReading.reading_date >= since, SatelliteReading.rainfall_mm.isnot(None)).all()
    rain_map = {d: float(mm) for d, mm in stored}
    for d in dates:
        res = index_for_date(rain_map, d)
        db.query(SatelliteReading).filter(
            SatelliteReading.district == district, SatelliteReading.reading_date == d,
            SatelliteReading.source == SOURCE).update({"drought_index": res["drought_index"] if res else None})
    db.commit()
    return len(rows)
