"""Batch 2: marketplace privacy/validation and the parametric-insurance trigger rules."""
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models.musika import InsuranceEnrollment, PayoutRecord, MarketListing
from app.models.satellite import SatelliteReading
from app.modules.musika import insurance_service as ins
from app.modules.musika.insurance_service import InsuranceError
from app.modules.settings_module.service import upsert_setting
from tests.conftest import make_user, auth

TODAY = date(2027, 1, 20)          # inside season 2026-27 (Nov 1 2026 .. Mar 31 2027)


def _readings(db, district, end, days, index):
    """`days` consecutive daily rows ending at `end`, all with the given drought_index."""
    for i in range(days):
        d = end - timedelta(days=i)
        row = db.query(SatelliteReading).filter_by(district=district, reading_date=d, source="nasa_power").first()
        if row:                       # upsert, like real ingestion
            row.drought_index = index
        else:
            db.add(SatelliteReading(district=district, reading_date=d, source="nasa_power", rainfall_mm=0.0, drought_index=index))
    db.commit()


def _enroll_at(db, user, district="Chipinge", season="2026-27", days_ago=60):
    e = InsuranceEnrollment(user_id=user.id, district=district, season=season, is_active=True)
    db.add(e); db.commit()
    e.created_at = datetime.combine(TODAY - timedelta(days=days_ago), datetime.min.time(), tzinfo=timezone.utc)
    db.commit()
    return e


# ─────────────────────────── marketplace ───────────────────────────
def _listing(**over):
    base = {"type": "seed", "title": "SC403 maize seed", "quantity": 40, "unit": "kg", "price_usd": 1.8, "district": "Chipinge"}
    return {**base, **over}


async def test_listing_validation(client, db):
    u = make_user(db)
    for bad in [{"quantity": -5}, {"quantity": 0}, {"price_usd": -1}, {"district": "Atlantis"}, {"type": "weapons"},
                {"expires_at": "2020-01-01T00:00:00Z"}, {"title": "x"},
                {"expires_at": (datetime.now(timezone.utc) + timedelta(days=400)).isoformat()}]:
        r = await client.post("/api/v1/musika/listings", headers=auth(u), json=_listing(**bad))
        assert r.status_code == 422, bad


async def test_seller_phone_hidden_unless_seller_opts_in(client, db, clean):
    seller, buyer = make_user(db), make_user(db)
    hidden = (await client.post("/api/v1/musika/listings", headers=auth(seller), json=_listing(title="Hidden phone"))).json()
    shown = (await client.post("/api/v1/musika/listings", headers=auth(seller), json=_listing(title="Shown phone", share_phone=True))).json()
    rows = {r["title"]: r for r in (await client.get("/api/v1/musika/listings", headers=auth(buyer))).json()}
    assert rows["Hidden phone"]["seller_phone"] is None
    assert rows["Shown phone"]["seller_phone"] == seller.phone
    assert rows["Hidden phone"]["is_mine"] is False
    mine = {r["title"]: r for r in (await client.get("/api/v1/musika/listings", headers=auth(seller))).json()}
    assert mine["Hidden phone"]["is_mine"] is True


async def test_expired_listings_are_not_shown_and_default_expiry_is_set(client, db, clean):
    u = make_user(db)
    created = (await client.post("/api/v1/musika/listings", headers=auth(u), json=_listing())).json()
    assert created["expires_at"] is not None                                   # default now + 30 days
    db.add(MarketListing(seller_id=u.id, type="seed", title="Old", quantity=1, unit="kg", price_usd=1, district="Chipinge",
                         is_active=True, expires_at=datetime.now(timezone.utc) - timedelta(days=1)))
    db.commit()
    titles = [l["title"] for l in (await client.get("/api/v1/musika/listings", headers=auth(u))).json()]
    assert titles == ["SC403 maize seed"]


