from __future__ import annotations

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from app.api.jobs import assert_confirmed  # noqa: E402
from app.db import Call, Job, get_session  # noqa: E402
from app.services.calling import place_outbound_call, set_agent_dynamic_variables  # noqa: E402
from app.services.job_spec import flatten_job_spec_to_dynamic_variables  # noqa: E402

from scripts.seed_demo_job import DEMO_JOB_ID  # noqa: E402

WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000").rstrip("/")

# Fill in with real, consenting teammates' phone numbers before a real
# rehearsal (plan §4.3, §8) -- never dial a number without consent, and
# never commit real personal numbers to this file; use env vars.
PERSONA_PHONE_NUMBERS = {
    "persona_tough": os.getenv("PERSONA_TOUGH_PHONE", ""),
    "persona_lowball": os.getenv("PERSONA_LOWBALL_PHONE", ""),
    "persona_hardsell": os.getenv("PERSONA_HARDSELL_PHONE", ""),
}


def _dispatch_one(job: Job, agent_id: str, agent_role: str, business_id: str, phone_number: str) -> str:
    session = get_session()
    try:
        dynamic_variables = flatten_job_spec_to_dynamic_variables(job.job_id, job.job_spec_sha256, job.spec)
        call = Call(
            call_id=f"call_{uuid.uuid4().hex[:8]}",
            job_id=job.job_id,
            business_id=business_id,
            agent_role=agent_role,
            job_spec_sha256_used=job.job_spec_sha256,
        )
        session.add(call)
        session.commit()

        call_vars = {**dynamic_variables, "customer_name": "Daniel", "business_name": business_id}
        conversation_id = place_outbound_call(agent_id, phone_number, call_vars)
        call.conversation_id = conversation_id
        session.commit()
        print(f"Dispatched {agent_role} call to {business_id} ({phone_number}): conversation_id={conversation_id}")
        return conversation_id
    finally:
        session.close()


def dispatch_round_one() -> list[str]:
    """Plan §7.2/§11 Phase 3: real Twilio/ElevenLabs calls to the three
    persona numbers via the Caller agent, injecting the confirmed job's
    exact dynamic variables so every call describes the job identically.
    Requires ELEVENLABS_CALLER_AGENT_ID, ELEVENLABS_AGENT_PHONE_NUMBER_ID,
    a convai_write-scoped ELEVENLABS_API_KEY, and the PERSONA_*_PHONE env
    vars -- none of which are set yet as of this build (see task backlog)."""
    session = get_session()
    try:
        job = session.get(Job, DEMO_JOB_ID)
        if job is None:
            raise SystemExit(f"job {DEMO_JOB_ID} not found -- run scripts/seed_demo_job.py first")
        assert_confirmed(job)
    finally:
        session.close()

    agent_id = os.environ["ELEVENLABS_CALLER_AGENT_ID"]
    conversation_ids = []
    for business_id, phone_number in PERSONA_PHONE_NUMBERS.items():
        if not phone_number:
            print(f"Skipping {business_id}: no phone number configured")
            continue
        conversation_ids.append(_dispatch_one(job, agent_id, "caller", business_id, phone_number))
    return conversation_ids


def dispatch_round_two(candidate_business_id: str) -> str:
    """Plan §7.3/§11 Phase 4: calls one round-one candidate back with the
    Closer agent, once at least two round-one quotes exist so the leverage
    the Closer cites is real."""
    session = get_session()
    try:
        job = session.get(Job, DEMO_JOB_ID)
        if job is None:
            raise SystemExit(f"job {DEMO_JOB_ID} not found -- run scripts/seed_demo_job.py first")
        assert_confirmed(job)
    finally:
        session.close()

    phone_number = PERSONA_PHONE_NUMBERS.get(candidate_business_id, "")
    if not phone_number:
        raise SystemExit(f"no phone number configured for {candidate_business_id}")
    agent_id = os.environ["ELEVENLABS_CLOSER_AGENT_ID"]
    return _dispatch_one(job, agent_id, "closer", candidate_business_id, phone_number)


def _create_call_row(job: Job, agent_role: str, business_id: str) -> str:
    """Returns the new call_id (a plain string, not the ORM object) --
    session.commit() expires the object's attributes by default, and this
    session closes before the caller would otherwise read them, which
    raises DetachedInstanceError on first post-close attribute access."""
    session = get_session()
    try:
        call = Call(
            call_id=f"call_{uuid.uuid4().hex[:8]}",
            job_id=job.job_id,
            business_id=business_id,
            agent_role=agent_role,
            job_spec_sha256_used=job.job_spec_sha256,
        )
        session.add(call)
        session.commit()
        return call.call_id
    finally:
        session.close()


def _widget_link(agent_id: str) -> str:
    return f"{WEBHOOK_BASE_URL}/widget/?agent_id={agent_id}"


def dispatch_one_widget(job_id: str, agent_role: str, business_id: str) -> str:
    """Human-in-the-loop path (plan pivot: no Twilio number available --
    see task backlog). Creates the Call row exactly as the Twilio path
    does, sets the job's dynamic variables as the agent's live defaults via
    set_agent_dynamic_variables (so the widget needs nothing but agent_id
    in its URL), and returns a link for the persona to open and answer as
    that business. Not safe for true concurrent dispatch -- open and finish
    one persona's call before starting the next."""
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if job is None:
            raise SystemExit(f"job {job_id} not found -- run scripts/seed_demo_job.py first")
        assert_confirmed(job)
    finally:
        session.close()

    call_id = _create_call_row(job, agent_role, business_id)
    dynamic_variables = flatten_job_spec_to_dynamic_variables(job.job_id, job.job_spec_sha256, job.spec)
    call_vars = {**dynamic_variables, "call_id": call_id, "customer_name": "Daniel", "business_name": business_id}

    env_var = "ELEVENLABS_CALLER_AGENT_ID" if agent_role == "caller" else "ELEVENLABS_CLOSER_AGENT_ID"
    agent_id = os.environ[env_var]
    set_agent_dynamic_variables(agent_id, call_vars)

    link = _widget_link(agent_id)
    print(f"Call {call_id} ready for {business_id} ({agent_role}). Have the persona open:\n  {link}")
    return link


def dispatch_round_one_widget() -> list[str]:
    """Round 1 over the widget: one link per persona. Open/finish each in
    turn (see dispatch_one_widget's concurrency caveat) rather than handing
    all three out simultaneously."""
    job = None
    session = get_session()
    try:
        job = session.get(Job, DEMO_JOB_ID)
    finally:
        session.close()
    if job is None:
        raise SystemExit(f"job {DEMO_JOB_ID} not found -- run scripts/seed_demo_job.py first")

    return [
        dispatch_one_widget(DEMO_JOB_ID, "caller", business_id)
        for business_id in PERSONA_PHONE_NUMBERS  # reuse the same 3 persona business_ids, phone number unused here
    ]


def dispatch_round_two_widget(candidate_business_id: str) -> str:
    """Closer round 2 over the widget, for the same candidate business."""
    return dispatch_one_widget(DEMO_JOB_ID, "closer", candidate_business_id)


if __name__ == "__main__":
    dispatch_round_one()
