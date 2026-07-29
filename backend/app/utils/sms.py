"""Africa's Talking SMS and USSD gateway utilities."""
import requests
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def send_sms(recipients: list[str], message: str) -> bool:
    """Send SMS via Africa's Talking API. Returns True if accepted."""
    try:
        resp = requests.post(
            "https://api.africastalking.com/version1/messaging",
            headers={
                "apiKey": settings.AT_API_KEY,
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "username": settings.AT_USERNAME,
                "to": ",".join(recipients),
                "message": message,
                "from": settings.AT_SHORTCODE,
            },
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"SMS sent to {len(recipients)} recipients: {result}")
        return True
    except Exception as e:
        logger.error(f"SMS send failed: {e}")
        return False
