"""USSD: real data only, <=160 chars on every reachable screen, navigation, registration, writes."""
import collections
from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.models.mvura import Borehole, BoreholeReport
from app.models.musika import MarketListing
from app.models.satellite import SatelliteReading
from app.models.user import User
from app.models.zunde import PestSighting
from app.modules.ussd.handler import USSDHandler, resolve
from app.modules.ussd.menus import MAX_LEN
from tests.conftest import make_user

H = USSDHandler()
PIN = "4829"


def fresh_phone() -> str:
    import uuid
    return f"+2637{uuid.uuid4().int % 10**8:08d}"
FAKE_MARKERS = ["Masvingo Village Well", "Chipinge  Mon", "42/100", "0800-", "Coming soon", "6.2 kWh", "Source: Agritex / SARCOF"]


def ask(db, phone, *inputs):
    out = H.route(db, phone, resolve(list(inputs)))
    assert len(out) <= MAX_LEN, f"USSD screen is {len(out)} chars (limit {MAX_LEN}): {out!r}"      # every test response, not just the walk
    return out


async def post(client, text, phone="+263771234567"):
    return await client.post("/api/v1/ussd/callback", data={"sessionId": "s", "serviceCode": "*123#", "phoneNumber": phone, "text": text})


def seed(db, district="Chipinge"):
    today = date.today()
    for i in range(6):
        db.add(SatelliteReading(district=district, reading_date=today - timedelta(days=i), source="nasa_power",
                                rainfall_mm=6.0 - i, temp_max_c=30.5, solar_kwh_m2=5.5, drought_index=40))
    db.add(Borehole(name="Mutema Primary School Community Borehole", village="Mutema", district=district, status="working",
                    last_verified=datetime.now(timezone.utc)))
    db.add(Borehole(name="Dry Gulley Borehole", village="V", district=district, status="dry"))
    seller = make_user(db, district)
    db.add(MarketListing(seller_id=seller.id, type="seed", title="SC403 certified maize seed", quantity=40, unit="kg",
                         price_usd=1.8, district=district, is_active=True, share_phone=True,
                         expires_at=datetime.now(timezone.utc) + timedelta(days=5)))
    db.commit()


# ───────── protocol / navigation ─────────
def test_resolve_navigation():
    assert resolve(["1", "2", "0"]) == ["1"]
    assert resolve(["1", "2", "9"]) == []
    assert resolve(["1", "2", "9", "3"]) == ["3"]
    assert resolve(["0"]) == ["0"]                 # root-level 0 = Help
    assert resolve(["1", "0", "0"]) == ["0"]


async def test_callback_main_menu_and_back(client):
    r = await post(client, "")
    assert r.status_code == 200 and r.text.startswith("CON KohwAI") and "Farming" in r.text
    back = await post(client, "1*0")
    assert back.text == r.text                       # 0 returns to the main menu
    menu = await post(client, "2*1*9")
    assert menu.text == r.text                       # 9 always returns to main menu


async def test_callback_help_uses_configured_contacts_only(client, monkeypatch):
    r = await post(client, "0")
    assert r.text.startswith("END") and "nearest Veterinary office" in r.text and "0800" not in r.text
    monkeypatch.setattr(settings, "VET_SERVICES_CONTACT", "0242-700000")
    assert "0242-700000" in (await post(client, "0")).text


async def test_ussd_gateway_flag_off_and_ip_allowlist(client, db, monkeypatch):
    # production-like: empty allowlist rejects everything (fail closed)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert (await post(client, "")).status_code == 403
    monkeypatch.setattr(settings, "USSD_ALLOWED_IPS", "203.0.113.9")
    assert (await post(client, "")).status_code == 403          # test client's IP is not on the list
    monkeypatch.setattr(settings, "USSD_ALLOWED_IPS", "127.0.0.1,testclient")
    assert (await post(client, "")).status_code == 200


# ───────── real data, no fakes ─────────
def test_weather_planting_solar_come_from_stored_readings(db, clean):
    seed(db)
    u = make_user(db, "Chipinge", pin=PIN)
    w = ask(db, u.phone, "1", "1")
    assert w.startswith("END") and "Chipinge" in w and "6.0mm" in w and "Observed, not a forecast" in w
    p = ask(db, u.phone, "1", "4")
    assert "Rain, last 5 days: 20mm" in p and "Rain still light" in p                # 6+5+4+3+2 = 20 < 25
    s = ask(db, u.phone, "3", "1")
    assert "5.5 kWh/m2/day" in s


