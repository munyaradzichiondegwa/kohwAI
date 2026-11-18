from __future__ import annotations

import logging
import os
from typing import Iterable

import requests

from .base import SmsResult, canonical_phone, normalize_phone

logger = logging.getLogger(__name__)
API_URL = "https://smspop.co.zw/api/campaigns"


def configured() -> bool:
    return bool(os.getenv("SMSPOP_API_TOKEN", "").strip() and os.getenv("SMSPOP_SENDER_ID", "").strip())


def _failed(recipients: Iterable[str], status: str, *, uncertain: bool = False) -> dict[str, SmsResult]:
    return {
        phone: SmsResult(False, status, provider="smspop", uncertain=uncertain)
        for phone in recipients
    }


def send(recipients: list[str], message: str) -> dict[str, SmsResult]:
    if not configured():
        return _failed(recipients, "not_configured")

    token = os.getenv("SMSPOP_API_TOKEN", "").strip()
    sender_id = os.getenv("SMSPOP_SENDER_ID", "").strip()
    campaign_name = os.getenv("SMSPOP_CAMPAIGN_NAME", "KohwAI transactional message").strip()
    payload = {
        "name": campaign_name[:255],
        "message": message,
        "sender_id": sender_id,
        "contact_import_method": "manual",
        "manual_contacts": ",".join(normalize_phone(p) for p in recipients),
    }
    callback_url = os.getenv("SMSPOP_CALLBACK_URL", "").strip()
    if callback_url:
        payload["callback_url"] = callback_url

    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=(5, 20),
        )
    except requests.RequestException as exc:
        # A timeout/transport error may occur after the provider accepted a
        # campaign. Do not fail over automatically: that can duplicate OTPs.
        logger.warning("SMSPoP transport outcome is uncertain: %s", type(exc).__name__)
        return _failed(recipients, "transport_outcome_uncertain", uncertain=True)

    if response.status_code >= 500:
        logger.warning("SMSPoP returned HTTP %s; delivery outcome is uncertain", response.status_code)
        return _failed(recipients, f"http_{response.status_code}_uncertain", uncertain=True)
    if response.status_code >= 400:
        logger.warning("SMSPoP rejected request with HTTP %s", response.status_code)
        return _failed(recipients, f"http_{response.status_code}_rejected")

    try:
        body = response.json()
        contacts = body.get("data", {}).get("contacts", [])
    except (ValueError, AttributeError, TypeError):
        logger.warning("SMSPoP returned an unreadable success response; suppressing fallback")
        return _failed(recipients, "unreadable_provider_response", uncertain=True)

    by_phone: dict[str, SmsResult] = {}
    for item in contacts:
        if not isinstance(item, dict):
            continue
        key = canonical_phone(str(item.get("phone", "")))
        status = str(item.get("status", "")).strip().lower()
        message_id = str(item.get("message_id", "")) or None
        if status == "sent":
            result = SmsResult(True, "accepted_by_network", provider="smspop", message_id=message_id)
        elif status in {"failed", "skipped"}:
            reason = str(item.get("reason", status)).strip()[:120]
            result = SmsResult(False, f"{status}:{reason}", provider="smspop")
        else:
            result = SmsResult(False, "unknown_contact_status", provider="smspop", message_id=message_id, uncertain=True)
        if key:
            by_phone[key] = result

    output: dict[str, SmsResult] = {}
    for original in recipients:
        result = by_phone.get(canonical_phone(original))
        # No recipient-specific result after HTTP 2xx is ambiguous. Don't risk
        # a duplicate by routing this same OTP through another provider.
        output[original] = result or SmsResult(
            False, "recipient_missing_from_provider_response", provider="smspop", uncertain=True
        )
    return output
