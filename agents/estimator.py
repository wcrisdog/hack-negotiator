from __future__ import annotations

import json

from agents._common import (
    DEFAULT_LLM,
    DEFAULT_VOICE_ID,
    PROMPTS_DIR,
    VERTICAL_DIR,
    get_client,
    load_json,
    load_text,
    webhook_tool,
    with_reference_appendix,
)

JOB_SPEC_SCHEMA = load_json(VERTICAL_DIR / "job_spec.schema.json")
INTAKE_CHECKLIST = load_text(VERTICAL_DIR / "intake_checklist.md")


def build_prompt() -> str:
    base = load_text(PROMPTS_DIR / "estimator.md")
    return with_reference_appendix(base, {"intake_checklist.md": INTAKE_CHECKLIST})


def build_config() -> dict:
    return {
        "agent": {
            "first_message": (
                "Hi, I'm an AI assistant helping you build a moving quote request -- "
                "this isn't a real mover yet, just gathering details before we call anyone."
            ),
            "language": "en",
            "prompt": {
                "prompt": build_prompt(),
                "llm": DEFAULT_LLM,
                "temperature": 0.2,
                "tools": [
                    webhook_tool(
                        name="submit_job_spec",
                        description="Submit the draft moving job specification once the checklist is complete and the customer has confirmed the summary out loud. This writes a DRAFT only -- the customer still confirms in the dashboard before any calls are made.",
                        path="/webhooks/agent-tools/submit_job_spec",
                        request_body_schema={
                            "type": "object",
                            "properties": {
                                "job_id": {"type": "string"},
                                "spec": JOB_SPEC_SCHEMA,
                            },
                            "required": ["job_id", "spec"],
                        },
                    ),
                ],
            },
        },
        "tts": {"voice_id": DEFAULT_VOICE_ID},
    }


def create_agent() -> str:
    """Creates the Estimator agent via the ElevenLabs API. Run once; save the
    returned agent_id into .env as ELEVENLABS_ESTIMATOR_AGENT_ID. Re-running
    creates a new agent -- use agents/estimator.py's `update_agent` (or the
    dashboard) to edit an existing one instead of recreating it."""
    client = get_client()
    response = client.conversational_ai.agents.create(
        name="The Negotiator -- Estimator",
        conversation_config=build_config(),
    )
    return response.agent_id


if __name__ == "__main__":
    agent_id = create_agent()
    print(f"Created Estimator agent: {agent_id}")
    print("Save this as ELEVENLABS_ESTIMATOR_AGENT_ID in .env")
