"""End-to-end smoke test of the whole loop against the FastAPI app,
simulating what the ElevenLabs Caller/Closer agents would do via their
webhook tools. This is the closest thing to plan §15's go/no-go checklist
that can run without live ElevenLabs/Twilio credentials.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.db import Business, get_session
from app.main import app

client = TestClient(app)

SPEC = {
    "origin": {"city": "Rock Hill", "state": "SC", "stairs_count": 14, "long_carry_ft": 40},
    "destination": {"city": "Charlotte", "state": "NC"},
    "distance_miles": 45,
}


def _log_fee(call_id, quote_id, category, status, amount=None):
    resp = client.post(
        "/webhooks/agent-tools/log_fee_line",
        json={
            "call_id": call_id,
            "quote_id": quote_id,
            "category": category,
            "status": status,
            "amount": amount,
            "idempotency_key": uuid.uuid4().hex,
        },
    )
    assert resp.status_code == 200, resp.text


def _set_total(call_id, quote_id, total, estimate_type="non_binding"):
    resp = client.post(
        "/webhooks/agent-tools/set_quote_total",
        json={
            "call_id": call_id,
            "quote_id": quote_id,
            "quoted_total": total,
            "estimate_type": estimate_type,
            "idempotency_key": uuid.uuid4().hex,
        },
    )
    assert resp.status_code == 200, resp.text


def _log_outcome(call_id, outcome):
    resp = client.post(
        "/webhooks/agent-tools/log_outcome",
        json={"call_id": call_id, "outcome": outcome, "idempotency_key": uuid.uuid4().hex},
    )
    assert resp.status_code == 200, resp.text


def test_full_loop_intake_to_ranked_report_with_live_negotiation():
    session = get_session()
    for business_id, name in [("biz_tough", "Tough"), ("biz_lowball", "Lowball"), ("biz_hardsell", "HardSell")]:
        session.merge(Business(business_id=business_id, name=name, source_type="demo_persona"))
    session.commit()
    session.close()

    # 1. Intake: Estimator submits a draft, user confirms in the dashboard.
    submit = client.post("/webhooks/agent-tools/submit_job_spec", json={"job_id": "job_e2e", "spec": SPEC})
    assert submit.status_code == 200
    confirm = client.post("/jobs/job_e2e/confirm", json={"spec": SPEC})
    assert confirm.status_code == 200
    job_spec_sha256 = confirm.json()["job_spec_sha256"]

    # 2. Round 1: dispatch calls to all three personas -- proves verbatim reuse.
    dispatch = client.post(
        "/calls/dispatch", json={"job_id": "job_e2e", "business_ids": ["biz_tough", "biz_lowball", "biz_hardsell"]}
    )
    assert dispatch.status_code == 200
    call_ids = dict(zip(["biz_tough", "biz_lowball", "biz_hardsell"], dispatch.json()["call_ids"]))

    # Tough: complete, high, binding quote. Itemize enough categories (>=5
    # of 10) to clear the 0.5 completeness floor that gates leverage
    # eligibility (plan §7.3) -- not_applicable still counts as resolved.
    _log_fee(call_ids["biz_tough"], "quote_tough", "base_labor_or_linehaul", "quoted", 1800)
    _log_fee(call_ids["biz_tough"], "quote_tough", "fuel_surcharge", "quoted", 200)
    _log_fee(call_ids["biz_tough"], "quote_tough", "stair_fee", "quoted", 100)
    _log_fee(call_ids["biz_tough"], "quote_tough", "long_carry_fee", "not_applicable")
    _log_fee(call_ids["biz_tough"], "quote_tough", "travel_or_truck_fee", "not_applicable")
    _set_total(call_ids["biz_tough"], "quote_tough", 2200, "binding")
    _log_outcome(call_ids["biz_tough"], "itemized_quote")

    # Lowball: attractive total but hides fees when itemized -- still complete once asked.
    _log_fee(call_ids["biz_lowball"], "quote_lowball", "base_labor_or_linehaul", "quoted", 1500)
    _log_fee(call_ids["biz_lowball"], "quote_lowball", "fuel_surcharge", "quoted", 150)
    _log_fee(call_ids["biz_lowball"], "quote_lowball", "stair_fee", "quoted", 80)
    _set_total(call_ids["biz_lowball"], "quote_lowball", 1900, "non_binding")
    _log_outcome(call_ids["biz_lowball"], "itemized_quote")

    # Hard-sell: stonewalls, only gives a callback commitment -- structured outcome, no quote.
    _log_outcome(call_ids["biz_hardsell"], "callback_committed")

    # 3. Round 2: Closer calls the cheapest complete quote back with real leverage.
    leverage = client.post(
        "/webhooks/agent-tools/get_best_quote_so_far", json={"job_id": "job_e2e", "exclude_business_id": "biz_lowball"}
    )
    assert leverage.json()["available"] is True
    assert leverage.json()["quoted_total"] == 2200  # only Tough is eligible/complete besides Lowball itself

    dispatch2 = client.post("/calls/dispatch", json={"job_id": "job_e2e", "business_ids": ["biz_lowball"], "agent_role": "closer"})
    closer_call_id = dispatch2.json()["call_ids"][0]
    _log_fee(closer_call_id, "quote_lowball", "fuel_surcharge", "included")  # fee waived live
    _set_total(closer_call_id, "quote_lowball", 1750, "non_binding")  # revised down further after pushback
    _log_outcome(closer_call_id, "itemized_quote")

    # 4. Report: verbatim reuse proof, ranking, and the live price change should all show up.
    report = client.get("/jobs/job_e2e/report").json()

    assert report["job_spec_sha256"] == job_spec_sha256
    assert report["verbatim_reuse_proof"]["all_calls_used_same_hash"] is True

    outcomes = {c["business_id"]: c["outcome"] for c in report["calls"]}
    assert outcomes == {
        "biz_tough": "itemized_quote",
        "biz_lowball": "itemized_quote",
        "biz_hardsell": "callback_committed",
    }

    recommended_ids = [e["quote_id"] for e in report["recommended_order"]]
    assert "quote_lowball" in recommended_ids and "quote_tough" in recommended_ids

    lowball_entry = next(e for e in report["recommended_order"] if e["quote_id"] == "quote_lowball")
    assert lowball_entry["quoted_total"] == 1750  # the revised, post-leverage total, not the original 1900

    assert report["narrative"]  # template fallback always produces something, no OPENAI_API_KEY needed
