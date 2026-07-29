from fastapi import APIRouter, Form
from app.modules.ussd.handler import USSDHandler

router = APIRouter()
handler = USSDHandler()

@router.post("/callback", summary="Africa's Talking USSD callback")
async def ussd_callback(
    sessionId: str  = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str        = Form(""),
):
    """
    Africa's Talking calls this endpoint on every USSD interaction.
    Returns a plain-text response prefixed with CON (continue) or END.
    """
    response = await handler.handle(
        session_id=sessionId,
        phone=phoneNumber,
        text=text,
        service_code=serviceCode,
    )
    return response
