from __future__ import annotations

import logging
import os
from typing import Iterable

import requests

from .base import SmsResult, canonical_phone, normalize_phone

logger = logging.getLogger(__name__)


def configured() -> bool:
    return bool(
        os.getenv("INFOBIP_BASE_URL", "").strip()
        and os.getenv("INFOBIP_API_KEY", "").strip()
        and os.getenv("INFOBIP_SENDER", "").strip()
    )


def _failed(recipients: Iterable[str], status: str, *, uncertain: bool = False) -> dict[str, SmsResult]:
    return {
        phone: SmsResult(False, status, provider="infobip", uncertain=uncertain)
        for phone in recipients
    }


def send(recipients: list[str], message: str) -> dict[str, SmsResult]:
    if not configured():
        return _failed(recipients, "not_configured")

    base_url = os.getenv("INFOBIP_BASE_URL", "").strip().rstrip("/")
    if not base_url.startswith("https://"):
        return _failed(recipients, "invalid_base_url")

    payload = {
        "messages": [
            {
                "sender": os.getenv("INFOBIP_SENDER", "").strip(),
                "destinations": [{"to": normalize_phone(phone)} for phone in recipients],
                "content": {"text": message},
            }
        ]
    }
    try:
        response = requests.post(
            f"{base_url}/sms/3/messages",
            headers={
                "Authorization": f"App {os.getenv('INFOBIP_API_KEY', '').strip()}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=(5, 20),
        )
    except requests.RequestException as exc:
        logger.warning("Infobip transport outcome is uncertain: %s", type(exc).__name__)
        return _failed(recipients, "transport_outcome_uncertain", uncertain=True)

    if response.status_code >= 500:
        logger.warning("Infobip returned HTTP %s; delivery outcome is uncertain", response.status_code)
        return _failed(recipients, f"http_{response.status_code}_uncertain", uncertain=True)
    if response.status_code >= 400:
        logger.warning("Infobip rejected request with HTTP %s", response.status_code)
        return _failed(recipients, f"http_{response.status_code}_rejected")

    try:
        body = response.json()
        messages = body.get("messages", [])
    except (ValueError, AttributeError, TypeError):
        logger.warning("Infobip returned an unreadable success response; suppressing fallback")
        return _failed(recipients, "unreadable_provider_response", uncertain=True)

    by_phone: dict[str, SmsResult] = {}
    for item in messages:
        if not isinstance(item, dict):
            continue
        destination = canonical_phone(str(item.get("to", "")))
        message_id = str(item.get("messageId", "")) or None
        status_obj = item.get("status") if isinstance(item.get("status"), dict) else {}
        group_name = str(status_obj.get("groupName", "")).upper()
        status_name = str(status_obj.get("name", "")).upper()
        description = str(status_obj.get("description", ""))[:120]

        # Infobip messageId means accepted for processing. It is not a handset
        # delivery receipt. An explicit REJECTED status is safe to fail over.
        if message_id and group_name != "REJECTED" and not status_name.startswith("REJECTED"):
            result = SmsResult(True, f"accepted:{group_name or 'processing'}", provider="infobip", message_id=message_id)
        elif group_name == "REJECTED" or status_name.startswith("REJECTED"):
            result = SmsResult(False, f"rejected:{description or status_name}", provider="infobip")
        else:
            result = SmsResult(False, "unknown_message_status", provider="infobip", message_id=message_id, uncertain=True)
        if destination:
            by_phone[destination] = result

    output: dict[str, SmsResult] = {}
    for original in recipients:
        result = by_phone.get(canonical_phone(original))
        output[original] = result or SmsResult(
            False, "recipient_missing_from_provider_response", provider="infobip", uncertain=True
        )
    return output
