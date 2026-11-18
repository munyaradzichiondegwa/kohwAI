"""Econet Wireless direct A2P adapter slot.

Econet publicly confirms A2P OTP/transactional SMS and provides an API
Marketplace registration portal, but its public material does not publish the
A2P send endpoint, auth contract, request schema, or response schema.

This adapter deliberately refuses to send until the authenticated Econet API
specification has been supplied and implemented. Do not invent an endpoint or
reuse Africa's Talking credentials here.
"""
from __future__ import annotations

from .base import SmsResult, is_econet_number


def configured() -> bool:
    # Keep this false until Econet provides the live API contract and the
    # adapter is implemented against that contract.
    return False


def eligible(phone: str) -> bool:
    return is_econet_number(phone)


def send(recipients: list[str], message: str) -> dict[str, SmsResult]:
    return {
        phone: SmsResult(
            False,
            "econet_a2p_pending_official_api_specification",
            provider="econet_a2p",
        )
        for phone in recipients
    }