# ─────────────────────────── insurance ───────────────────────────
def test_season_window_and_validators():
    assert ins.season_window("2026-27") == (date(2026, 11, 1), date(2027, 3, 31))
    from app.utils.validation import check_season, check_ecocash
    with pytest.raises(ValueError): check_season("2026-28")
    with pytest.raises(ValueError): check_season("26-27")
    assert check_ecocash("077 123 4567") == "0771234567"
    with pytest.raises(ValueError): check_ecocash("abc")


def test_no_payout_outside_season_even_with_index_100(db, clean):
    """The dry-season bug: ~0mm rain gives index 100 in July. Must never pay."""
    u = make_user(db); _enroll_at(db, u, season="2026-27")
    july = date(2027, 7, 10)
    _readings(db, "Chipinge", july, 10, 100)
    res = ins.evaluate_district_payout(db, "Chipinge", "2026-27", today=july)
    assert res["triggered"] is False and "Outside policy season" in res["reason"]
    assert db.query(PayoutRecord).count() == 0


def test_needs_five_consecutive_days(db, clean):
    u = make_user(db); _enroll_at(db, u)
    _readings(db, "Chipinge", TODAY, 4, 90)                        # only 4 days
    r = ins.evaluate_district_payout(db, "Chipinge", "2026-27", today=TODAY)
    assert r["triggered"] is False and "need 5" in r["reason"]
    _readings(db, "Chipinge", TODAY - timedelta(days=5), 3, 90)    # older run, but a GAP (day 4 missing) -> still 4 in a row
    assert ins.evaluate_district_payout(db, "Chipinge", "2026-27", today=TODAY)["triggered"] is False
    db.add(SatelliteReading(district="Chipinge", reading_date=TODAY - timedelta(days=4), source="nasa_power",
                            rainfall_mm=0, drought_index=90)); db.commit()   # fill the gap -> 8 in a row
    r = ins.evaluate_district_payout(db, "Chipinge", "2026-27", today=TODAY)
    assert r["triggered"] is True and r["payouts_created"] == 1


def test_one_payout_per_enrolment_however_often_evaluated_or_index_changes(db, clean):
    """Old bug: dedupe keyed on the index value -> $45 paid on a $15 policy."""
    u = make_user(db); e = _enroll_at(db, u)
    for day, idx in enumerate([72, 75, 80, 80, 91]):
        d = TODAY + timedelta(days=day)
        _readings(db, "Chipinge", d, 6, idx)       # the newest day moves to a different index each time
        ins.evaluate_district_payout(db, "Chipinge", "2026-27", today=d)
    rows = db.query(PayoutRecord).all()
    assert len(rows) == 1 and float(rows[0].amount_usd) == 15.0