def test_no_data_says_so_instead_of_inventing(db, clean):
    u = make_user(db, "Binga")
    assert "No satellite data stored yet" in ask(db, u.phone, "1", "1")
    assert "Not enough recent rain data" in ask(db, u.phone, "1", "4")
    assert "No solar data stored yet" in ask(db, u.phone, "3", "1")
    assert "None registered yet" in ask(db, u.phone, "2", "1")
    assert "No seed listings" in ask(db, u.phone, "4", "1", "1")


def test_boreholes_screen_shows_real_names_and_verification(db, clean):
    seed(db); u = make_user(db, "Chipinge", pin=PIN)
    out = ask(db, u.phone, "2", "1")
    assert "Mutema Primary S: working" in out and "Dry Gulley Boreh: dry (unverified)" in out
    assert out.index("working") < out.index("dry")                         # best status first


def test_browse_shows_phone_only_when_seller_opted_in(db, clean):
    seed(db); u = make_user(db, "Chipinge", pin=PIN)
    assert "SC403 certifie 40kg $1.8 07" in ask(db, u.phone, "4", "1", "1")
    db.query(MarketListing).update({"share_phone": False}); db.commit()
    out = ask(db, u.phone, "4", "1", "1")
    assert "SC403" in out and "$1.8 07" not in out


def test_diagnosis_screens_are_honest_and_short(db):
    u = "+263771110000"
    assert "Maize Streak Virus" in ask(db, u, "1", "2", "1", "1") and "Guide only" in ask(db, u, "1", "2", "1", "1")
    assert "No guidance yet" in ask(db, u, "1", "2", "3", "2")             # sorghum + chewed leaves: no rule -> say so
    assert "No crop guide yet" in ask(db, u, "1", "2", "1", "3")
    fmd = ask(db, u, "1", "3", "3", "1")
    assert "Foot and Mouth" in fmd and "REPORTABLE" in fmd and "Report to your nearest Veterinary office NOW" in fmd
    assert "No guide for this animal yet" in ask(db, u, "1", "3", "1", "3")
    assert "Nitrogen" in ask(db, u, "1", "2", "1", "1")


def test_battery_calculator_uses_real_energy_model(db, clean):
    seed(db); u = make_user(db, "Chipinge", pin=PIN)
    out = ask(db, u.phone, "3", "2", "1000", "10000", "5", "1")
    # 1000W * 5.5 kWh/m2 * 0.75 = 4125 Wh/day; +41.25% - 0.24% (1W load) + 5% start = ~46% after any 24h, whatever the clock
    assert "Battery now 5%" in out and "In 24h: ~46%" in out and "live sun data" in out
    assert "Invalid number" in ask(db, u.phone, "3", "2", "1000", "10000", "150", "1")
    assert "Invalid number" in ask(db, u.phone, "3", "2", "abc")
    assert ask(db, u.phone, "3", "2").startswith("CON Solar panel watts?")


# ───────── registration & writes ─────────
def test_registration_requires_consent_district_and_pin(db):
    phone = fresh_phone()
    consent = ask(db, phone, "5")
    assert "accept the KohwAI Terms" in consent and "SMS" in consent
    assert ask(db, phone, "5", "2") == "END Invalid choice. Dial again to restart."
    page1 = ask(db, phone, "5", "1")
    assert "1. Chipinge" in page1 and "8. More" in page1 and "9." not in page1          # '9' is reserved for Menu
    page2 = ask(db, phone, "5", "1", "8")
    assert "1. Mutare" in page2 and "3. Masvingo" in page2 and "Chipinge" not in page2
    assert "Create a 4-digit PIN" in ask(db, phone, "5", "1", "8", "3")
    assert "Confirm your PIN" in ask(db, phone, "5", "1", "8", "3", PIN)
    assert db.query(User).filter_by(phone=phone).first() is None                      # nothing saved until PIN confirmed
    assert "did not match" in ask(db, phone, "5", "1", "8", "3", PIN, "1111")
    assert "too easy" in ask(db, phone, "5", "1", "8", "3", "1234", "1234")
    assert db.query(User).filter_by(phone=phone).first() is None
    done = ask(db, phone, "5", "1", "8", "3", PIN, PIN)
    assert "Registered in Masvingo" in done
    u = db.query(User).filter_by(phone=phone).one()
    assert u.terms_accepted_at is not None and u.terms_version == settings.TERMS_VERSION and u.sms_alerts is True
    assert u.roles == ["farmer"] and u.district == "Masvingo" and u.pin_hash and PIN not in u.pin_hash
    assert "Registered: Masvingo" in ask(db, phone, "5")                               # now recognised


