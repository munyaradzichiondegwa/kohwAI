from __future__ import annotations

import logging
import os
from typing import Callable

from .base import SmsResult
from . import africas_talking, econet_a2p, infobip, smspop

logger = logging.getLogger(__name__)

PROVIDERS: dict[str, tuple[Callable[[], bool], Callable[[list[str], str], dict[str, SmsResult]]]] = {
    "smspop": (smspop.configured, smspop.send),
    "infobip": (infobip.configured, infobip.send),
    "econet_a2p": (econet_a2p.configured, econet_a2p.send),
    # Optional legacy route; it is deliberately excluded from the default
    # order because the previous account credentials returned HTTP 401.
    "africastalking": (africas_talking.configured, africas_talking.send),
}
DEFAULT_PROVIDER_ORDER = ("smspop", "infobip", "econet_a2p")


def provider_order() -> list[str]:
    raw = os.getenv("SMS_PROVIDER_ORDER", ",".join(DEFAULT_PROVIDER_ORDER))
    result = [item.strip().lower() for item in raw.split(",") if item.strip()]
    # Ignore unknown entries rather than dynamically importing arbitrary code.
    return [item for item in result if item in PROVIDERS]


def gateway_configured() -> bool:
    return any(PROVIDERS[name][0]() for name in provider_order())


def _eligible(name: str, recipients: list[str]) -> list[str]:
    if name == "econet_a2p":
        return [phone for phone in recipients if econet_a2p.eligible(phone)]
    return list(recipients)


def send_sms_detailed(recipients: list[str], message: str) -> dict[str, SmsResult]:
    """Deliver per recipient with safe failover.

    Failover occurs only after a provider's definitive rejection. Timeouts,
    HTTP 5xx responses, and malformed success bodies are treated as uncertain
    and stop further delivery attempts for that recipient to prevent duplicate
    OTP messages.
    """
    if not recipients:
        return {}

    final: dict[str, SmsResult] = {}
    pending = list(dict.fromkeys(recipients))
    last_failure: dict[str, SmsResult] = {}

    for name in provider_order():
        if not pending:
            break
        is_configured, send = PROVIDERS[name]
        if not is_configured():
            continue
        eligible = _eligible(name, pending)
        if not eligible:
            continue
        try:
            provider_results = send(eligible, message)
        except Exception:  # noqa: BLE001
            logger.exception("Unexpected error in SMS provider adapter: %s", name)
            provider_results = {
                phone: SmsResult(False, "adapter_error_uncertain", provider=name, uncertain=True)
                for phone in eligible
            }

        for phone in eligible:
            result = provider_results.get(phone)
            if result is None:
                result = SmsResult(False, "missing_provider_result_uncertain", provider=name, uncertain=True)
            if result.ok or result.uncertain:
                final[phone] = result
                if phone in pending:
                    pending.remove(phone)
            else:
                last_failure[phone] = result

    for phone in pending:
        final[phone] = last_failure.get(
            phone,
            SmsResult(False, "no_configured_provider_accepted_message", provider="", permanent=False),
        )

    # Preserve results for duplicate input numbers without sending duplicates.
    return {phone: final[phone] for phone in recipients}


def send_sms(recipients: list[str], message: str) -> bool:
    """Backward-compatible helper: True means provider acceptance, not DLR."""
    if not recipients:
        return True
    results = send_sms_detailed(recipients, message)
    return all(results.get(phone, SmsResult(False, "missing_result")).ok for phone in recipients)
