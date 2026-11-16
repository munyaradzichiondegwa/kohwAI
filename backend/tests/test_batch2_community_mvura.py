"""Batch 2: validator integrity, borehole trust model, UUID handling."""
from sqlalchemy import text

from app.models.community import ValidatorAssignment
from app.models.mvura import Borehole, BoreholeReport
from app.models.zunde import PestSighting
from tests.conftest import make_user, auth


def _assign(db, validator, district, admin):
    db.add(ValidatorAssignment(user_id=validator.id, district=district, assigned_by=admin.id, is_active=True))
    db.commit()


async def _borehole(client, admin, district="Chipinge", name="Mutema BH"):
    r = await client.post("/api/v1/mvura/boreholes", headers=auth(admin),
                          json={"name": name, "village": "Mutema", "district": district, "lat": -20.19, "lng": 32.62})
    assert r.status_code == 200, r.text
    return r.json()


async def test_farmer_report_does_not_change_public_status_until_approved(client, db, clean):
    admin = make_user(db, roles=("admin",)); farmer = make_user(db); val = make_user(db, roles=("validator",))
    _assign(db, val, "Chipinge", admin)
    bh = await _borehole(client, admin)
    assert bh["verified"] is True and bh["status"] == "working"

    r = await client.post(f"/api/v1/mvura/boreholes/{bh['id']}/report", headers=auth(farmer), json={"new_status": "dry"})
    assert r.status_code == 200 and r.json()["status"] == "pending"
    shown = (await client.get("/api/v1/mvura/boreholes?district=Chipinge", headers=auth(farmer))).json()[0]
    assert shown["status"] == "working"                       # public status untouched
    assert shown["pending_report"] == "dry" and shown["pending_reports"] == 1   # shown as UNVERIFIED signal

    q = (await client.get("/api/v1/community/queue", headers=auth(val))).json()
    item = [i for i in q if i["kind"] == "borehole_report"][0]
    assert "***" in item["reporter_phone"] and farmer.phone not in item["reporter_phone"]   # anonymised

    ok = await client.post(f"/api/v1/community/queue/borehole_report/{item['id']}/approve", headers=auth(val))
    assert ok.status_code == 200
    after = (await client.get("/api/v1/mvura/boreholes?district=Chipinge", headers=auth(farmer))).json()[0]
    assert after["status"] == "dry" and after["pending_reports"] == 0


async def test_rejected_report_never_applies_and_is_marked_rejected(client, db, clean):
    admin = make_user(db, roles=("admin",)); farmer = make_user(db)
    bh = await _borehole(client, admin)
    await client.post(f"/api/v1/mvura/boreholes/{bh['id']}/report", headers=auth(farmer), json={"new_status": "dry"})
    rep = db.query(BoreholeReport).one()
    short = await client.post(f"/api/v1/community/queue/borehole_report/{rep.id}/reject", headers=auth(admin), json={"reason": "no"})
    assert short.status_code == 422                                        # reason required, min length
    r = await client.post(f"/api/v1/community/queue/borehole_report/{rep.id}/reject", headers=auth(admin),
                          json={"reason": "Borehole was working when I visited"})
    assert r.status_code == 200
    db.expire_all()
    rep = db.query(BoreholeReport).one()
    assert rep.status == "rejected" and rep.rejection_reason
    assert (await client.get("/api/v1/mvura/boreholes", headers=auth(farmer))).json()[0]["status"] == "working"
    again = await client.post(f"/api/v1/community/queue/borehole_report/{rep.id}/approve", headers=auth(admin))
    assert again.status_code == 409                                        # can't flip a decided report


async def test_cannot_review_own_submission(client, db, clean):
    admin = make_user(db, roles=("admin",)); val = make_user(db, roles=("validator",))
    _assign(db, val, "Chipinge", admin)
    s = PestSighting(user_id=val.id, species="Aphids", severity="low", district="Chipinge", status="pending")
    db.add(s); db.commit()
    r = await client.post(f"/api/v1/community/queue/pest_sighting/{s.id}/approve", headers=auth(val))
    assert r.status_code == 403
    q = (await client.get("/api/v1/community/queue", headers=auth(val))).json()
    assert q == []                                                          # own items are not even queued for them
    assert (await client.post(f"/api/v1/community/queue/pest_sighting/{s.id}/approve", headers=auth(admin))).status_code == 200


