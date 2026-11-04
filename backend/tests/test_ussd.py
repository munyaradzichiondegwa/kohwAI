"""Tests for USSD handler."""



async def test_main_menu(client):
    if True:
        resp = await client.post("/api/v1/ussd/callback", data={
            "sessionId": "test-session-1",
            "serviceCode": "*123#",
            "phoneNumber": "+263771234567",
            "text": "",
        })
    assert resp.status_code == 200
    assert "CON Welcome to KohwAI" in resp.text


async def test_zunde_menu(client):
    if True:
        resp = await client.post("/api/v1/ussd/callback", data={
            "sessionId": "test-session-2",
            "serviceCode": "*123#",
            "phoneNumber": "+263771234567",
            "text": "1",
        })
    assert "Zunde" in resp.text


async def test_crop_triage_result(client):
    """Symptom: yellow leaves (1) + Maize (1) → disease + disclaimer."""
    if True:
        resp = await client.post("/api/v1/ussd/callback", data={
            "sessionId": "test-session-3",
            "serviceCode": "*123#",
            "phoneNumber": "+263771234567",
            "text": "1*2*1*1",
        })
    assert "END" in resp.text
    assert "symptom guide" in resp.text.lower()
