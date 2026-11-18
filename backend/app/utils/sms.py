"""Compatibility facade for KohwAI's multi-provider SMS router.

Existing modules can continue importing send_sms/send_sms_detailed. A result
with ok=True means provider acceptance/queueing; confirmed handset delivery is
reported asynchronously by the provider's delivery-receipt mechanism.
"""
from app.utils.sms_providers.base import SmsResult
from app.utils.sms_providers.router import gateway_configured, send_sms, send_sms_detailed

__all__ = ["SmsResult", "gateway_configured", "send_sms", "send_sms_detailed"]
