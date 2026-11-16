"""Batch 3A: alert dispatch, SMS gateway parsing, risk worker, realtime WebSocket, readiness."""
import json
import threading
import time
from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.core.redis_client import redis_client, publish_alert
from app.models.alerts import Alert, AlertDelivery
from app.models.satellite import SatelliteReading
from app.models.zunde import PestSighting
from app.modules.alerts import dispatch
from app.utils import sms
from app.utils.sms import SmsResult
from tests.conftest import make_user, auth


def mk_alert(db, district="Chipinge", severity="red", title="Armyworm outbreak", body="Check your maize fields today.", **kw):
    a = Alert(pillar="zunde", type="pest", severity=severity, title=title, body=body, district=district, **kw)
    db.add(a); db.commit(); db.refresh(a)
    return a


class FakeGateway:
    def __init__(self, fail=(), permanent=()):
        self.calls, self.fail, self.permanent = [], set(fail), set(permanent)

    def __call__(self, recipients, message):
        self.calls.append((list(recipients), message))
        return {r: (SmsResult(False, "InvalidPhoneNumber", True) if r in self.permanent else
                    SmsResult(False, "InsufficientBalance") if r in self.fail else SmsResult(True, "Success")) for r in recipients}

    @property
    def all_recipients(self):
        return [r for c, _ in self.calls for r in c]


# ───────────── who gets an SMS ─────────────
def test_only_consented_opted_in_active_farmers_in_the_district_are_messaged(db, clean):
    ok = make_user(db, "Chipinge")
    make_user(db, "Chipinge", consent=False)                  # never accepted the terms
    make_user(db, "Chipinge", sms_alerts=False)               # switched alerts off
    make_user(db, "Binga")                                    # other district
    gone = make_user(db, "Chipinge"); gone.is_active = False; db.commit()
    a = mk_alert(db); gw = FakeGateway()
    res = dispatch.dispatch_alert(db, a, gateway=gw)
    assert gw.all_recipients == [ok.phone] and res["sent"] == 1
    d = db.query(AlertDelivery).one()
    assert d.status == "sent" and d.sent_at is not None and d.provider_status == "Success"
    db.refresh(a)
    assert a.dispatched_at is not None and a.sms_sent is True and a.recipient_count == 1


def test_rerun_never_double_sends(db, clean):
    make_user(db, "Chipinge"); a = mk_alert(db); gw = FakeGateway()
    dispatch.dispatch_alert(db, a, gateway=gw)
    dispatch.dispatch_alert(db, a, gateway=gw)
    assert len(gw.all_recipients) == 1 and db.query(AlertDelivery).count() == 1


def test_failures_are_recorded_retried_and_given_up_on_honestly(db, clean):
    good, flaky, dead = make_user(db), make_user(db), make_user(db)
    a = mk_alert(db)
    gw = FakeGateway(fail=[flaky.phone], permanent=[dead.phone])
    r1 = dispatch.dispatch_alert(db, a, gateway=gw)
    assert r1["sent"] == 1 and r1["failed"] == 2 and r1["will_retry"] == 1                   # dead number is NOT retried
    db.refresh(a); assert a.dispatched_at is None                                           # still has retryable work
    by = {d.user_id: d for d in db.query(AlertDelivery)}
    assert by[good.id].status == "sent" and by[flaky.id].status == "failed" and by[dead.id].attempts == settings.ALERT_SMS_MAX_ATTEMPTS
    gw2 = FakeGateway(fail=[flaky.phone])
    dispatch.dispatch_alert(db, a, gateway=gw2); dispatch.dispatch_alert(db, a, gateway=gw2)
    assert gw2.all_recipients == [flaky.phone, flaky.phone]                                  # only the flaky one, up to 3 attempts total
    db.refresh(a); assert a.dispatched_at is not None                                       # gave up -> finished
    assert {d.user_id: d.status for d in db.query(AlertDelivery)}[flaky.id] == "failed"
    gw3 = FakeGateway(); dispatch.dispatch_alert(db, a, gateway=gw3)
    assert gw3.calls == []                                                                   # nothing left to try


