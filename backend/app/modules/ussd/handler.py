"""
USSD session handler for KohwAI.

Africa's Talking sends the cumulative input as `text` ("1*2*3"), so the handler is stateless:
every request re-derives where the user is from that string. `0` = back, `9` = main menu.

Principles (repo-wide "no pretend data"):
  * every number on a screen comes from the database (persisted satellite readings, real
    boreholes/listings, the caller's own records) — nothing is hardcoded;
  * if data does not exist yet the screen says so plainly;
  * writes (pest report, borehole report, listing) need a registered phone and create *pending*
    records that follow the same validation rules as the web app;
  * each screen is <= 160 characters (asserted by tests).
Language: English only for now. Shona/Ndebele copy has not been written, so there is no
"change language" option rather than a fake one.
"""
import logging
import re
from datetime import date, datetime, timezone
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.mvura import Borehole, BoreholeReport
from app.models.musika import InsuranceEnrollment, MarketListing
from app.models.satellite import SatelliteReading
from app.models.user import User
from app.models.zunde import PestSighting
from app.modules.identity.schemas import normalise_phone
from app.modules.identity import pin as pinlib
from app.modules.identity.pin import PinResult
from app.core.config import settings
from app.modules.musika import insurance_service
from app.modules.musika.schemas import DEFAULT_LISTING_DAYS
from app.modules.settings_module.service import flag_enabled
from app.modules.ussd import menus
from app.modules.ussd.menus import MAIN_MENU
from app.modules.ussd.rules_engine import RulesEngine, CROP_SYMPTOMS, LIVESTOCK_SYMPTOMS, CROPS, ANIMALS, vet_contact, agritex_contact
from app.modules.zunde.pests import PEST_SPECIES
from app.modules.zunde.service import ONSET_5DAY_THRESHOLD_MM
from app.utils.audit import write_audit_log
from app.utils.satellite import DISTRICTS
from datetime import timedelta

logger = logging.getLogger(__name__)
rules = RulesEngine()

DLIST = list(DISTRICTS)                      # fixed order -> stable menu numbers
USSD_PESTS = [p for p in PEST_SPECIES if p not in ("Termites", "Other")][:7] + ["Other"]   # 1-7 + 8; digit 9 is reserved for "Menu"
STATUS_CODES = {"1": "working", "2": "low", "3": "dry", "4": "broken"}
UNITS = {"1": "kg", "2": "bag", "3": "head"}
LISTING_TYPES = {"1": "seed", "2": "produce"}


# ── navigation ───────────────────────────────────────────────────────────
def resolve(parts: list[str]) -> list[str]:
    """Apply 0=back / 9=main-menu to the cumulative input. At the very top, "0" means Help."""
    stack: list[str] = []
    for p in parts:
        if p == "9":
            stack = []
        elif p == "0":
            if stack:
                stack.pop()
            else:
                stack.append("0")        # root-level 0 = Help
        else:
            stack.append(p)
    return stack


def con(*lines: str) -> str:
    return "CON " + "\n".join(lines)


def end(*lines: str) -> str:
    return "END " + "\n".join(lines)


def finalize(resp: str) -> str:
    if len(resp) > 182:                         # hard carrier limit; tests keep us <=160 normally
        logger.warning("USSD screen too long (%d chars) — truncated", len(resp))
        resp = resp[:179] + "..."
    return resp


# ── helpers ──────────────────────────────────────────────────────────────
def _user(db: Session, phone: str) -> User | None:
    try:
        p = normalise_phone(phone.replace(" ", ""))
    except ValueError:
        return None
    return db.query(User).filter(User.phone == p).first()


def _district_step(args: list[str]):
    """Two-page district picker (digit 9 is reserved for Menu). -> (district|None, consumed, screen|None)"""
    page1, page2 = DLIST[:7], DLIST[7:]
    if not args:
        return None, 0, con("Your district:", *[f"{i}. {d}" for i, d in enumerate(page1, 1)], "8. More")
    a = args[0]
    if a.isdigit() and 1 <= int(a) <= len(page1):
        return page1[int(a) - 1], 1, None
    if a == "8":
        if len(args) == 1:
            return None, 1, con("Your district:", *[f"{i}. {d}" for i, d in enumerate(page2, 1)])
        b = args[1]
        if b.isdigit() and 1 <= int(b) <= len(page2):
            return page2[int(b) - 1], 2, None
    return None, 0, menus.INVALID


