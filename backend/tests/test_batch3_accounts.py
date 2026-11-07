"""Batch 3A: consent, preferences, PIN reset, data export, account deletion."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.config import settings
from app.models.alerts import AlertDelivery
from app.models.livestock import LivestockProfile
from app.models.musika import InsuranceEnrollment, MarketListing, PayoutRecord
from app.models.user import User
from app.modules.ussd.handler import USSDHandler, resolve
from tests.conftest import make_user, auth

API = "/api/v1/auth"


def phone():
    return f"07{uuid.uuid4().int % 10**8:08d}"


async def otp(client, ph):
    return (await client.post(f"{API}/otp/request", json={"phone": ph})).json()["dev_otp"]


# ───────────── consent at registration ─────────────
async def test_new_account_requires_accepting_terms_and_the_code_is_not_burned(client, db):
    ph = phone(); code = await otp(client, ph)
    r = await client.post(f"{API}/otp/verify", json={"phone": ph, "otp": code, "district": "Chipinge"})
    assert r.status_code == 400 and "accept the Terms" in r.json()["detail"]
    assert db.query(User).filter(User.phone.like("%" + ph[1:])).count() == 0              # no account created
    r = await client.post(f"{API}/otp/verify", json={"phone": ph, "otp": code, "district": "Chipinge", "accept_terms": True})
    assert r.status_code == 200                                                              # SAME code still works after ticking the box
    u = r.json()["user"]
    assert u["needs_consent"] is False and u["sms_alerts"] is True and u["has_pin"] is False
    row = db.query(User).filter(User.id == u["id"]).one()
    assert row.terms_accepted_at and row.terms_version == settings.TERMS_VERSION
    n = db.execute(text("select count(*) from audit_logs where action='consent.accepted' and entity_id=:i"), {"i": u["id"]}).scalar()
    assert n == 1


async def test_returning_user_logs_in_without_the_checkbox_and_old_accounts_are_asked_to_consent(client, db):
    legacy = make_user(db, consent=False)                    # an account created before consent capture existed
    me = (await client.get(f"{API}/me", headers=auth(legacy))).json()
    assert me["needs_consent"] is True
    assert (await client.post(f"{API}/consent", headers=auth(legacy), json={"accept": False})).status_code == 400
    r = await client.post(f"{API}/consent", headers=auth(legacy), json={"accept": True})
    assert r.status_code == 200 and r.json()["needs_consent"] is False
    # login of an existing account does not need accept_terms
    ph = legacy.phone; code = await otp(client, ph)
    assert (await client.post(f"{API}/otp/verify", json={"phone": ph, "otp": code})).status_code == 200


async def test_new_terms_version_asks_everyone_again(client, db, monkeypatch):
    u = make_user(db)
    assert (await client.get(f"{API}/me", headers=auth(u))).json()["needs_consent"] is False
    monkeypatch.setattr(settings, "TERMS_VERSION", "2027-01-v2")
    assert (await client.get(f"{API}/me", headers=auth(u))).json()["needs_consent"] is True


async def test_profile_updates_are_validated(client, db):
    u = make_user(db)
    for bad in ({"district": "Atlantis"}, {"language": "klingon"}, {"fcm_token": "x" * 600}):
        assert (await client.patch(f"{API}/me", headers=auth(u), json=bad)).status_code == 422, bad
    ok = await client.patch(f"{API}/me", headers=auth(u), json={"district": "Binga", "language": "sn", "sms_alerts": False})
    assert ok.status_code == 200 and ok.json()["district"] == "Binga" and ok.json()["sms_alerts"] is False
    ph = phone(); code = await otp(client, ph)
    bad = await client.post(f"{API}/otp/verify", json={"phone": ph, "otp": code, "district": "Atlantis", "accept_terms": True})
    assert bad.status_code == 422


# ───────────── PIN via the app ─────────────
async def test_pin_reset_from_the_app_clears_a_lockout_and_works_on_ussd(client, db):
    u = make_user(db, "Chipinge", pin="4829")
    u.pin_locked_until = datetime.now(timezone.utc) + timedelta(minutes=20); db.commit()
    H = USSDHandler()
    assert "Locked" in H.route(db, u.phone, resolve(["1", "5", "4829"]))
    for weak in ("1234", "0000", "9999", "12a4", "123"):
        assert (await client.put(f"{API}/me/pin", headers=auth(u), json={"pin": weak})).status_code == 422, weak
    assert (await client.put(f"{API}/me/pin", headers=auth(u), json={"pin": "7391"})).status_code == 200
    assert H.route(db, u.phone, resolve(["1", "5", "7391"])).startswith("CON Which pest?")
    assert "Wrong PIN" in H.route(db, u.phone, resolve(["1", "5", "4829"]))
    assert (await client.get(f"{API}/me", headers=auth(u))).json()["has_pin"] is True


def test_pin_is_stored_keyed_and_not_derivable_from_the_phone_alone(db):
    from app.modules.identity import pin as pinlib
    a = pinlib.hash_for_new_user("+263771000001", "4829")
    b = pinlib.hash_for_new_user("+263771000002", "4829")
    assert "4829" not in a and a != b                                   # per-phone digest + bcrypt salt
    assert pinlib.validate_pin_format("4829") is None
    assert pinlib.validate_pin_format("1234") and pinlib.validate_pin_format("4321") and pinlib.validate_pin_format("7777")


# ───────────── export & deletion ─────────────
def _populate(db, u):
    animal = LivestockProfile(owner_id=u.id, name="Bessie", animal_type="cattle", district=u.district)
    listing = MarketListing(seller_id=u.id, type="seed", title="Seed", quantity=1, unit="kg", price_usd=1, district=u.district, is_active=True)
    enrol = InsuranceEnrollment(user_id=u.id, district=u.district, season="2026-27", ecocash_number="0771234567", is_active=True)
    db.add_all([animal, listing, enrol]); db.commit()
    return enrol


async def test_export_contains_everything_we_hold(client, db, clean):
    u = make_user(db, "Chipinge", pin="4829"); _populate(db, u)
    r = await client.get(f"{API}/me/export", headers=auth(u))
    d = r.json()
    assert r.status_code == 200 and d["profile"]["phone"] == u.phone and "pin_hash" not in str(d)
    assert d["livestock"][0]["name"] == "Bessie" and d["listings"][0]["title"] == "Seed"
    assert d["insurance"][0]["ecocash_number"] == "0771234567"
    db.expire_all(); assert db.get(User, u.id).data_export_requested_at is not None


async def test_account_deletion_removes_personal_data_but_keeps_audit_trail(client, db, clean):
    u = make_user(db, "Chipinge", pin="4829"); enrol = _populate(db, u)
    uid, old_phone, hdr = u.id, u.phone, auth(u)
    assert (await client.post(f"{API}/me/delete-account", headers=hdr, json={"confirm": False})).status_code == 400

    db.add(PayoutRecord(enrollment_id=enrol.id, district="Chipinge", drought_index=80, amount_usd=15, status="pending_manual_disbursement")); db.commit()
    blocked = await client.post(f"{API}/me/delete-account", headers=hdr, json={"confirm": True})
    assert blocked.status_code == 409 and "payout" in blocked.json()["detail"]                 # never lose money by closing an account
    db.query(PayoutRecord).update({"status": "sent"}); db.commit()

    r = await client.post(f"{API}/me/delete-account", headers=hdr, json={"confirm": True})
    assert r.status_code == 200
    db.expire_all()
    row = db.get(User, uid)
    assert row.is_active is False and row.phone != old_phone and row.phone.startswith("del-") and row.pin_hash is None and row.district is None
    assert db.query(LivestockProfile).filter_by(owner_id=uid).count() == 0
    assert db.query(MarketListing).filter_by(seller_id=uid).count() == 0
    assert db.query(InsuranceEnrollment).filter_by(user_id=uid).one().ecocash_number is None   # financial record kept, phone scrubbed
    assert db.execute(text("select count(*) from audit_logs where action='account.deleted' and user_id=:i"), {"i": str(uid)}).scalar() == 1
    assert (await client.get(f"{API}/me", headers=hdr)).status_code == 401                      # old token is dead
    assert db.query(User).filter(User.phone == old_phone).count() == 0                          # number can register again