def test_writes_require_registration(db):
    p = fresh_phone()
    for path in (("1", "5"), ("2", "2"), ("4", "2"), ("4", "3")):
        assert "register first" in ask(db, p, *path), path


def test_pest_report_creates_pending_sighting(db, clean):
    u = make_user(db, "Chipinge", pin=PIN)
    out = ask(db, u.phone, "1", "5", PIN, "1", "3")
    assert out.startswith("END Thank you")
    s = db.query(PestSighting).one()
    assert s.species == "Fall Armyworm" and s.severity == "high" and s.status == "pending" and s.district == "Chipinge"
    assert ask(db, u.phone, "1", "5", PIN, "9x") == "END Invalid choice. Dial again to restart."


def test_borehole_report_is_pending_and_updates_not_stacks(db, clean):
    seed(db); u = make_user(db, "Chipinge", pin=PIN)
    assert ask(db, u.phone, "2", "2", PIN, "1", "3").startswith("END Thank you")
    ask(db, u.phone, "2", "2", PIN, "1", "4")
    reports = db.query(BoreholeReport).all()
    assert len(reports) == 1 and reports[0].status == "pending" and reports[0].new_status == "broken"
    assert db.query(Borehole).filter_by(name="Mutema Primary School Community Borehole").one().status == "working"


def test_sell_flow_creates_a_validated_listing(db, clean):
    u = make_user(db, "Chipinge", pin=PIN)
    assert ask(db, u.phone, "4", "2", PIN, "2", "Maize <script>", "1", "50", "0.3").startswith("CON Maize script 50kg $0.3")
    out = ask(db, u.phone, "4", "2", PIN, "2", "Maize <script>", "1", "50", "0.3", "2")
    assert out.startswith("END Listed!")
    m = db.query(MarketListing).one()
    assert m.title == "Maize script" and float(m.quantity) == 50 and m.share_phone is False and m.expires_at > datetime.now(timezone.utc)
    assert "Invalid number" in ask(db, u.phone, "4", "2", PIN, "2", "Maize", "1", "-5")
    assert "Invalid price" in ask(db, u.phone, "4", "2", PIN, "2", "Maize", "1", "5", "abc")


def test_insurance_screen_reflects_flag_and_real_enrolment(db, clean):
    from app.modules.settings_module.service import upsert_setting
    u = make_user(db, "Chipinge", pin=PIN)
    assert "open yet" in ask(db, u.phone, "4", "3")                      # flag OFF by default
    upsert_setting(db, "feature_flags", {"musika_insurance_enrollment": True, "ussd_gateway": True,
                                         "livestock_ai_photo_diagnosis": False}, None, str(u.id))
    try:
        assert "not enrolled" in ask(db, u.phone, "4", "3", PIN)
        from app.modules.musika.insurance_service import enroll
        enroll(db, str(u.id), "Chipinge", "2099-00", None, today=date(2099, 1, 5))
        out = ask(db, u.phone, "4", "3", PIN)
        assert "Cover 2099-00 Chipinge" in out and "No satellite data yet" in out
    finally:
        upsert_setting(db, "feature_flags", {"musika_insurance_enrollment": False, "ussd_gateway": True,
                                             "livestock_ai_photo_diagnosis": False}, None, str(u.id))


