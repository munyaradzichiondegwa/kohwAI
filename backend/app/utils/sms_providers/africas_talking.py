"""Optional legacy Africa's Talking adapter (not in the default route order)."""
from __future__ import annotations

import logging
from typing import Iterable

import requests

from .base import SmsResult, canonical_phone, normalize_phone

logger = logging.getLogger(__name__)
API_URL = "https://api.africastalking.com/version1/messaging"
SUCCESS_CODES = {100, 101, 102}


def _settings():
    from app.core.config import settings
    return settings


def configured() -> bool:
    settings = _settings()
    return bool(settings.AT_API_KEY.strip() and settings.AT_USERNAME.strip())


def _failed(recipients: Iterable[str], status: str, *, uncertain: bool = False) -> dict[str, SmsResult]:
    return {p: SmsResult(False, status, provider="africas_talking", uncertain=uncertain) for p in recipients}


def send(recipients: list[str], message: str) -> dict[str, SmsResult]:
    if not configured():
        return _failed(recipients, "not_configured")
    settings = _settings()
    data = {
        "username": settings.AT_USERNAME.strip(),
        "to": ",".join(normalize_phone(p) for p in recipients),
        "message": message,
    }
    shortcode = (settings.AT_SHORTCODE or "").strip()
    if shortcode and shortcode != "123":
        data["from"] = shortcode
    try:
        response = requests.post(
            API_URL,
            headers={
                "apiKey": settings.AT_API_KEY.strip(),
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=data,
            timeout=(5, 20),
        )
    except requests.RequestException as exc:
        logger.warning("Africa's Talking transport outcome is uncertain: %s", type(exc).__name__)
        return _failed(recipients, "transport_outcome_uncertain", uncertain=True)
    if response.status_code >= 500:
        return _failed(recipients, f"http_{response.status_code}_uncertain", uncertain=True)
    if response.status_code >= 400:
        return _failed(recipients, f"http_{response.status_code}_rejected")
    try:
        entries = response.json().get("SMSMessageData", {}).get("Recipients", [])
    except (ValueError, AttributeError, TypeError):
        return _failed(recipients, "unreadable_provider_response", uncertain=True)
    by_phone: dict[str, SmsResult] = {}
    for entry in entries:
        key = canonical_phone(str(entry.get("number", "")))
        code = int(entry.get("statusCode", 0) or 0)
        by_phone[key] = SmsResult(
            code in SUCCESS_CODES,
            str(entry.get("status", code)),
            provider="africas_talking",
            message_id=str(entry.get("messageId", "")) or None,
        )
    return {
        phone: by_phone.get(canonical_phone(phone), SmsResult(False, "recipient_missing_from_provider_response", provider="africas_talking", uncertain=True))
        for phone in recipients
    }