def test_database_itself_rejects_a_second_payout(db, clean):
    u = make_user(db); e = _enroll_at(db, u)
    db.add(PayoutRecord(enrollment_id=e.id, district="Chipinge", drought_index=80, amount_usd=15, status="pending_manual_disbursement"))
    db.commit()
    db.add(PayoutRecord(enrollment_id=e.id, district="Chipinge", drought_index=81, amount_usd=15, status="pending_manual_disbursement"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_waiting_period_blocks_last_minute_enrolment(db, clean):
    early, late = make_user(db), make_user(db)
    _enroll_at(db, early, days_ago=60)
    _enroll_at(db, late, days_ago=3)                                # enrolled after the dry spell began
    _readings(db, "Chipinge", TODAY, 8, 85)
    r = ins.evaluate_district_payout(db, "Chipinge", "2026-27", today=TODAY)
    assert r["payouts_created"] == 1 and r["skipped_waiting_period"] == 1


def test_stale_data_never_triggers(db, clean):
    u = make_user(db); _enroll_at(db, u)
    _readings(db, "Chipinge", TODAY - timedelta(days=10), 8, 95)    # latest reading is 10 days old
    r = ins.evaluate_district_payout(db, "Chipinge", "2026-27", today=TODAY)
    assert r["triggered"] is False and "stale" in r["reason"]


def test_other_districts_and_seasons_unaffected(db, clean):
    a, b = make_user(db), make_user(db, "Binga")
    _enroll_at(db, a); _enroll_at(db, b, district="Binga")
    _readings(db, "Chipinge", TODAY, 8, 90)
    ins.evaluate_district_payout(db, "Chipinge", "2026-27", today=TODAY)
    assert db.query(PayoutRecord).count() == 1
    assert db.query(PayoutRecord).one().district == "Chipinge"


def test_enrolment_rules(db, clean):
    u = make_user(db)
    e1 = ins.enroll(db, str(u.id), "Chipinge", "2026-27", "0771234567", today=TODAY)
    e1b = ins.enroll(db, str(u.id), "Chipinge", "2026-27", None, today=TODAY)         # idempotent re-enrol
    assert e1.id == e1b.id
    with pytest.raises(InsuranceError) as ex:
        ins.enroll(db, str(u.id), "Binga", "2026-27", None, today=TODAY)               # can't hop districts mid-season
    assert ex.value.status == 409
    with pytest.raises(InsuranceError):
        ins.enroll(db, str(u.id), "Chipinge", "2025-26", None, today=TODAY)            # season over
    e2 = ins.enroll(db, str(u.id), "Chipinge", "2027-28", None, today=TODAY)           # next season = new enrolment
    assert e2.id != e1.id and ins.get_my_enrollment(db, str(u.id)).season == "2027-28"


def test_no_new_enrolment_while_dry_spell_in_progress(db, clean):
    _readings(db, "Chipinge", TODAY, 7, 90)
    with pytest.raises(InsuranceError) as ex:
        ins.enroll(db, str(make_user(db).id), "Chipinge", "2026-27", None, today=TODAY)
    assert "already exist" in str(ex.value)


async def test_enrol_endpoint_respects_feature_flag_and_validates(client, db, clean):
    u = make_user(db); admin = make_user(db, roles=("admin",))
    body = {"district": "Chipinge", "season": "2026-27", "ecocash_number": "0771234567"}
    r = await client.post("/api/v1/musika/insurance/enroll", headers=auth(u), json=body)
    assert r.status_code == 403 and "not open" in r.json()["detail"]                   # flag defaults to OFF
    upsert_setting(db, "feature_flags", {"musika_insurance_enrollment": True, "ussd_gateway": True,
                                         "livestock_ai_photo_diagnosis": False}, None, str(admin.id))
    try:
        bad = await client.post("/api/v1/musika/insurance/enroll", headers=auth(u), json={**body, "ecocash_number": "abc"})
        assert bad.status_code == 422
        bad = await client.post("/api/v1/musika/insurance/enroll", headers=auth(u), json={**body, "district": "Atlantis"})
        assert bad.status_code == 422
        today_season = ins.get_my_enrollment  # noqa: F841  (season check below uses a far-future season)
        ok = await client.post("/api/v1/musika/insurance/enroll", headers=auth(u), json={**body, "season": "2099-00"})
        assert ok.status_code == 200 and ok.json()["season"] == "2099-00"
    finally:
        upsert_setting(db, "feature_flags", {"musika_insurance_enrollment": False, "ussd_gateway": True,
                                             "livestock_ai_photo_diagnosis": False}, None, str(admin.id))


async def test_mark_sent_cannot_be_repeated_and_is_audited(client, db, clean):
    admin = make_user(db, roles=("admin",)); u = make_user(db); e = _enroll_at(db, u)
    p = PayoutRecord(enrollment_id=e.id, district="Chipinge", drought_index=80, amount_usd=15, status="pending_manual_disbursement")
    db.add(p); db.commit()
    assert (await client.post(f"/api/v1/musika/insurance/payouts/{p.id}/mark-sent", headers=auth(admin), json={"ecocash_ref": "EC123456"})).status_code == 200
    assert (await client.post(f"/api/v1/musika/insurance/payouts/{p.id}/mark-sent", headers=auth(admin), json={"ecocash_ref": "EC999999"})).status_code == 409
    from sqlalchemy import text
    n = db.execute(text("select count(*) from audit_logs where action='insurance.payout_marked_sent' and entity_id=:i"), {"i": str(p.id)}).scalar()
    assert n == 1