# ───────── exhaustive: every reachable screen <=160 chars and fake-free ─────────
@pytest.mark.parametrize("district", ["Bulawayo", "Masvingo", "Chipinge"])
def test_every_reachable_screen_fits_160_chars(db, clean, monkeypatch, district):
    monkeypatch.setattr(settings, "VET_SERVICES_CONTACT", "0242 700 000 (24h)")      # long real-looking number
    monkeypatch.setattr(settings, "AGRITEX_CONTACT", "0242 111 222")
    seed(db, district)
    from app.modules.settings_module.service import upsert_setting
    registered = make_user(db, district, pin=PIN)
    no_pin = make_user(db, district)
    unregistered = "+263774445555"
    inputs = ["1", "2", "3", "4", "5", "6", "7", "8", "Maize grain", "50", "2.5", "1000", "10000", "80", PIN, "7391"]
    texts, over, fakes, calls = set(), [], [], 0
    for phone in (registered.phone, no_pin.phone, unregistered):
        seen_screens = set()                       # each phone gets its own walk (different account state = different screens)
        queue = collections.deque([[]])
        while queue and calls < 20000:
            path = queue.popleft()
            # the walker deliberately tries wrong PINs; un-lock so it can keep exploring behind the PIN gate
            db.query(User).filter(User.id.in_([registered.id, no_pin.id])).update(
                {"pin_failed_attempts": 0, "pin_locked_until": None}, synchronize_session=False)
            db.commit()
            screen = H.route(db, phone, path); calls += 1
            if len(screen) > MAX_LEN: over.append((len(screen), path, screen))
            if any(f in screen for f in FAKE_MARKERS): fakes.append((path, screen))
            key = (screen, tuple(path[:2]))           # same text reached through a different flow is a different state
            if key in seen_screens or not screen.startswith("CON") or len(path) >= 10:
                continue
            seen_screens.add(key)
            for i in inputs:
                queue.append(path + [i])
        texts |= {t for t, _ in seen_screens}
        db.rollback()
    assert not over, over[:3]
    assert not fakes, fakes[:3]
    must_reach = ["CON Which pest?", "CON How bad?", "CON Status now?", "CON Which borehole?", "CON Unit:", "CON SMS alerts for your district",
                  "CON New 4-digit PIN", "CON Confirm new PIN", "CON Create a 4-digit PIN", "CON Confirm your PIN", "CON Your district:",
                  "CON Enter your PIN:", "CON Solar panel watts?", "CON Browse:", "CON Which crop?", "CON Which animal?"]
    missing = [m for m in must_reach if not any(t.startswith(m) for t in texts)]
    assert not missing, f"walk never reached: {missing}"                          # the walk really covered the tree
    db.query(User).filter(User.phone == unregistered).delete(); db.commit()


# ───────── PIN gate ─────────
def test_every_write_and_personal_screen_asks_for_the_pin_first(db, clean):
    seed(db); u = make_user(db, "Chipinge", pin=PIN)
    from app.modules.settings_module.service import upsert_setting
    for path in (("1", "5"), ("2", "2"), ("4", "2"), ("5", "1"), ("5", "2"), ("5", "3")):
        assert ask(db, u.phone, *path).startswith("CON Enter your PIN"), path
    assert db.query(PestSighting).count() == 0
    # public reads never ask
    for path in (("1", "1"), ("1", "2"), ("2", "1"), ("3", "1")):
        assert "PIN" not in ask(db, u.phone, *path), path


def test_wrong_pin_counts_down_then_locks_and_right_pin_is_refused_while_locked(db, clean):
    u = make_user(db, "Chipinge", pin=PIN)
    r1 = ask(db, u.phone, "1", "5", "0001x")
    assert "Wrong PIN" in r1 and "2 tries left" in r1
    assert "1 tries left" in ask(db, u.phone, "1", "5", "7777")
    locked = ask(db, u.phone, "1", "5", "6543")
    assert "Locked for 30 min" in locked
    assert "Locked for 30 min" in ask(db, u.phone, "1", "5", PIN)                      # correct PIN still refused
    db.expire_all()
    u = db.get(User, u.id)
    assert u.pin_locked_until is not None
    u.pin_locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)             # lock expires
    db.commit()
    assert ask(db, u.phone, "1", "5", PIN).startswith("CON Which pest?")
    db.expire_all()
    assert db.get(User, u.id).pin_failed_attempts == 0                                 # success resets the counter


def test_account_without_pin_creates_one_then_ends_session(db, clean):
    u = make_user(db, "Chipinge")                                      # e.g. registered through the web app: no PIN yet
    assert "Create a 4-digit PIN" in ask(db, u.phone, "1", "5")
    assert "Confirm your PIN" in ask(db, u.phone, "1", "5", PIN)
    out = ask(db, u.phone, "1", "5", PIN, PIN)
    assert out.startswith("END PIN saved")
    db.expire_all()
    assert db.get(User, u.id).pin_hash
    assert ask(db, u.phone, "1", "5", PIN).startswith("CON Which pest?")


def test_sms_alert_preference_and_pin_change_via_ussd(db, clean):
    u = make_user(db, "Chipinge", pin=PIN)
    assert "SMS alerts: ON" in ask(db, u.phone, "5")
    assert "Turn OFF" in ask(db, u.phone, "5", "2", PIN)
    assert "now" in ask(db, u.phone, "5", "2", PIN, "2") and "OFF" in ask(db, u.phone, "5", "2", PIN, "2")
    db.expire_all(); assert db.get(User, u.id).sms_alerts is False
    assert "New 4-digit PIN" in ask(db, u.phone, "5", "3", PIN)
    assert "PIN changed" in ask(db, u.phone, "5", "3", PIN, "7391", "7391")
    assert "Wrong PIN" in ask(db, u.phone, "1", "5", PIN)                              # old PIN no longer works
    assert ask(db, u.phone, "1", "5", "7391").startswith("CON Which pest?")
