from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from app.db import Call, get_session


def place_outbound_call(agent_id: str, to_number: str, dynamic_variables: dict) -> str:
    """Places a real outbound call via ElevenLabs' native Twilio integration
    (plan §4.3). Verified against the installed elevenlabs==2.58.0 SDK:
    `client.conversational_ai.twilio.outbound_call(agent_id=..., agent_phone_number_id=...,
    to_number=..., conversation_initiation_client_data={"dynamic_variables": ...})`.
    Requires ELEVENLABS_API_KEY (set) and ELEVENLABS_AGENT_PHONE_NUMBER_ID
    (a Twilio number imported into the ElevenLabs dashboard -- not yet done
    as of this build; see task backlog)."""
    from elevenlabs.client import ElevenLabs

    agent_phone_number_id = os.environ["ELEVENLABS_AGENT_PHONE_NUMBER_ID"]
    client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
    result = client.conversational_ai.twilio.outbound_call(
        agent_id=agent_id,
        agent_phone_number_id=agent_phone_number_id,
        to_number=to_number,
        conversation_initiation_client_data={"dynamic_variables": dynamic_variables},
        call_recording_enabled=True,
    )
    return result.conversation_id


def set_agent_dynamic_variables(agent_id: str, dynamic_variables: dict) -> None:
    """Sets the agent's default dynamic-variable VALUES (not just a schema)
    via `dynamic_variable_placeholders` -- verified against the installed
    elevenlabs==2.58.0 SDK's ConversationalConfig. Any session that starts
    without its own per-session dynamic_variables (e.g. a browser widget
    opened with just an agent_id, no signed URL or client-side overrides)
    falls back to these defaults. This is what makes the widget/human-in-
    the-loop calling path (plan pivot: no Twilio number available) work
    without needing to verify an unconfirmed client-side JS API for passing
    per-session dynamic variables -- call this right before a persona opens
    the widget page, exactly as scripts/run_demo.py's widget dispatch does.

    Not safe to call concurrently for two different calls against the same
    agent (it mutates a shared default) -- fine for a hackathon demo run
    one call at a time, not for true parallel dispatch."""
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
    client.conversational_ai.agents.update(
        agent_id=agent_id,
        conversation_config={"agent": {"dynamic_variables": {"dynamic_variable_placeholders": dynamic_variables}}},
    )


def reconcile_missing_outcomes(stale_after_minutes: int = 30) -> list[str]:
    """Failure reconciliation (plan §2, §7.2, §11 Phase 3): any call still
    unreconciled after it should plausibly have ended gets a
    documented_decline/tool_failure record, so no call stays ambiguous.
    Run this on a schedule (or before generating a report) in addition to
    the post-call-webhook reconciliation in app/webhooks/post_call.py."""
    session = get_session()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_after_minutes)
        stale = session.query(Call).filter(Call.reconciled.is_(False), Call.created_at < cutoff).all()
        reconciled_ids = []
        for call in stale:
            call.outcome = "documented_decline"
            call.outcome_reason = "tool_failure"
            call.reconciled = True
            reconciled_ids.append(call.call_id)
        session.commit()
        return reconciled_ids
    finally:
        session.close()
