"""Account PIN (USSD + web recovery).

Threat model, honestly:
  * USSD gives us the caller's phone number from the network, but a stolen/borrowed/SIM-swapped phone would
    otherwise be able to file reports, list produce and read insurance details as that farmer. A PIN stops casual misuse.
  * A 4-digit PIN has only 10,000 values, so slow hashing alone cannot protect a leaked hash. We therefore (a) bcrypt a
    keyed HMAC of "phone:pin" — useless to brute-force without SECRET_KEY — and (b) lock after 3 wrong tries (30 min).
  * On USSD the PIN travels inside the session text, which the operator/aggregator may log. Treat it as low-assurance
    protection against misuse, not as banking-grade security. Nothing here moves money.
"""
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.utils.audit import write_audit_log

COMMON = {"1004", "2580", "2000", "1122", "6969", "1212", "1313", "0852", "1998", "2001"}


class PinResult(str, Enum):
    OK = "ok"
    WRONG = "wrong"
    LOCKED = "locked"
    NOT_SET = "not_set"


def validate_pin_format(pin: str) -> str | None:
    """Return a human-readable problem, or None if the PIN is acceptable."""
    if not (len(pin) == 4 and pin.isdigit()):
        return "PIN must be exactly 4 digits."
    d = [int(c) for c in pin]
    if len(set(pin)) == 1 or all(d[i + 1] - d[i] == 1 for i in range(3)) or all(d[i] - d[i + 1] == 1 for i in range(3)) or pin in COMMON:
        return "That PIN is too easy to guess."
    return None


def _digest(phone: str, pin: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"{phone}:{pin}".encode(), hashlib.sha256).hexdigest()


def set_pin(db: Session, user: User, pin: str, actor_note: str = "") -> None:
    problem = validate_pin_format(pin)
    if problem:
        raise ValueError(problem)
    had = bool(user.pin_hash)
    user.pin_hash = hash_password(_digest(user.phone, pin))
    user.pin_failed_attempts = 0
    user.pin_locked_until = None          # a successful (re)set is also how a locked-out farmer recovers
    db.commit()
    write_audit_log(db, str(user.id), "pin.change" if had else "pin.set", "user", str(user.id), after={"via": actor_note})


def hash_for_new_user(phone: str, pin: str) -> str:
    problem = validate_pin_format(pin)
    if problem:
        raise ValueError(problem)
    return hash_password(_digest(phone, pin))


def check_pin(db: Session, user_id, pin: str) -> tuple[PinResult, int]:
    """Verify under a row lock so parallel guesses cannot dodge the attempt counter. -> (result, tries_left)"""
    now = datetime.now(timezone.utc)
    # populate_existing: always read the lock/attempt state fresh from the DB under the row lock, never from a stale in-memory copy
    u = db.query(User).filter(User.id == user_id).populate_existing().with_for_update().one()
    if not u.pin_hash:
        db.rollback()
        return PinResult.NOT_SET, 0
    if u.pin_locked_until and u.pin_locked_until > now:
        db.rollback()
        return PinResult.LOCKED, 0
    if verify_password(_digest(u.phone, pin), u.pin_hash):
        u.pin_failed_attempts = 0
        u.pin_locked_until = None
        db.commit()
        return PinResult.OK, settings.PIN_MAX_ATTEMPTS
    u.pin_failed_attempts = (u.pin_failed_attempts or 0) + 1
    if u.pin_failed_attempts >= settings.PIN_MAX_ATTEMPTS:
        u.pin_locked_until = now + timedelta(minutes=settings.PIN_LOCK_MINUTES)
        u.pin_failed_attempts = 0
        db.commit()
        write_audit_log(db, str(u.id), "pin.locked", "user", str(u.id), after={"minutes": settings.PIN_LOCK_MINUTES})
        return PinResult.LOCKED, 0
    left = settings.PIN_MAX_ATTEMPTS - u.pin_failed_attempts
    db.commit()
    write_audit_log(db, str(u.id), "pin.failed", "user", str(u.id), after={"tries_left": left})
    return PinResult.WRONG, left
