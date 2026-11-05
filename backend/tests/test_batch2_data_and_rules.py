"""Batch 2: satellite/risk data handling, battery model, livestock, Zunde, intelligence."""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.redis_client import redis_client
from app.models.livestock import LivestockProfile
from app.models.satellite import SatelliteReading
from app.models.zunde import DiagnosisReport, PestSighting
from app.models.intelligence import CrossPillarInsight
from app.models.alerts import Alert
from app.utils import satellite, risk, readings
from tests.conftest import make_user, auth


def _nasa_payload(days, rain, fill_last=0, solar=5.0):
    """NASA-shaped JSON for `days` days ending today; the newest `fill_last` days are -999 (not published yet)."""
    end = date.today()
    ds = [(end - timedelta(days=i)).strftime("%Y%m%d") for i in range(days - 1, -1, -1)]
    def series(v):
        return {d: (-999.0 if i >= len(ds) - fill_last else v) for i, d in enumerate(ds)}
    return {"properties": {"parameter": {"PRECTOTCORR": series(rain), "T2M": series(25.0), "T2M_MAX": series(31.0),
                                         "T2M_MIN": series(15.0), "ALLSKY_SFC_SW_DWN": series(solar)}}}


class _Resp:
    def __init__(self, j): self._j = j
    def raise_for_status(self): pass
    def json(self): return self._j


@pytest.fixture(autouse=True)
def _flush_cache():
    redis_client.flushdb()
    yield
    redis_client.flushdb()


# ───────────── NASA fill values / cache ─────────────
def test_fill_values_are_removed_and_results_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(satellite.requests, "get", lambda *a, **k: calls.append(1) or _Resp(_nasa_payload(10, 2.0, fill_last=3)))
    data = satellite.fetch_nasa_power("Chipinge", days_back=9)
    assert all(v > -900 for s in data.values() for v in s.values())      # no -999 anywhere
    assert len(data["PRECTOTCORR"]) == 7                                  # 10 days - 3 unpublished
    satellite.fetch_nasa_power("Chipinge", days_back=9)
    assert len(calls) == 1                                                # second call served from Redis


def test_unknown_district_is_an_error_never_harare():
    with pytest.raises(ValueError):
        satellite.fetch_nasa_power("Atlantis")
    with pytest.raises(ValueError):
        risk.compute_drought_index("Atlantis")


def test_index_is_scaled_for_missing_days_and_none_when_too_few():
    full = risk.index_from_rainfall([1.0] * 30)               # 30mm of 60 -> 50
    assert full["drought_index"] == 50
    gappy = risk.index_from_rainfall([1.0] * 24)              # 24 valid days -> scaled to 30 -> same 50, not "drier"
    assert gappy["drought_index"] == 50
    assert risk.index_from_rainfall([1.0] * 19) is None       # < 20 valid days: refuse to guess


def test_drought_index_endpoint_flags_off_season(monkeypatch):
    monkeypatch.setattr(satellite.requests, "get", lambda *a, **k: _Resp(_nasa_payload(31, 0.0)))
    out = risk.compute_drought_index("Chipinge")
    assert out["drought_index"] == 100
    assert "in_rain_season" in out and "not a calibrated" in out["note"]


def test_store_readings_upserts_and_computes_index(db, clean):
    payload = _nasa_payload(45, 0.5)["properties"]["parameter"]
    cleaned = {k: satellite.clean_series(v) for k, v in payload.items()}
    n1 = readings.store_readings(db, "Chipinge", cleaned)
    n2 = readings.store_readings(db, "Chipinge", cleaned)                 # idempotent
    assert n1 == n2 == 45 and db.query(SatelliteReading).count() == 45
    newest = db.query(SatelliteReading).order_by(SatelliteReading.reading_date.desc()).first()
    assert newest.drought_index == 75 and float(newest.rainfall_mm) == 0.5     # 15mm/30d vs 60 -> 75
    oldest = db.query(SatelliteReading).order_by(SatelliteReading.reading_date).first()
    assert oldest.drought_index is None                                   # <20 days of history before it


