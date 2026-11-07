"""Alert dispatch: turns Alert rows into SMS (and real-time WebSocket pushes).

Rules (each one exists because of a way this could hurt farmers or waste their money):
  * only people who ACCEPTED the terms and have SMS alerts switched on are messaged;
  * only severe alerts (ALERT_SMS_SEVERITIES) go out by SMS; everything else is in-app only;
  * at most ALERT_SMS_DAILY_CAP alert SMS per farmer per rolling 24h;
  * alerts older than ALERT_MAX_AGE_HOURS are never sent (e.g. after an outage — stale warnings are noise);
  * idempotent: one delivery row per (alert, farmer); a crash or re-run never double-sends;
  * unvalidated community claims (alerts flagged requires_validation) are held until a validator has approved
    at least one matching report, so a handful of fake accounts cannot trigger a district-wide SMS;
  * every delivery outcome is recorded truthfully, including failures.
"""
import json
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis_client import publish_alert
from app.models.alerts import Alert, AlertDelivery
from app.models.user import User
from app.models.zunde import PestSighting
from app.utils.sms import send_sms_detailed

logger = logging.getLogger(__name__)

SMS_LEN = 160
LABELS = {"red": "URGENT", "darkRed": "EMERGENCY"}


def sms_severities() -> set[str]:
    return {s.strip() for s in settings.ALERT_SMS_SEVERITIES.split(",") if s.strip()}


def _gsm_safe(text: str) -> str:
    """Keep to plain GSM-friendly characters: one smart quote or dash would switch the SMS to UCS-2 (70 chars/part)."""
    text = (text.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
                .replace("\u2013", "-").replace("\u2014", "-").replace("\u2026", "..."))
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def sms_text(alert: Alert) -> str:
    prefix = f"KohwAI {LABELS.get(alert.severity, 'ALERT')}: "
    suffix = f" Dial {settings.USSD_SERVICE_CODE}" if settings.USSD_SERVICE_CODE else ""
    body = _gsm_safe(re.sub(r"\s+", " ", f"{alert.title}. {alert.body}")).strip()
    room = SMS_LEN - len(prefix) - len(suffix)
    if len(body) > room:
        body = body[: room - 3].rstrip() + "..."
    return prefix + body + suffix


def _validated(db: Session, alert: Alert) -> bool:
    """Alerts built from community reports need at least one approved report behind them before SMS."""
    extra = alert.extra_data or {}
    if not extra.get("requires_validation"):
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    return db.query(PestSighting.id).filter(
        PestSighting.district == alert.district, PestSighting.species == extra.get("species"),
        PestSighting.status == "approved", PestSighting.created_at >= cutoff).first() is not None


def pending_alerts(db: Session, now: datetime | None = None) -> list[Alert]:
    now = now or datetime.now(timezone.utc)
    return (db.query(Alert)
            .filter(Alert.is_active.is_(True), Alert.dispatched_at.is_(None), Alert.severity.in_(sms_severities()),
                    Alert.created_at >= now - timedelta(hours=settings.ALERT_MAX_AGE_HOURS))
            .filter((Alert.expires_at.is_(None)) | (Alert.expires_at > now))
            .order_by(Alert.created_at)
            .with_for_update(skip_locked=True).all())      # two workers never grab the same alert


def dispatch_alert(db: Session, alert: Alert, gateway=None, now: datetime | None = None) -> dict:
    gateway = gateway or send_sms_detailed          # resolved at call time so tests/other gateways can be swapped in
    now = now or datetime.now(timezone.utc)
    if not _validated(db, alert):
        return {"alert": str(alert.id), "held": "awaiting validator approval"}

    farmers = (db.query(User).filter(User.district == alert.district, User.is_active.is_(True),
                                     User.sms_alerts.is_(True), User.terms_accepted_at.isnot(None)).all())
    rows = {d.user_id: d for d in db.query(AlertDelivery).filter(AlertDelivery.alert_id == alert.id, AlertDelivery.channel == "sms")}
    sent_24h = dict(db.query(AlertDelivery.user_id, func.count()).filter(
        AlertDelivery.channel == "sms", AlertDelivery.status == "sent", AlertDelivery.sent_at >= now - timedelta(hours=24))
        .group_by(AlertDelivery.user_id).all())

    todo: list[User] = []
    for u in farmers:
        d = rows.get(u.id)
        if d and (d.status in ("sent", "skipped_cap") or d.attempts >= settings.ALERT_SMS_MAX_ATTEMPTS):
            continue
        if not d and sent_24h.get(u.id, 0) >= settings.ALERT_SMS_DAILY_CAP:
            db.add(AlertDelivery(alert_id=alert.id, user_id=u.id, channel="sms", status="skipped_cap", attempts=0))
            continue
        todo.append(u)

    text, sent, failed = sms_text(alert), 0, 0
    for i in range(0, len(todo), settings.ALERT_SMS_BATCH):
        chunk = todo[i:i + settings.ALERT_SMS_BATCH]
        results = gateway([u.phone for u in chunk], text)
        for u in chunk:
            r = results.get(u.phone)
            d = rows.get(u.id) or AlertDelivery(alert_id=alert.id, user_id=u.id, channel="sms", attempts=0)
            d.attempts = (d.attempts or 0) + 1
            d.provider_status = r.status if r else "no_result"
            if r and r.ok:
                d.status, d.sent_at, d.error = "sent", now, None
                sent += 1
            else:
                d.status, d.error = "failed", d.provider_status
                if r and r.permanent:
                    d.attempts = settings.ALERT_SMS_MAX_ATTEMPTS      # don't keep retrying a dead number
                failed += 1
            db.add(d)
        db.flush()

    retryable = db.query(AlertDelivery).filter(
        AlertDelivery.alert_id == alert.id, AlertDelivery.status == "failed",
        AlertDelivery.attempts < settings.ALERT_SMS_MAX_ATTEMPTS).count()
    alert.sms_sent = bool(alert.sms_sent) or sent > 0
    alert.recipient_count = (alert.recipient_count or 0) + sent
    if retryable == 0:
        alert.dispatched_at = now
    db.commit()
    return {"alert": str(alert.id), "recipients": len(farmers), "sent": sent, "failed": failed, "will_retry": retryable}


def broadcast_realtime(db: Session, now: datetime | None = None) -> int:
    """Publish not-yet-broadcast alerts (ANY severity) to the district's WebSocket channel."""
    now = now or datetime.now(timezone.utc)
    alerts = (db.query(Alert).filter(Alert.is_active.is_(True), Alert.ws_broadcast.is_(False),
                                     Alert.created_at >= now - timedelta(hours=settings.ALERT_MAX_AGE_HOURS))
              .with_for_update(skip_locked=True).all())
    for a in alerts:
        try:
            publish_alert(f"alerts:{a.district}", {"id": str(a.id), "type": a.type, "severity": a.severity, "title": a.title,
                                                   "body": a.body, "district": a.district, "pillar": a.pillar,
                                                   "createdAt": a.created_at.isoformat() if a.created_at else None})
            a.ws_broadcast = True
        except Exception:  # noqa: BLE001
            logger.warning("realtime publish failed for alert %s", a.id, exc_info=True)
    db.commit()
    return len(alerts)
