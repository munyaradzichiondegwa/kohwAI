import os
import unittest
from unittest.mock import patch

import requests

from app.utils.sms_providers.router import send_sms_detailed
from app.utils.sms_providers.base import is_econet_number, normalize_phone


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class SmsProviderRouterTests(unittest.TestCase):
    def test_phone_normalization_and_econet_prefix_hint(self):
        self.assertEqual(normalize_phone("0774387106"), "+263774387106")
        self.assertEqual(normalize_phone("+263774387106"), "+263774387106")
        self.assertTrue(is_econet_number("+263774387106"))
        self.assertFalse(is_econet_number("+263714387106"))

    @patch.dict(os.environ, {
        "SMS_PROVIDER_ORDER": "smspop,infobip,econet_a2p",
        "SMSPOP_API_TOKEN": "test-token",
        "SMSPOP_SENDER_ID": "KOHWAI",
        "INFOBIP_BASE_URL": "https://example.api.infobip.com",
        "INFOBIP_API_KEY": "test-infobip-key",
        "INFOBIP_SENDER": "KOHWAI",
        "ECONET_A2P_ENABLED": "false",
    }, clear=True)
    @patch("requests.post")
    def test_definitive_smspop_rejection_falls_back_to_infobip(self, post):
        post.side_effect = [
            FakeResponse(200, {
                "success": True,
                "data": {"contacts": [{"phone": "263774387106", "status": "skipped", "reason": "sender not approved"}]},
            }),
            FakeResponse(200, {
                "messages": [{
                    "to": "263774387106",
                    "messageId": "infobip-message-1",
                    "status": {"groupName": "PENDING", "name": "PENDING_ENROUTE", "description": "Accepted"},
                }]
            }),
        ]

        result = send_sms_detailed(["+263774387106"], "KohwAI test OTP 123456")["+263774387106"]

        self.assertTrue(result.ok)
        self.assertEqual(result.provider, "infobip")
        self.assertEqual(result.message_id, "infobip-message-1")
        self.assertEqual(post.call_count, 2)

    @patch.dict(os.environ, {
        "SMS_PROVIDER_ORDER": "smspop,infobip,econet_a2p",
        "SMSPOP_API_TOKEN": "test-token",
        "SMSPOP_SENDER_ID": "KOHWAI",
        "INFOBIP_BASE_URL": "https://example.api.infobip.com",
        "INFOBIP_API_KEY": "test-infobip-key",
        "INFOBIP_SENDER": "KOHWAI",
    }, clear=True)
    @patch("requests.post", side_effect=requests.Timeout("simulated timeout"))
    def test_timeout_stops_fallback_to_prevent_duplicate_otp(self, post):
        result = send_sms_detailed(["+263774387106"], "KohwAI test OTP 123456")["+263774387106"]
        self.assertFalse(result.ok)
        self.assertTrue(result.uncertain)
        self.assertEqual(result.provider, "smspop")
        post.assert_called_once()

    @patch.dict(os.environ, {"SMS_PROVIDER_ORDER": "econet_a2p", "ECONET_A2P_ENABLED": "true"}, clear=True)
    def test_econet_direct_route_remains_disabled_until_official_api_contract(self):
        result = send_sms_detailed(["+263774387106"], "KohwAI test OTP 123456")["+263774387106"]
        self.assertFalse(result.ok)
        self.assertIn("no_configured_provider", result.status)


if __name__ == "__main__":
    unittest.main()