def test_ingest_task_continues_past_one_failing_district(db, clean, monkeypatch):
    from app.workers import satellite as worker
    def fake(district, days_back=1, use_cache=True):
        if district == "Binga":
            return None
        return {k: satellite.clean_series(v) for k, v in _nasa_payload(30, 1.0)["properties"]["parameter"].items()}
    monkeypatch.setattr(worker, "fetch_nasa_power", fake)
    monkeypatch.setattr(worker.ingest_nasa_power, "retry", lambda **kw: (_ for _ in ()).throw(RuntimeError("retry")))
    with pytest.raises(RuntimeError):
        worker.ingest_nasa_power.run()
    got = {d for (d,) in db.query(SatelliteReading.district).distinct()}
    assert "Chipinge" in got and "Mutare" in got and "Binga" not in got      # others were NOT aborted


# ───────────── planting calendar ─────────────
def test_planting_calendar_uses_days_that_have_data_and_flags_stale(monkeypatch):
    from app.modules.zunde import service
    monkeypatch.setattr(satellite.requests, "get", lambda *a, **k: _Resp(_nasa_payload(10, 6.0, fill_last=2)))
    cal = service.get_planting_calendar("Chipinge")
    assert cal["cumulative_5day_mm"] == 30.0 and cal["rains_likely_onset"] is True and cal["data_is_stale"] is False
    redis_client.flushdb()
    monkeypatch.setattr(satellite.requests, "get", lambda *a, **k: _Resp(_nasa_payload(10, 6.0, fill_last=9)))
    stale = service.get_planting_calendar("Chipinge")
    assert stale["data_is_stale"] is True and stale["rains_likely_onset"] is False and stale["cumulative_5day_mm"] is None
    with pytest.raises(ValueError):
        service.get_planting_calendar("Atlantis")


async def test_planting_endpoint_rejects_unknown_district(client, db):
    u = make_user(db)
    r = await client.get("/api/v1/zunde/planting-calendar?district=Atlantis", headers=auth(u))
    assert r.status_code == 422
    assert (await client.get("/api/v1/simba/battery-forecast?district=Atlantis&battery_capacity_wh=1000&panel_watts=100&load_watts=10",
                             headers=auth(u))).status_code == 422


# ───────────── battery model ─────────────
def test_battery_model_conserves_energy_over_a_day():
    from app.modules.simba.service import simulate_battery, daylight_overlap_hours
    assert daylight_overlap_hours(0, 24) == 12 and daylight_overlap_hours(18, 30) == 0 and daylight_overlap_hours(5, 7) == 1
    # 1000W panel * 5 kWh/m2 * 0.75 loss = 3750 Wh/day; 10 kWh battery from empty, no load: +37.5% after 24h
    f = simulate_battery(10000, 1000, 0, 0, 5.0, 0.0)
    assert f[4]["hours_from_now"] == 24 and f[4]["estimated_battery_pct"] == 37.5       # old code gave 56.2 (1.5x)


def test_battery_respects_local_time():
    from app.modules.simba.service import simulate_battery
    noon = simulate_battery(10000, 1000, 0, 0, 5.0, 12.0)      # starting at noon: 6 sun-hours then night
    midnight = simulate_battery(10000, 1000, 0, 0, 5.0, 0.0)   # starting at midnight: night first
    assert noon[1]["estimated_battery_pct"] > 0 and midnight[1]["estimated_battery_pct"] == 0
    drain = simulate_battery(1000, 100, 100, 100, 5.0, 19.0)   # night with a load: must drain, never go negative
    assert drain[1]["estimated_battery_pct"] < 100 and min(x["estimated_battery_pct"] for x in drain) >= 0


