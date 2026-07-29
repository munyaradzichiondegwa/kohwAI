"""Tests for identity/auth module."""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_otp_request():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/otp/request", json={"phone": "+263771234567"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_invalid_otp():
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post("/api/v1/auth/otp/request", json={"phone": "+263771111111"})
        resp = await client.post("/api/v1/auth/otp/verify", json={"phone": "+263771111111", "otp": "000000"})
    assert resp.status_code == 400
