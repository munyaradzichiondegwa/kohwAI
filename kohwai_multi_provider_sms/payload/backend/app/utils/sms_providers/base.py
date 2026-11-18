from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SmsResult:
    """Result for one recipient.

    `ok=True` means the provider accepted/queued the message, not that the
    handset has received it. Delivery receipts are a separate later event.
    `uncertain=True` means the provider may have accepted the message; callers
    must not automatically send the same OTP through another provider.
    """

    ok: bool
    status: str
    permanent: bool = False
    provider: str = ""
    message_id: Optional[str] = None
    uncertain: bool = False


def normalize_phone(phone: str) -> str:
    """Normalize Zimbabwe numbers to E.164; preserve other international E.164."""
    raw = (phone or "").strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return raw

    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("263") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 10:
        return f"+263{digits[1:]}"
    if digits.startswith("7") and len(digits) == 9:
        return f"+263{digits}"
    if raw.startswith("+"):
        return f"+{digits}"
    return raw


def canonical_phone(phone: str) -> str:
    return re.sub(r"\D", "", normalize_phone(phone))


def is_econet_number(phone: str) -> bool:
    """Return True for originally assigned Econet 077/078/079 ranges.

    Zimbabwe's published number allocations identify 077/078/079 as Econet
    ranges. This is a routing hint; only use the direct Econet adapter after
    Econet confirms the destination-routing rules for the A2P product.
    """
    digits = canonical_phone(phone)
    if digits.startswith("263"):
        national = digits[3:]
    elif digits.startswith("0"):
        national = digits[1:]
    else:
        national = digits
    return len(national) == 9 and national.startswith(("77", "78", "79"))
