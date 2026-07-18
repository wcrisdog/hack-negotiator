from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

VERTICAL_DIR = Path("config/verticals/residential_moving")
PROMPTS_DIR = Path("agents/prompts")
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # "George", same as example.py
DEFAULT_LLM = "gpt-4.1"  # plan §16: spend OpenAI credits, not a separate LLM budget


def load_text(path: Path) -> str:
    return path.read_text()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def webhook_base_url() -> str:
    return os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000").rstrip("/")


def webhook_tool(
    name: str,
    description: str,
    path: str,
    request_body_schema: dict[str, Any],
    method: str = "POST",
) -> dict[str, Any]:
    """Shape verified against the installed elevenlabs==2.58.0 SDK's
    PromptAgentApiModelOutputToolsItem_Webhook / WebhookToolApiSchemaConfigOutput
    (see the introspection notes in this session -- plain dicts validate
    fine against ConversationalConfig.model_validate)."""
    return {
        "type": "webhook",
        "name": name,
        "description": description,
        "api_schema": {
            "url": f"{webhook_base_url()}{path}",
            "method": method,
            "request_body_schema": request_body_schema,
        },
    }


def with_reference_appendix(prompt_text: str, sections: dict[str, str]) -> str:
    """Embeds reference config (checklist/taxonomy/levers) directly into the
    system prompt instead of ElevenLabs' knowledge_base attachment, which
    would require uploading documents and wiring real document_ids first.
    Same effect for a hackathon build -- the agent still sees the config,
    just inline rather than RAG-retrieved."""
    appendix = "\n\n## Reference (from vertical config -- do not deviate from this data)\n"
    for title, content in sections.items():
        appendix += f"\n### {title}\n{content}\n"
    return prompt_text + appendix


def end_call_tool() -> dict:
    """Minimal valid shape for the built-in end_call system tool, verified
    against elevenlabs==2.58.0's SystemToolConfigOutput (a bare `{}` fails
    validation -- `name` and `params` are required)."""
    return {"name": "end_call", "params": {}}


def get_client():
    from elevenlabs.client import ElevenLabs

    return ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
