"""Tests for identity/auth module."""



async def test_otp_request(client):
    if True:
        resp = await client.post("/api/v1/auth/otp/request", json={"phone": "+263771234567"})
    assert resp.status_code == 200


async def test_invalid_otp(client):
    if True:
        await client.post("/api/v1/auth/otp/request", json={"phone": "+263771111111"})
        resp = await client.post("/api/v1/auth/otp/verify", json={"phone": "+263771111111", "otp": "000000"})
    assert resp.status_code == 400