def _district_for(user: User | None, args: list[str]):
    """Registered users with a district use it; anyone else picks one inline. -> (district, rest_args, screen)"""
    if user and user.district in DISTRICTS:
        return user.district, args, None
    d, used, screen = _district_step(args)
    if d is None:
        return None, args, screen
    return d, args[used:], None


def _recent_readings(db: Session, district: str, n: int):
    return (db.query(SatelliteReading).filter(SatelliteReading.district == district,
                                              SatelliteReading.rainfall_mm.isnot(None))
            .order_by(SatelliteReading.reading_date.desc()).limit(n).all())


def _fmt_day(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"


def _num(s: str, lo: float, hi: float) -> float | None:
    try:
        v = float(s)
    except ValueError:
        return None
    return v if lo < v <= hi else None


# ── handler ──────────────────────────────────────────────────────────────
class USSDHandler:
    async def handle(self, session_id: str, phone: str, text: str, service_code: str) -> PlainTextResponse:
        parts = [p for p in text.split("*")] if text else []
        try:
            response = await run_in_threadpool(self._route_sync, phone, parts)
        except Exception:  # noqa: BLE001
            logger.exception("USSD error session=%s", session_id)
            response = "END An error occurred. Please try again later."
        return PlainTextResponse(content=finalize(response), media_type="text/plain")

    def _route_sync(self, phone: str, raw_parts: list[str]) -> str:
        db = SessionLocal()
        try:
            if not flag_enabled(db, "ussd_gateway"):
                return menus.UNAVAILABLE
            return self.route(db, phone, resolve(raw_parts))
        finally:
            db.close()

    def route(self, db: Session, phone: str, parts: list[str]) -> str:
        user = _user(db, phone)
        if not parts:
            return MAIN_MENU
        top, sub = parts[0], parts[1:]
        if top == "1":
            return self._zunde(db, user, phone, sub)
        if top == "2":
            return self._mvura(db, user, sub)
        if top == "3":
            return self._simba(db, user, sub)
        if top == "4":
            return self._musika(db, user, sub)
        if top == "5":
            return self._account(db, user, phone, sub)
        if top == "0":
            return end("KohwAI help", f"Crops: {agritex_contact()}", f"Animals: {vet_contact()}")
        return menus.INVALID

    # ── PIN gate ─────────────────────────────────────────────────────────
    def _pin_gate(self, db, user, args):
        """Personal data and every write need the caller's PIN, entered as the first input of that flow.
        -> (remaining_args, screen). If `screen` is not None, return it to the caller as-is.
        A PIN-less account (e.g. registered in the web app) creates one here, then the session ends: the cumulative
        USSD text would otherwise mix 'create' tokens with 'verify' tokens on the next request."""
        if not user.pin_hash:
            if not args:
                return args, con("Create a 4-digit PIN", "to protect your account:")
            if len(args) < 2:
                return args, con("Confirm your PIN:")
            if args[0] != args[1]:
                return args, end("PINs did not match.", "Please dial again.")
            try:
                pinlib.set_pin(db, user, args[0], actor_note="ussd")
            except ValueError as e:
                return args, end(str(e), "Dial again.")
            return args, end("PIN saved.", "Dial again and use it.")
        if not args:
            return args, con("Enter your PIN:")
        result, left = pinlib.check_pin(db, user.id, args[0])
        if result == PinResult.OK:
            return args[1:], None
        if result == PinResult.LOCKED:
            return args, end("Too many wrong PINs.", f"Locked for {settings.PIN_LOCK_MINUTES} min.")
        return args, end("Wrong PIN.", f"{left} tries left. Dial again.")

    # ── Zunde ────────────────────────────────────────────────────────────
    def _zunde(self, db, user, phone, sub):
        if not sub:
            return menus.ZUNDE_MENU
        sel, rest = sub[0], sub[1:]
        if sel == "1":
            return self._weather(db, user, rest)
        if sel == "2":
            return self._crop(rest)
        if sel == "3":
            return self._livestock(rest)
        if sel == "4":
            return self._planting(db, user, rest)
        if sel == "5":
            return self._pest_report(db, user, rest)
        return menus.INVALID

    def _weather(self, db, user, args):
        district, _rest, screen = _district_for(user, args)
        if not district:
            return screen
        rows = _recent_readings(db, district, 3)
        if not rows:
            return end(f"Weather - {district}", "No satellite data stored yet.", "Please try again later.")
        lines = [f"{_fmt_day(r.reading_date)}: {r.rainfall_mm:.1f}mm" + (f" {r.temp_max_c:.0f}C" if r.temp_max_c is not None else "")
                 for r in rows]
        return end(f"Recent weather - {district}", *lines, "Observed, not a forecast.")

    def _planting(self, db, user, args):
        district, _rest, screen = _district_for(user, args)
        if not district:
            return screen
        rows = _recent_readings(db, district, 5)
        if len(rows) < 3 or (date.today() - rows[0].reading_date).days > 5:
            return end(f"Planting - {district}", "Not enough recent rain data.", f"Ask {agritex_contact()}.")
        total = sum(float(r.rainfall_mm) for r in rows)
        verdict = "Rains look started." if total >= ONSET_5DAY_THRESHOLD_MM else "Rain still light - wait."
        return end(f"Planting - {district}", f"Rain, last {len(rows)} days: {total:.0f}mm", verdict, f"Confirm with {agritex_contact()}")

    def _crop(self, args):
        if not args:
            return con("Sick crop - symptom:", *[f"{c}. {short}" for c, _f, short in CROP_SYMPTOMS], "0. Back")
        symptom = args[0]
        if symptom not in {c for c, _f, _s in CROP_SYMPTOMS}:
            return menus.INVALID
        if len(args) < 2:
            return con("Which crop?", *[f"{c}. {l.split(' /')[0]}" for c, l in CROPS], "3. Other", "0. Back")
        if args[1] == "3":
            return end(f"No crop guide yet.", f"Ask {agritex_contact()}.")
        if args[1] not in {c for c, _l in CROPS}:
            return menus.INVALID
        r = rules.diagnose_crop(symptom, args[1])
        if not r["known"]:
            return end(r["ussd"])
        return end(f"Likely: {r['disease1']} or {r['disease2']}", r["ussd"], "Guide only. Confirm with Agritex.")

    def _livestock(self, args):
        if not args:
            return con("Sick animal - symptom:", *[f"{c}. {short}" for c, _f, short in LIVESTOCK_SYMPTOMS], "0. Back")
        symptom = args[0]
        if symptom not in {c for c, _f, _s in LIVESTOCK_SYMPTOMS}:
            return menus.INVALID
        menu = {str(i): code for i, (code, _l) in enumerate(ANIMALS, 1)}
        if len(args) < 2:
            return con("Which animal?", *[f"{i}. {l}" for i, (_c, l) in enumerate(ANIMALS, 1)],
                       f"{len(ANIMALS) + 1}. Other", "0. Back")
        if args[1] == str(len(ANIMALS) + 1):
            return end("No guide for this animal yet.", f"Contact {vet_contact()}.")
        if args[1] not in menu:
            return menus.INVALID
        r = rules.diagnose_livestock(symptom, menu[args[1]])
        if not r["known"]:
            return end(r["ussd"])
        return end(f"Likely: {r['disease']}" + (" (REPORTABLE)" if r["notifiable"] else ""), r["ussd"], "Guide only. Vet must confirm.")

    def _pest_report(self, db, user, args):
        if not user or user.district not in DISTRICTS:
            return menus.NOT_REGISTERED
        args, screen = self._pin_gate(db, user, args)
        if screen:
            return screen
        if not args:
            return con("Which pest?", *[f"{i}. {p.split(' (')[0]}" for i, p in enumerate(USSD_PESTS, 1)], "0. Back")
        if not (args[0].isdigit() and 1 <= int(args[0]) <= len(USSD_PESTS)):
            return menus.INVALID
        if len(args) < 2:
            return con("How bad?", "1. A few plants", "2. Part of field", "3. Whole field", "0. Back")
        sev = {"1": "low", "2": "medium", "3": "high"}.get(args[1])
        if not sev:
            return menus.INVALID
        species = USSD_PESTS[int(args[0]) - 1]
        s = PestSighting(user_id=user.id, species=species, severity=sev, district=user.district, status="pending")
        db.add(s)
        db.commit()
        return end("Thank you. Report sent to", f"{user.district} validators for checking.")

    # ── Mvura ────────────────────────────────────────────────────────────
    def _mvura(self, db, user, sub):
        if not sub:
            return menus.MVURA_MENU
        sel, rest = sub[0], sub[1:]
        if sel == "3":
            return menus.WATER_TIPS
        if sel == "1":
            district, _r, screen = _district_for(user, rest)
            if not district:
                return screen
            bhs = self._district_boreholes(db, district)[:4]
            if not bhs:
                return end(f"Boreholes - {district}", "None registered yet.")
            lines = [f"{b.name[:16]}: {b.status}" + ("" if b.last_verified else " (unverified)") for b in bhs]
            return end(f"Boreholes - {district}", *lines)
        if sel == "2":
            if not user or user.district not in DISTRICTS:
                return menus.NOT_REGISTERED
            rest, screen = self._pin_gate(db, user, rest)
            if screen:
                return screen
            bhs = self._district_boreholes(db, user.district)[:7]
            if not bhs:
                return end("No boreholes registered", "in your district yet.")
            if not rest:
                return con("Which borehole?", *[f"{i}. {b.name[:20]}" for i, b in enumerate(bhs, 1)], "0. Back")
            if not (rest[0].isdigit() and 1 <= int(rest[0]) <= len(bhs)):
                return menus.INVALID
            if len(rest) < 2:
                return con("Status now?", "1. Working", "2. Low water", "3. Dry", "4. Broken", "0. Back")
            status = STATUS_CODES.get(rest[1])
            if not status:
                return menus.INVALID
            bh = bhs[int(rest[0]) - 1]
            existing = db.query(BoreholeReport).filter(BoreholeReport.borehole_id == bh.id, BoreholeReport.reported_by == user.id,
                                                       BoreholeReport.status == "pending").first()
            if existing:
                existing.new_status = status
            else:
                db.add(BoreholeReport(borehole_id=bh.id, reported_by=user.id, new_status=status, status="pending", validated=False))
            db.commit()
            return end("Thank you. Shown as", "unverified until a validator", "confirms it.")
        return menus.INVALID

    @staticmethod
    def _district_boreholes(db, district):
        order = {"working": 0, "low": 1, "broken": 2, "dry": 3}
        rows = db.query(Borehole).filter(Borehole.district == district).all()
        return sorted(rows, key=lambda b: (order.get(b.status, 9), b.name))

    # ── Simba ────────────────────────────────────────────────────────────
    def _simba(self, db, user, sub):
        if not sub:
            return menus.SIMBA_MENU
        sel, rest = sub[0], sub[1:]
        if sel == "3":
            return menus.ENERGY_TIPS
        if sel == "1":
            district, _r, screen = _district_for(user, rest)
            if not district:
                return screen
            irr = self._irradiance(db, district)
            if irr is None:
                return end(f"Sunshine - {district}", "No solar data stored yet.")
            return end(f"Sunshine - {district}", f"Avg last 3 days: {irr:.1f} kWh/m2/day", "Higher = better charging.")
        if sel == "2":
            return self._battery(db, user, rest)
        return menus.INVALID

    @staticmethod
    def _irradiance(db, district) -> float | None:
        rows = (db.query(SatelliteReading.solar_kwh_m2).filter(SatelliteReading.district == district,
                SatelliteReading.solar_kwh_m2.isnot(None)).order_by(SatelliteReading.reading_date.desc()).limit(3).all())
        vals = [float(r[0]) for r in rows]
        return sum(vals) / len(vals) if vals else None

    def _battery(self, db, user, args):
        from app.modules.simba.service import simulate_battery, FALLBACK_IRRADIANCE_KWH_M2, ZIMBABWE_UTC_OFFSET
        specs = [("Solar panel watts?", 1, 20000), ("Battery capacity (Wh)?", 10, 200000),
                 ("Battery now (%)?", 1, 100), ("Average load (watts)?", 1, 20000)]   # 0 is the Back key, so it cannot be an answer
        vals = []
        for i, (question, lo, hi) in enumerate(specs):
            if i >= len(args):
                return con(question, "0. Back")
            try:
                v = float(args[i])
            except ValueError:
                v = None
            if v is None or not (lo <= v <= hi):
                return end("Invalid number.", "Please dial again.")
            vals.append(v)
        panel, cap, pct, load = vals
        district = user.district if user and user.district in DISTRICTS else None
        irr = self._irradiance(db, district) if district else None
        used = irr if irr is not None else FALLBACK_IRRADIANCE_KWH_M2
        now = datetime.now(timezone.utc).astimezone(timezone(ZIMBABWE_UTC_OFFSET))
        f = simulate_battery(cap, panel, pct, load, used, now.hour + now.minute / 60.0)
        by = {x["hours_from_now"]: x["estimated_battery_pct"] for x in f}
        src = "live sun data" if irr is not None else "typical sun"
        return end(f"Battery now {pct:.0f}%", f"In 24h: ~{by[24]:.0f}%", f"In 48h: ~{by[48]:.0f}%", f"Estimate ({src}).")

    # ── Musika ───────────────────────────────────────────────────────────
    def _musika(self, db, user, sub):
        if not sub:
            return menus.MUSIKA_MENU
        sel, rest = sub[0], sub[1:]
        if sel == "1":
            return self._browse(db, user, rest)
        if sel == "2":
            return self._sell(db, user, rest)
        if sel == "3":
            return self._insurance(db, user, rest)
        return menus.INVALID

    def _browse(self, db, user, args):
        if not args:
            return con("Browse:", "1. Seeds", "2. Produce", "0. Back")
        t = LISTING_TYPES.get(args[0])
        if not t:
            return menus.INVALID
        district, _r, screen = _district_for(user, args[1:])
        if not district:
            return screen
        now = datetime.now(timezone.utc)
        rows = (db.query(MarketListing).filter(MarketListing.is_active.is_(True), MarketListing.type == t,
                MarketListing.district == district, or_(MarketListing.expires_at.is_(None), MarketListing.expires_at > now))
                .order_by(MarketListing.created_at.desc()).limit(3).all())
        if not rows:
            return end(f"No {t} listings in", f"{district} right now.")
        phones = {}
        ids = {r.seller_id for r in rows if r.share_phone and r.seller_id}
        if ids:
            phones = {u.id: u.phone for u in db.query(User).filter(User.id.in_(ids)).all()}
        lines = []
        for r in rows:
            line = f"{r.title[:14]} {float(r.quantity):g}{r.unit} ${float(r.price_usd):g}"
            if r.share_phone and phones.get(r.seller_id):
                line += f" 0{phones[r.seller_id][-9:]}"        # local dialling format 07xxxxxxxx
            lines.append(line)
        return end(f"{t.title()} - {district}", *lines)

    def _sell(self, db, user, args):
        if not user or user.district not in DISTRICTS:
            return menus.NOT_REGISTERED
        args, screen = self._pin_gate(db, user, args)
        if screen:
            return screen
        steps = len(args)
        if steps == 0:
            return con("Sell:", "1. Seeds", "2. Produce", "0. Back")
        t = LISTING_TYPES.get(args[0])
        if not t:
            return menus.INVALID
        if steps == 1:
            return con("What are you selling?", "(e.g. Maize grain)")
        title = re.sub(r"[^A-Za-z0-9 .,'-]", "", args[1]).strip()[:40]
        if len(title) < 2:
            return end("Invalid name.", "Please dial again.")
        if steps == 2:
            return con("Unit:", "1. kg", "2. bag", "3. head")
        unit = UNITS.get(args[2])
        if not unit:
            return menus.INVALID
        if steps == 3:
            return con(f"How many {unit}?")
        qty = _num(args[3], 0, 10_000_000)
        if qty is None:
            return end("Invalid number.", "Please dial again.")
        if steps == 4:
            return con(f"Price per {unit} (USD)?")
        try:
            price = float(args[4])
        except ValueError:
            price = -1
        if not (0 <= price <= 1_000_000):
            return end("Invalid price.", "Please dial again.")
        if steps == 5:
            return con(f"{title[:20]} {qty:g}{unit} ${price:g}", "1. Post, show my phone", "2. Post, hide my phone", "0. Back")
        if args[5] not in ("1", "2"):
            return menus.INVALID
        db.add(MarketListing(seller_id=user.id, type=t, title=title, quantity=qty, unit=unit, price_usd=price,
                             district=user.district, is_active=True, share_phone=(args[5] == "1"),
                             expires_at=datetime.now(timezone.utc) + timedelta(days=DEFAULT_LISTING_DAYS)))
        db.commit()
        return end("Listed! Visible to buyers", f"in {user.district} for {DEFAULT_LISTING_DAYS} days.")

    def _insurance(self, db, user, args):
        if not user:
            return menus.NOT_REGISTERED
        if not flag_enabled(db, "musika_insurance_enrollment"):
            return end("Drought cover is not", "open yet. We will tell you.")
        _rest, screen = self._pin_gate(db, user, args)     # insurance details are personal and financial
        if screen:
            return screen
        e = insurance_service.get_my_enrollment(db, str(user.id))
        if not e:
            return end("You are not enrolled.", "Enrol in the KohwAI app.")
        run = insurance_service.qualifying_run(db, e.district, insurance_service.settings.INSURANCE_DROUGHT_THRESHOLD)
        need = insurance_service.settings.INSURANCE_MIN_CONSECUTIVE_DAYS
        paid = [p for p in insurance_service.list_my_payouts(db, str(user.id)) if p.status != "void_duplicate"]
        if paid:
            return end(f"Cover {e.season} {e.district}", f"Payout USD {float(paid[0].amount_usd):.2f}: {paid[0].status.replace('_', ' ')}")
        if run["latest"] is None:
            return end(f"Cover {e.season} {e.district}", "No satellite data yet.", f"Payout if dry {need}+ days.")
        return end(f"Cover {e.season} {e.district}", f"Dry days in a row: {run['run_days']} of {need}",
                   f"Payout USD {float(e.payout_amount_usd):.2f} if met.")

    # ── My account ───────────────────────────────────────────────────────
    def _account(self, db, user, phone, sub):
        if user:
            if not sub:
                return con(f"Registered: {user.district or 'no district'}", f"SMS alerts: {'ON' if user.sms_alerts else 'OFF'}",
                           "1. Change district", "2. SMS alerts on/off", "3. Change PIN", "0. Back")
            sel, rest = sub[0], sub[1:]
            rest, screen = self._pin_gate(db, user, rest)
            if screen:
                return screen
            if sel == "1":
                d, _used, screen = _district_step(rest)
                if d is None:
                    return screen
                before = user.district
                user.district = d
                db.commit()
                write_audit_log(db, str(user.id), "ussd.change_district", "user", str(user.id), before=before, after=d)
                return end(f"District set to {d}.")
            if sel == "2":
                if not rest:
                    return con("SMS alerts for your district:", "1. Turn ON", "2. Turn OFF", "0. Back")
                if rest[0] not in ("1", "2"):
                    return menus.INVALID
                user.sms_alerts = rest[0] == "1"
                db.commit()
                write_audit_log(db, str(user.id), "ussd.sms_alerts", "user", str(user.id), after=user.sms_alerts)
                return end("SMS alerts are now", "ON." if user.sms_alerts else "OFF.")
            if sel == "3":
                if not rest:
                    return con("New 4-digit PIN:")
                if len(rest) < 2:
                    return con("Confirm new PIN:")
                if rest[0] != rest[1]:
                    return end("PINs did not match.", "Please dial again.")
                try:
                    pinlib.set_pin(db, user, rest[0], actor_note="ussd")
                except ValueError as e:
                    return end(str(e), "Dial again.")
                return end("PIN changed.")
            return menus.INVALID
        # not registered: consent -> district -> PIN
        if not sub:
            return con("Register free. By joining you", "accept the KohwAI Terms and", "Privacy Policy and get SMS", "alerts for your district.", "1. I accept", "0. Back")
        if sub[0] != "1":
            return menus.INVALID
        d, used, screen = _district_step(sub[1:])
        if d is None:
            return screen
        pins = sub[1 + used:]
        if not pins:
            return con("Create a 4-digit PIN", "to protect your account:")
        if len(pins) < 2:
            return con("Confirm your PIN:")
        if pins[0] != pins[1]:
            return end("PINs did not match.", "Please dial again.")
        try:
            p = normalise_phone(phone.replace(" ", ""))
            pin_hash = pinlib.hash_for_new_user(p, pins[0])
        except ValueError as e:
            return end(str(e), "Dial again.")
        u = User(phone=p, district=d, language="en", roles=["farmer"], terms_accepted_at=datetime.now(timezone.utc),
                 terms_version=settings.TERMS_VERSION, pin_hash=pin_hash)
        db.add(u)
        db.commit()
        write_audit_log(db, str(u.id), "ussd.register", "user", str(u.id), after={"district": d, "terms_version": settings.TERMS_VERSION})
        return end(f"Welcome! Registered in {d}.", "Dial again to use all services.")