# ───────────── livestock ─────────────
async def test_livestock_diagnosis_is_persisted_with_real_id(client, db, clean):
    u = make_user(db)
    animal = (await client.post("/api/v1/livestock/profiles", headers=auth(u),
                                json={"name": "Bessie", "animal_type": "cattle", "district": "Chipinge"})).json()
    r = await client.post("/api/v1/livestock/diagnose", headers=auth(u),
                          json={"animal_type_code": "1", "symptom_code": "3", "animal_id": animal["id"]})
    body = r.json()
    assert r.status_code == 200 and body["notifiable"] is True and body["id"] != str(u.id)
    assert "0800" not in body["action"]                                    # no invented phone numbers
    row = db.query(DiagnosisReport).filter_by(subject_type="livestock").one()
    assert str(row.id) == body["id"] and row.top_disease == "Foot and Mouth Disease"
    db.expire_all()
    assert db.query(LivestockProfile).one().health_status == "sick"
    rec = await client.post(f"/api/v1/livestock/profiles/{animal['id']}/recovered", headers=auth(u))
    assert rec.status_code == 200
    db.expire_all()
    assert db.query(LivestockProfile).one().health_status == "healthy"


async def test_livestock_cannot_touch_someone_elses_animal_and_unknown_combo_is_honest(client, db, clean):
    owner, other = make_user(db), make_user(db)
    animal = (await client.post("/api/v1/livestock/profiles", headers=auth(owner),
                                json={"name": "B", "animal_type": "cattle"})).json()
    r = await client.post("/api/v1/livestock/diagnose", headers=auth(other),
                          json={"animal_type_code": "1", "symptom_code": "3", "animal_id": animal["id"]})
    assert r.status_code == 404
    r = await client.post("/api/v1/livestock/recovered", headers=auth(other)) if False else None
    unknown = await client.post("/api/v1/livestock/diagnose", headers=auth(owner), json={"animal_type_code": "2", "symptom_code": "1"})
    j = unknown.json()
    assert j["known"] is False and j["notifiable"] is False and "No guidance" in j["action"]
    assert (await client.post("/api/v1/livestock/diagnose", headers=auth(owner),
                              json={"animal_type_code": "1", "symptom_code": "9"})).status_code == 422


def test_rules_have_no_invented_contacts_and_use_configured_ones(monkeypatch):
    from app.modules.ussd import rules_engine as re_
    from app.core.config import settings
    text = repr(re_.RulesEngine.CROP_RULES) + repr(re_.RulesEngine.LIVESTOCK_RULES)
    assert "0800" not in text
    assert "nearest Veterinary office" in re_.RulesEngine().diagnose_livestock("5", "1")["action"]
    monkeypatch.setattr(settings, "VET_SERVICES_CONTACT", "0242-111111")
    assert "0242-111111" in re_.RulesEngine().diagnose_livestock("5", "1")["action"]
    for code in ("1", "2", "3", "4", "5"):        # one meaning per code, shared by every client
        assert any(c == code for c, _f, _s in re_.LIVESTOCK_SYMPTOMS)
    assert re_.RulesEngine().diagnose_crop("3", "2")["known"] is False and re_.RulesEngine().diagnose_crop("3", "2")["disease2"] is None


# ───────────── pest sightings & intelligence ─────────────
async def test_pest_species_is_a_controlled_vocabulary(client, db):
    u = make_user(db)
    ok = await client.post("/api/v1/zunde/pest-sightings", headers=auth(u),
                           json={"species": "fall  ARMYWORM", "severity": "low", "district": "Chipinge"})
    assert ok.status_code == 200
    assert db.query(PestSighting).order_by(PestSighting.created_at.desc()).first().species == "Fall Armyworm"
    bad = await client.post("/api/v1/zunde/pest-sightings", headers=auth(u),
                            json={"species": "Drought Stress", "severity": "low", "district": "Chipinge"})
    assert bad.status_code == 422
    assert "Fall Armyworm" in (await client.get("/api/v1/zunde/reference/pest-species", headers=auth(u))).json()