def test_daily_cap_protects_farmers_from_sms_spam(db, clean):
    u = make_user(db)
    gw = FakeGateway()
    for i in range(settings.ALERT_SMS_DAILY_CAP + 2):
        dispatch.dispatch_alert(db, mk_alert(db, title=f"Alert {i}"), gateway=gw)
    assert len(gw.all_recipients) == settings.ALERT_SMS_DAILY_CAP
    assert db.query(AlertDelivery).filter_by(status="skipped_cap").count() == 2


def test_only_fresh_severe_alerts_are_selected(db, clean):
    now = datetime.now(timezone.utc)
    fresh = mk_alert(db, title="fresh")
    mk_alert(db, severity="amber", title="amber is in-app only")
    mk_alert(db, severity="green", title="green")
    old = mk_alert(db, title="old"); old.created_at = now - timedelta(hours=settings.ALERT_MAX_AGE_HOURS + 1); db.commit()
    expired = mk_alert(db, title="expired", expires_at=now - timedelta(minutes=1))
    done = mk_alert(db, title="done"); done.dispatched_at = now; db.commit()
    assert [a.title for a in dispatch.pending_alerts(db)] == ["fresh"]
    db.rollback()


def test_unvalidated_community_alert_is_held_until_a_validator_approves_a_report(db, clean):
    make_user(db, "Chipinge")
    a = mk_alert(db, extra_data={"requires_validation": True, "species": "Aphids"}, source="intelligence")
    gw = FakeGateway()
    assert "held" in dispatch.dispatch_alert(db, a, gateway=gw) and gw.calls == []
    reporter = make_user(db, "Chipinge")
    db.add(PestSighting(user_id=reporter.id, species="Aphids", severity="high", district="Chipinge", status="pending")); db.commit()
    assert "held" in dispatch.dispatch_alert(db, a, gateway=gw)                          # pending is not enough
    db.query(PestSighting).update({"status": "approved"}); db.commit()
    assert dispatch.dispatch_alert(db, a, gateway=gw)["sent"] == 2 and len(gw.calls) == 1


def test_sms_text_is_one_gsm_segment(db):
    long_body = "A" * 400
    a = Alert(severity="darkRed", title="Anthrax — reported near you", body=f"Don’t touch carcasses… {long_body}", district="X")
    t = dispatch.sms_text(a)
    assert len(t) <= 160 and t.startswith("KohwAI EMERGENCY:") and t.isascii() and t.endswith("...")
    settings.USSD_SERVICE_CODE = "*123#"
    try:
        t2 = dispatch.sms_text(Alert(severity="red", title="T", body="short", district="X"))
        assert t2.endswith(" Dial *123#") and len(t2) <= 160
    finally:
        settings.USSD_SERVICE_CODE = ""


def test_recipients_are_batched(db, clean, monkeypatch):
    monkeypatch.setattr(settings, "ALERT_SMS_BATCH", 3)
    for _ in range(7): make_user(db, "Chipinge")
    gw = FakeGateway()
    dispatch.dispatch_alert(db, mk_alert(db), gateway=gw)
    assert sorted(len(c) for c, _ in gw.calls) == [1, 3, 3]


# ───────────── the real gateway parser ─────────────
class _Resp:
    def __init__(self, j): self._j = j
    def raise_for_status(self): pass
    def json(self): return self._j


