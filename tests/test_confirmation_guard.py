from fastapi.testclient import TestClient

from app.db import Business, get_session
from app.main import app

client = TestClient(app)


def test_dispatch_rejected_before_confirmation():
    create = client.post("/jobs", json={"vertical_id": "residential_moving", "spec": {"a": 1}})
    job_id = create.json()["job_id"]

    resp = client.post("/calls/dispatch", json={"job_id": job_id, "business_ids": ["persona_tough"]})
    assert resp.status_code == 409


def test_dispatch_allowed_after_confirmation():
    session = get_session()
    session.merge(Business(business_id="persona_tough", name="Tough Negotiator", source_type="demo_persona"))
    session.commit()
    session.close()

    create = client.post("/jobs", json={"vertical_id": "residential_moving", "spec": {"a": 1}})
    job_id = create.json()["job_id"]

    client.post(f"/jobs/{job_id}/confirm", json={"spec": {"a": 1}})

    resp = client.post("/calls/dispatch", json={"job_id": job_id, "business_ids": ["persona_tough"]})
    assert resp.status_code == 200
    assert resp.json()["job_spec_sha256"]


def test_every_dispatched_call_carries_the_confirmed_hash():
    session = get_session()
    session.merge(Business(business_id="persona_lowball", name="Lowball", source_type="demo_persona"))
    session.commit()
    session.close()

    create = client.post("/jobs", json={"vertical_id": "residential_moving", "spec": {"a": 2}})
    job_id = create.json()["job_id"]
    confirm = client.post(f"/jobs/{job_id}/confirm", json={"spec": {"a": 2}})
    confirmed_hash = confirm.json()["job_spec_sha256"]

    dispatch = client.post("/calls/dispatch", json={"job_id": job_id, "business_ids": ["persona_lowball"]})
    assert dispatch.json()["job_spec_sha256"] == confirmed_hash
