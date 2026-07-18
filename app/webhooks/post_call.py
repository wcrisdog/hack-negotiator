from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.db import Call, get_session

router = APIRouter(prefix="/webhooks/elevenlabs", tags=["post-call"])


class PostCallTranscriptionPayload(BaseModel):
    conversation_id: str
    call_id: str
    transcript: list[dict] = []
    status: str = "done"


@router.post("/post-call-transcription")
def post_call_transcription(payload: PostCallTranscriptionPayload) -> dict:
    """ElevenLabs post_call_transcription webhook target (plan §4.3, §7.2
    'Add a post-call reconciliation job for dropped calls and missing
    outcomes'). If the agent never called log_outcome before the call
    ended, this backfills a documented_decline rather than leaving the row
    ambiguous forever."""
    session = get_session()
    try:
        call = session.get(Call, payload.call_id)
        if call is None:
            return {"status": "ignored_unknown_call"}
        call.conversation_id = payload.conversation_id
        call.transcript = payload.transcript
        if not call.reconciled:
            call.outcome = "documented_decline"
            call.outcome_reason = "hung_up" if payload.status != "done" else "tool_failure"
            call.reconciled = True
        session.commit()
        return {"status": "stored"}
    finally:
        session.close()


class PostCallAudioPayload(BaseModel):
    conversation_id: str
    call_id: str
    recording_url: str


@router.post("/post-call-audio")
def post_call_audio(payload: PostCallAudioPayload) -> dict:
    session = get_session()
    try:
        call = session.get(Call, payload.call_id)
        if call is None:
            return {"status": "ignored_unknown_call"}
        call.recording_url = payload.recording_url
        session.commit()
        return {"status": "stored"}
    finally:
        session.close()
