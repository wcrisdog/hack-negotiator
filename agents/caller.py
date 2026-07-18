from __future__ import annotations

import json

from agents._common import (
    DEFAULT_LLM,
    DEFAULT_VOICE_ID,
    PROMPTS_DIR,
    VERTICAL_DIR,
    end_call_tool,
    get_client,
    load_json,
    load_text,
    webhook_tool,
    with_reference_appendix,
)

QUOTE_TAXONOMY = load_json(VERTICAL_DIR / "quote_taxonomy.json")


def build_prompt() -> str:
    base = load_text(PROMPTS_DIR / "caller.md")
    return with_reference_appendix(base, {"quote_taxonomy.json": json.dumps(QUOTE_TAXONOMY, indent=2)})


def build_config() -> dict:
    return {
        "agent": {
            "first_message": (
                "Hi, this is an AI assistant calling on behalf of {{customer_name}} "
                "about a move from {{origin_city}}, {{origin_state}} to "
                "{{destination_city}}, {{destination_state}} -- is this a moving company?"
            ),
            "language": "en",
            "prompt": {
                "prompt": build_prompt(),
                "llm": DEFAULT_LLM,
                "temperature": 0.4,
                "tools": [
                    webhook_tool(
                        name="log_fee_line",
                        description="Log one itemized fee line as soon as it's stated. Call this incrementally during the call, not all at once at the end. status must be one of: quoted, included, not_applicable, unknown, refused -- never guess a number.",
                        path="/webhooks/agent-tools/log_fee_line",
                        request_body_schema={
                            "type": "object",
                            "properties": {
                                "call_id": {"type": "string"},
                                "quote_id": {"type": "string"},
                                "category": {"type": "string", "enum": QUOTE_TAXONOMY["fee_categories"]},
                                "status": {"type": "string", "enum": QUOTE_TAXONOMY["allowed_statuses"]},
                                "amount": {"type": "number"},
                                "idempotency_key": {"type": "string"},
                            },
                            "required": ["call_id", "quote_id", "category", "status", "idempotency_key"],
                        },
                    ),
                    webhook_tool(
                        name="set_quote_total",
                        description="Record the counterparty's stated total and whether it's binding, non-binding, or unknown.",
                        path="/webhooks/agent-tools/set_quote_total",
                        request_body_schema={
                            "type": "object",
                            "properties": {
                                "call_id": {"type": "string"},
                                "quote_id": {"type": "string"},
                                "quoted_total": {"type": "number"},
                                "estimate_type": {"type": "string", "enum": ["binding", "non_binding", "unknown"]},
                                "idempotency_key": {"type": "string"},
                            },
                            "required": ["call_id", "quote_id", "quoted_total", "idempotency_key"],
                        },
                    ),
                    webhook_tool(
                        name="log_outcome",
                        description="Call this before intentionally ending the call, with exactly one terminal outcome. Never end a call without calling this.",
                        path="/webhooks/agent-tools/log_outcome",
                        request_body_schema={
                            "type": "object",
                            "properties": {
                                "call_id": {"type": "string"},
                                "outcome": {
                                    "type": "string",
                                    "enum": ["itemized_quote", "callback_committed", "documented_decline"],
                                },
                                "reason": {
                                    "type": "string",
                                    "enum": ["no_answer", "hung_up", "refused_to_quote", "invalid_number", "tool_failure"],
                                },
                                "idempotency_key": {"type": "string"},
                            },
                            "required": ["call_id", "outcome", "idempotency_key"],
                        },
                    ),
                ],
                "built_in_tools": {"end_call": end_call_tool()},
            },
        },
        "tts": {"voice_id": DEFAULT_VOICE_ID},
    }


def create_agent() -> str:
    client = get_client()
    response = client.conversational_ai.agents.create(
        name="The Negotiator -- Caller",
        conversation_config=build_config(),
    )
    return response.agent_id


if __name__ == "__main__":
    agent_id = create_agent()
    print(f"Created Caller agent: {agent_id}")
    print("Save this as ELEVENLABS_CALLER_AGENT_ID in .env")
