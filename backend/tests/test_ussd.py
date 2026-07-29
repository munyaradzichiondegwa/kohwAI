"""Tests for USSD handler."""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_main_menu():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/ussd/callback", data={
            "sessionId": "test-session-1",
            "serviceCode": "*123#",
            "phoneNumber": "+263771234567",
            "text": "",
        })
    assert resp.status_code == 200
    assert "CON Welcome to KohwAI" in resp.text


@pytest.mark.asyncio
async def test_zunde_menu():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/ussd/callback", data={
            "sessionId": "test-session-2",
            "serviceCode": "*123#",
            "phoneNumber": "+263771234567",
            "text": "1",
        })
    assert "Zunde" in resp.text


@pytest.mark.asyncio
async def test_crop_triage_result():
    """Symptom: yellow leaves (1) + Maize (1) → disease + disclaimer."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/ussd/callback", data={
            "sessionId": "test-session-3",
            "serviceCode": "*123#",
            "phoneNumber": "+263771234567",
            "text": "1*2*1*1",
        })
    assert "END" in resp.text
    assert "symptom guide" in resp.text.lower()