def test_gateway_response_is_parsed_per_recipient(monkeypatch):
    monkeypatch.setattr(settings, "AT_API_KEY", "k")
    payload = {"SMSMessageData": {"Message": "Sent to 1/3", "Recipients": [
        {"number": "+263771000001", "statusCode": 101, "status": "Success"},
        {"number": "+263771000002", "statusCode": 403, "status": "InvalidPhoneNumber"},
        {"number": "+263771000003", "statusCode": 405, "status": "InsufficientBalance"}]}}
    monkeypatch.setattr(sms.requests, "post", lambda *a, **k: _Resp(payload))
    r = sms.send_sms_detailed(["+263771000001", "+263771000002", "+263771000003", "+263771000004"], "hi")
    assert r["+263771000001"].ok
    assert not r["+263771000002"].ok and r["+263771000002"].permanent
    assert not r["+263771000003"].ok and not r["+263771000003"].permanent
    assert not r["+263771000004"].ok and r["+263771000004"].status == "not_in_gateway_response"   # never assumed delivered
    assert sms.send_sms(["+263771000001"], "x") is True
    assert sms.send_sms(["+263771000001", "+263771000002"], "x") is False


def test_gateway_outage_is_a_retryable_failure_for_everyone(monkeypatch):
    monkeypatch.setattr(settings, "AT_API_KEY", "k")
    def boom(*a, **k): raise ConnectionError("down")
    monkeypatch.setattr(sms.requests, "post", boom)
    r = sms.send_sms_detailed(["+263771000001"], "hi")
    assert r["+263771000001"] == SmsResult(False, "gateway_error", False)


# ───────────── worker + realtime ─────────────
def test_worker_without_gateway_still_pushes_realtime_but_sends_no_sms(db, clean, monkeypatch):
    from app.workers import alerts as worker
    make_user(db, "Chipinge"); a = mk_alert(db)
    monkeypatch.setattr(settings, "AT_API_KEY", "")
    pubsub = redis_client.pubsub(); pubsub.subscribe("alerts:Chipinge"); pubsub.get_message(timeout=1)
    out = worker.dispatch_pending_alerts.run()
    assert out["broadcast"] == 1 and out["sms_skipped"] == "no_gateway"
    msg = None
    for _ in range(10):
        msg = pubsub.get_message(timeout=0.5)
        if msg and msg["type"] == "message": break
    assert msg and json.loads(msg["data"])["title"] == "Armyworm outbreak"
    db.expire_all()
    a = db.get(Alert, a.id)
    assert a.ws_broadcast is True and a.dispatched_at is None and db.query(AlertDelivery).count() == 0   # SMS still pending, nothing claimed


def test_worker_with_gateway_sends_sms(db, clean, monkeypatch):
    from app.workers import alerts as worker
    u = make_user(db, "Chipinge"); mk_alert(db)
    gw = FakeGateway()
    monkeypatch.setattr(settings, "AT_API_KEY", "k")
    monkeypatch.setattr(dispatch, "send_sms_detailed", gw)
    out = worker.dispatch_pending_alerts.run()
    assert gw.all_recipients == [u.phone] and out["sms"][0]["sent"] == 1


async def test_creating_an_alert_queues_immediate_dispatch(client, db, clean):
    admin = make_user(db, roles=("admin",))
    redis_client.delete("default")
    r = await client.post("/api/v1/alerts", headers=auth(admin), json={
        "pillar": "zunde", "type": "pest", "severity": "red", "title": "Armyworm", "body": "Check fields", "district": "Chipinge"})
    assert r.status_code == 200
    assert redis_client.llen("default") == 1


# ───────────── risk worker: no more fabricated 100/100 alarms ─────────────
def test_risk_worker_does_not_invent_scores_and_alerts_only_when_enabled(db, clean, monkeypatch):
    from app.workers import risk_model
    out = risk_model.calculate_district_risk_scores.run()
    assert set(out.values()) == {"insufficient data"} and db.query(Alert).count() == 0       # old code: 100.0 for every district
    for i in range(10):
        db.add(SatelliteReading(district="Binga", reading_date=date.today() - timedelta(days=i), source="nasa_power", rainfall_mm=30.0))
    db.commit()
    out = risk_model.calculate_district_risk_scores.run()
    assert out["Binga"] == 75.0 and out["Chipinge"] == "insufficient data"
    assert db.query(Alert).count() == 0                                                         # alerts OFF by default
    monkeypatch.setattr(settings, "RISK_MODEL_ALERTS_ENABLED", True)
    risk_model.calculate_district_risk_scores.run(); risk_model.calculate_district_risk_scores.run()
    alerts = db.query(Alert).all()
    assert len(alerts) == 1 and alerts[0].severity == "amber" and alerts[0].extra_data["heuristic"] is True   # deduped, in-app only


