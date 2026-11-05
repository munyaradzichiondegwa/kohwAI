from fastapi import APIRouter, Form, HTTPException, Request
from app.core.config import settings
from app.modules.ussd.handler import USSDHandler

router = APIRouter()
handler = USSDHandler()


def _caller_allowed(request: Request) -> bool:
    """Africa's Talking does not sign callbacks, so we restrict by source IP.
    Outside development an empty allowlist rejects everything (fail closed): without it anyone
    could POST as any phone number and file reports or listings in that person's name."""
    allowed = {ip.strip() for ip in settings.USSD_ALLOWED_IPS.split(",") if ip.strip()}
    if not allowed:
        return settings.ENVIRONMENT == "development"
    return bool(request.client and request.client.host in allowed)


@router.post("/callback", summary="Africa's Talking USSD callback")
async def ussd_callback(
    request: Request,
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(""),
):
    """Plain-text response prefixed with CON (continue) or END. Source IP must be allow-listed
    (USSD_ALLOWED_IPS) outside development. Run uvicorn with --proxy-headers behind a proxy."""
    if not _caller_allowed(request):
        raise HTTPException(403, "Forbidden")
    return await handler.handle(session_id=sessionId, phone=phoneNumber, text=text, service_code=serviceCode)