async def test_validator_is_limited_to_assigned_districts(client, db, clean):
    admin = make_user(db, roles=("admin",)); val = make_user(db, roles=("validator",)); farmer = make_user(db, "Binga")
    unassigned = make_user(db, roles=("validator",))
    _assign(db, val, "Chipinge", admin)
    s = PestSighting(user_id=farmer.id, species="Aphids", severity="low", district="Binga", status="pending")
    db.add(s); db.commit()
    assert (await client.get("/api/v1/community/queue", headers=auth(val))).json() == []
    assert (await client.get("/api/v1/community/queue?district=Binga", headers=auth(val))).json() == []
    assert (await client.post(f"/api/v1/community/queue/pest_sighting/{s.id}/approve", headers=auth(val))).status_code == 404
    assert (await client.get("/api/v1/community/queue", headers=auth(unassigned))).json() == []   # no assignment = sees nothing
    assert len((await client.get("/api/v1/community/queue", headers=auth(admin))).json()) == 1    # admin: all districts


async def test_admin_can_appoint_and_revoke_validator(client, db, clean):
    admin = make_user(db, roles=("admin",)); farmer = make_user(db, "Gweru")
    r = await client.post("/api/v1/community/validators", headers=auth(admin),
                          json={"phone": farmer.phone, "districts": ["Gweru", "Mutare"]})
    assert r.status_code == 200 and "validator" in r.json()["roles"]
    listing = (await client.get("/api/v1/community/validators", headers=auth(admin))).json()
    mine = [v for v in listing if v["id"] == str(farmer.id)][0]
    assert mine["districts"] == ["Gweru", "Mutare"]
    assert (await client.post("/api/v1/community/validators", headers=auth(farmer),
                              json={"phone": farmer.phone, "districts": ["Gweru"]})).status_code == 403
    assert (await client.post("/api/v1/community/validators", headers=auth(admin),
                              json={"phone": "+263779999999", "districts": ["Gweru"]})).status_code == 404
    assert (await client.delete(f"/api/v1/community/validators/{farmer.id}", headers=auth(admin))).status_code == 200
    db.expire_all()
    assert db.query(ValidatorAssignment).filter_by(user_id=farmer.id, is_active=True).count() == 0


async def test_malformed_ids_are_422_not_500(client, db):
    u = make_user(db)
    for method, url, kw in [
        ("post", "/api/v1/mvura/boreholes/not-a-uuid/report", {"json": {"new_status": "dry"}}),
        ("delete", "/api/v1/musika/listings/xyz", {}),
        ("post", "/api/v1/community/queue/pest_sighting/xyz/approve", {}),
        ("post", "/api/v1/livestock/profiles/zzz/recovered", {}),
        ("post", "/api/v1/musika/insurance/payouts/zzz/mark-sent", {"json": {"ecocash_ref": "ABCD1234"}}),
    ]:
        r = await getattr(client, method)(url, headers=auth(make_user(db, roles=("admin",))), **kw)
        assert r.status_code == 422, (url, r.status_code)


async def test_borehole_input_validation(client, db):
    admin = make_user(db, roles=("admin",))
    bad = [{"district": "Atlantis"}, {"lat": 95.0}, {"lat": -20.0, "lng": 200.0}, {"depth_m": -3}]
    for extra in bad:
        body = {"name": "BH", "village": "V", "district": "Chipinge", **extra}
        assert (await client.post("/api/v1/mvura/boreholes", headers=auth(admin), json=body)).status_code == 422, extra
    assert (await client.get("/api/v1/mvura/boreholes?district=Atlantis", headers=auth(admin))).status_code == 422
