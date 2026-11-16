"""Business logic for Identity & Access — phone + OTP authentication.

No password is ever stored for farmer accounts: the phone number plus a
short-lived OTP (delivered by SMS in production, returned directly in the
API response in local development when no SMS gateway is configured) is
the credential, matching how USSD/feature-phone users already authenticate.
"""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, verify_password,
)
from app.core.redis_client import redis_client
from app.models.user import User, OTPLog
from app.utils.sms import send_sms
from app.utils.audit import write_audit_log
from app.modules.identity.schemas import UserOut

OTP_TTL_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
OTP_RATE_LIMIT_WINDOW_SECONDS = 15 * 60
OTP_RATE_LIMIT_MAX_SENDS = 3


def _rate_limit_key(phone: str) -> str:
    return f"otp_rate:{phone}"


def request_otp(db: Session, phone: str, ip: str = "") -> dict:
    """Generate, store (hashed), and dispatch an OTP. Returns metadata only —
    never the plaintext OTP, except in local development with no SMS gateway
    configured, where it is echoed back so the flow is testable end-to-end."""
    try:
        sent_so_far = redis_client.incr(_rate_limit_key(phone))
        if sent_so_far == 1:
            redis_client.expire(_rate_limit_key(phone), OTP_RATE_LIMIT_WINDOW_SECONDS)
        if sent_so_far > OTP_RATE_LIMIT_MAX_SENDS:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                 "Too many OTP requests. Please wait 15 minutes and try again.")
    except HTTPException:
        raise
    except Exception:
        pass  # Redis unavailable — degrade gracefully rather than blocking auth entirely.

    otp = f"{secrets.randbelow(1_000_000):06d}"
    otp_log = OTPLog(
        phone=phone,
        otp_hash=hash_password(otp),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES),
        used=False,
        attempts=0,
        ip_address=ip or None,
    )
    db.add(otp_log)
    db.commit()

    dev_otp = None
    if settings.AT_API_KEY:
        send_sms([phone], f"Your KohwAI verification code is {otp}. Valid for {OTP_TTL_MINUTES} minutes.")
    elif settings.ENVIRONMENT == "development" and settings.EXPOSE_DEV_OTP:
        # Explicit opt-in, development only. Any other environment fails closed:
        # without an SMS gateway the code is simply not delivered.
        dev_otp = otp

    return {"phone": phone, "expires_in_seconds": OTP_TTL_MINUTES * 60, "dev_otp": dev_otp}


def verify_otp(db: Session, phone: str, otp: str, language: str, district: str | None, ip: str = "",
               accept_terms: bool = False) -> tuple[User, str, str]:
    otp_log = (
        db.query(OTPLog)
        .filter(OTPLog.phone == phone, OTPLog.used.is_(False))
        .order_by(OTPLog.created_at.desc())
        .first()
    )
    if not otp_log:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No pending verification code for this number. Request a new one.")
    if otp_log.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Code expired. Request a new one.")
    if otp_log.attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many incorrect attempts. Request a new code.")
    if not verify_password(otp, otp_log.otp_hash):
        otp_log.attempts += 1
        db.commit()
        write_audit_log(db, None, "auth.otp_failed", "user", phone, after={"attempts": otp_log.attempts}, ip=ip)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Incorrect code.")

    user = db.query(User).filter(User.phone == phone).first()
    if not user and not accept_terms:
        # Checked BEFORE the code is consumed, so ticking the box and retrying works with the same code.
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "To create an account you must accept the Terms and Privacy Policy.")

    otp_log.used = True
    db.commit()

    registered = False
    if not user:
        user = User(phone=phone, language=language or "en", district=district, roles=["farmer"],
                    terms_accepted_at=datetime.now(timezone.utc), terms_version=settings.TERMS_VERSION)
        db.add(user)
        db.commit()
        db.refresh(user)
        registered = True
    else:
        changed = False
        if district and user.district != district:
            user.district = district
            changed = True
        if language and user.language != language:
            user.language = language
            changed = True
        if changed:
            db.commit()

    write_audit_log(db, str(user.id), "auth.register" if registered else "auth.login", "user", str(user.id), ip=ip)
    if registered:
        write_audit_log(db, str(user.id), "consent.accepted", "user", str(user.id), after={"terms_version": settings.TERMS_VERSION}, ip=ip)
    access = create_access_token(str(user.id), extra={"roles": user.roles})
    refresh = create_refresh_token(str(user.id))
    return user, access, refresh


def refresh_access_token(db: Session, refresh_token: str) -> str:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token.")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not found or disabled.")
    return create_access_token(str(user.id), extra={"roles": user.roles})


# ── profile helpers ──────────────────────────────────────────────────────
def user_out(user: User) -> UserOut:
    return UserOut(id=str(user.id), phone=user.phone, language=user.language, district=user.district,
                   roles=user.roles, created_at=user.created_at,
                   needs_consent=(user.terms_accepted_at is None or user.terms_version != settings.TERMS_VERSION),
                   sms_alerts=bool(user.sms_alerts), has_pin=bool(user.pin_hash))


def accept_terms(db: Session, user: User, ip: str = "") -> None:
    user.terms_accepted_at = datetime.now(timezone.utc)
    user.terms_version = settings.TERMS_VERSION
    db.commit()
    write_audit_log(db, str(user.id), "consent.accepted", "user", str(user.id),
                    after={"terms_version": settings.TERMS_VERSION}, ip=ip)
