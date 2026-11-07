"""Africa's Talking SMS gateway.

`send_sms_detailed` returns a result PER RECIPIENT, because the gateway can accept some numbers and reject
others in one call — treating the whole batch as "sent" (the old behaviour) hides failures and would make
the delivery record a lie."""
import logging
from dataclasses import dataclass

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

AT_URL = "https://api.africastalking.com/version1/messaging"
AT_SUCCESS_CODES = {100, 101, 102}              # Processed / Sent / Queued
AT_PERMANENT_CODES = {403, 406, 407, 409}       # invalid number, blacklisted, unroutable, do-not-disturb: retrying is pointless


@dataclass
class SmsResult:
    ok: bool
    status: str                 # provider text or "gateway_error"
    permanent: bool = False     # True = never retry this recipient


def gateway_configured() -> bool:
    return bool(settings.AT_API_KEY)


def send_sms_detailed(recipients: list[str], message: str) -> dict[str, SmsResult]:
    """Send one message to many numbers. Returns {phone: SmsResult}. Raises nothing: a transport failure is
    reported as a retryable failure for every recipient."""
    if not gateway_configured():
        return {r: SmsResult(False, "no_gateway_configured") for r in recipients}
    try:
        resp = requests.post(
            AT_URL,
            headers={"apiKey": settings.AT_API_KEY, "Accept": "application/json",
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"username": settings.AT_USERNAME, "to": ",".join(recipients), "message": message,
                  "from": settings.AT_SHORTCODE},
            timeout=20,
        )
        resp.raise_for_status()
        entries = resp.json().get("SMSMessageData", {}).get("Recipients", [])
    except Exception as e:  # noqa: BLE001
        logger.error("SMS gateway call failed: %s", e)
        return {r: SmsResult(False, "gateway_error") for r in recipients}

    out: dict[str, SmsResult] = {}
    for e in entries:
        code = int(e.get("statusCode", 0) or 0)
        out[e.get("number", "")] = SmsResult(code in AT_SUCCESS_CODES, str(e.get("status", code)), code in AT_PERMANENT_CODES)
    for r in recipients:                       # anyone the gateway did not mention is NOT assumed delivered
        out.setdefault(r, SmsResult(False, "not_in_gateway_response"))
    return out


def send_sms(recipients: list[str], message: str) -> bool:
    """Convenience for single transactional messages (OTP, payout notice). True only if EVERY recipient was accepted.
    Without credentials (local dev/tests) nothing is sent and False is returned."""
    if not gateway_configured():
        logger.info("SMS skipped (no AT_API_KEY configured): to=%s", recipients)
        return False
    results = send_sms_detailed(recipients, message)
    return all(results[r].ok for r in recipients)      # only the numbers WE asked about
