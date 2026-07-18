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
NEGOTIATION_LEVERS = load_json(VERTICAL_DIR / "negotiation_levers.json")


def build_prompt() -> str:
    base = load_text(PROMPTS_DIR / "closer.md")
    return with_reference_appendix(
        base,
        {
            "quote_taxonomy.json": json.dumps(QUOTE_TAXONOMY, indent=2),
            "negotiation_levers.json": json.dumps(NEGOTIATION_LEVERS, indent=2),
        },
    )


def build_config() -> dict:
    return {
        "agent": {
            "first_message": (
                "Hi, this is an AI assistant calling back on behalf of {{customer_name}} "
                "about the moving quote {{business_name}} gave earlier for the move from "
                "{{origin_city}}, {{origin_state}} to {{destination_city}}, {{destination_state}}."
            ),
            "language": "en",
            "prompt": {
                "prompt": build_prompt(),
                "llm": DEFAULT_LLM,
                "temperature": 0.4,
                "tools": [
                    webhook_tool(
                        name="get_best_quote_so_far",
                        description="The ONLY source of a competing quote number you may ever cite. Call this before mentioning any competing price. If available is false, do not claim a competing quote exists.",
                        path="/webhooks/agent-tools/get_best_quote_so_far",
                        request_body_schema={
                            "type": "object",
                            "properties": {
                                "job_id": {"type": "string"},
                                "exclude_business_id": {"type": "string"},
                            },
                            "required": ["job_id", "exclude_business_id"],
                        },
                    ),
                    webhook_tool(
                        name="log_fee_line",
                        description="Log a revised itemized fee line. Set is_revision true and include previous_amount when this changes a number from the earlier call.",
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
                        description="Record the revised total. Use is_revision/previous_amount fields to prove the price moved because of leverage gathered this call.",
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
                        description="Call this before intentionally ending the call, with exactly one terminal outcome.",
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
        name="The Negotiator -- Closer",
        conversation_config=build_config(),
    )
    return response.agent_id


if __name__ == "__main__":
    agent_id = create_agent()
    print(f"Created Closer agent: {agent_id}")
    print("Save this as ELEVENLABS_CLOSER_AGENT_ID in .env")