def _sightings(db, users, species="Fall Armyworm", status="pending"):
    for u in users:
        db.add(PestSighting(user_id=u.id, species=species, severity="high", district="Chipinge", status=status))
    db.commit()


def test_outbreak_needs_three_different_farmers_and_ignores_rejected(db, clean):
    from app.modules.intelligence import service
    a, b, c = make_user(db), make_user(db), make_user(db)
    _sightings(db, [a, a, a])                                               # one farmer spamming 3 reports
    assert service.evaluate_pest_outbreak(db, "Chipinge") is None and db.query(Alert).count() == 0
    _sightings(db, [b, c], status="rejected")                              # validators said these were false
    assert service.evaluate_pest_outbreak(db, "Chipinge") is None
    _sightings(db, [b, c])                                                 # genuine independent reports
    insight = service.evaluate_pest_outbreak(db, "Chipinge")
    assert insight is not None and "3 different farmers" in insight.message and db.query(Alert).count() == 1
    assert service.evaluate_pest_outbreak(db, "Chipinge") is None          # deduped


def test_outbreak_evaluates_every_species(db, clean):
    from app.modules.intelligence import service
    us = [make_user(db) for _ in range(3)]
    _sightings(db, us, "Fall Armyworm"); _sightings(db, us, "Aphids")
    service.evaluate_pest_outbreak(db, "Chipinge")
    assert db.query(Alert).count() == 2


def test_district_wide_insight_cannot_be_dismissed_by_one_farmer(db, clean):
    from app.modules.intelligence import service
    u = make_user(db)
    shared = CrossPillarInsight(user_id=None, district="Chipinge", source_pillar="community", target_pillar="zunde",
                                insight_type="pest_outbreak:Aphids", severity="red", message="m")
    mine = CrossPillarInsight(user_id=u.id, district="Chipinge", source_pillar="zunde", target_pillar="mvura",
                              insight_type="drought_water_risk", severity="amber", message="m")
    db.add_all([shared, mine]); db.commit()
    assert service.dismiss(db, str(shared.id), u) is False
    assert service.dismiss(db, str(mine.id), u) is True


def test_old_recovered_or_stale_sick_animal_does_not_trigger_followup(db, clean):
    from app.modules.intelligence import service
    u = make_user(db)
    db.add(LivestockProfile(owner_id=u.id, name="Old", animal_type="cattle", district="Chipinge", health_status="sick",
                            last_diagnosed=datetime.now(timezone.utc) - timedelta(days=60))); db.commit()
    assert service.evaluate_for_user(db, u) == []
    db.add(LivestockProfile(owner_id=u.id, name="New", animal_type="cattle", district="Chipinge", health_status="sick",
                            last_diagnosed=datetime.now(timezone.utc))); db.commit()
    out = service.evaluate_for_user(db, u)
    assert len(out) == 1 and "0800" not in out[0].message


async def test_alert_creation_is_validated_and_trailing_slash_works(client, db, clean):
    admin, farmer = make_user(db, roles=("admin",)), make_user(db)
    good = {"pillar": "zunde", "type": "pest", "severity": "red", "title": "Armyworm", "body": "Check fields", "district": "Chipinge"}
    assert (await client.post("/api/v1/alerts", headers=auth(admin), json=good)).status_code == 200
    assert (await client.post("/api/v1/alerts/", headers=auth(admin), json=good)).status_code == 200      # no 307
    assert (await client.post("/api/v1/alerts", headers=auth(admin), json={**good, "severity": "banana"})).status_code == 422
    assert (await client.post("/api/v1/alerts", headers=auth(admin), json={**good, "district": "Nowhere"})).status_code == 422
    assert (await client.post("/api/v1/alerts", headers=auth(farmer), json=good)).status_code == 403


def test_shared_rules_json_matches_python_rules():
    """web/mobile read shared/rules/rules.json; it must never drift from the Python rules engine."""
    import subprocess, sys, pathlib
    script = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "export_rules.py"
    r = subprocess.run([sys.executable, str(script), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