def test_outbreak_alert_from_intelligence_requires_validation_before_sms(db, clean):
    from app.modules.intelligence import service
    us = [make_user(db) for _ in range(3)]
    for u in us:
        db.add(PestSighting(user_id=u.id, species="Aphids", severity="high", district="Chipinge", status="pending"))
    db.commit()
    service.evaluate_pest_outbreak(db, "Chipinge")
    a = db.query(Alert).one()
    assert a.extra_data == {"requires_validation": True, "species": "Aphids"} and a.expires_at is not None


# ───────────── WebSocket ─────────────
def _ws_client():
    from starlette.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_websocket_requires_auth_and_district_match_and_delivers_messages(db):
    farmer = make_user(db, "Chipinge"); admin = make_user(db, "Harare", roles=("admin",))
    from tests.conftest import auth as _auth
    token = lambda u: _auth(u)["Authorization"].split()[1]
    c = _ws_client()
    # no/invalid token
    with c.websocket_connect("/ws/alerts/Chipinge") as ws:
        ws.send_json({"token": "garbage"})
        with pytest.raises(Exception): ws.receive_json()
    # someone else's district
    with c.websocket_connect("/ws/alerts/Binga") as ws:
        ws.send_json({"token": token(farmer)})
        with pytest.raises(Exception): ws.receive_json()
    # own district: gets live alerts
    with c.websocket_connect("/ws/alerts/Chipinge") as ws:
        ws.send_json({"token": token(farmer)})
        assert ws.receive_json() == {"type": "subscribed", "district": "Chipinge"}
        publish_alert("alerts:Chipinge", {"title": "live!"})
        assert json.loads(ws.receive_text())["title"] == "live!"
    # admin may listen anywhere
    with c.websocket_connect("/ws/alerts/Binga") as ws:
        ws.send_json({"token": token(admin)})
        assert ws.receive_json()["district"] == "Binga"


def test_websocket_rejects_refresh_tokens(db):
    from app.core.security import create_refresh_token
    farmer = make_user(db, "Chipinge")
    with _ws_client().websocket_connect("/ws/alerts/Chipinge") as ws:
        ws.send_json({"token": create_refresh_token(str(farmer.id))})
        with pytest.raises(Exception): ws.receive_json()


# ───────────── readiness / prod hardening ─────────────
async def test_readiness_reports_dependencies(client, monkeypatch):
    r = await client.get("/health/ready")
    assert r.status_code == 200 and r.json() == {"status": "ready", "database": "ok", "redis": "ok"}
    from app.core import redis_client as rc
    monkeypatch.setattr(rc.redis_client, "ping", lambda: (_ for _ in ()).throw(ConnectionError("down")))
    r = await client.get("/health/ready")
    assert r.status_code == 503 and r.json()["redis"] == "down" and r.json()["status"] == "degraded"
    assert (await client.get("/health")).status_code == 200                                    # liveness is independent


def test_api_docs_are_off_outside_development():
    import importlib, app.main as m
    from app.core.config import settings as s
    old = s.ENVIRONMENT
    try:
        s.ENVIRONMENT = "production"
        reloaded = importlib.reload(m)
        assert reloaded.app.docs_url is None and reloaded.app.openapi_url is None
    finally:
        s.ENVIRONMENT = old
        importlib.reload(m)
