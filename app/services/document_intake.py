from __future__ import annotations

import base64
import json
import os
from pathlib import Path

EXTRACTION_INSTRUCTIONS = (
    "Extract residential-moving job fields from this existing quote PDF into "
    "the JSON schema below. Use null for any field the document does not "
    "state -- never guess or invent a value. Return JSON only, matching the "
    "schema's shape."
)


def extract_job_spec_from_pdf(pdf_path: str, schema: dict) -> dict:
    """Plan §7.1 document workflow step 2. Requires OPENAI_API_KEY (not yet
    set as of this build -- see task backlog). Output merges into the same
    job-spec schema as the voice interview (app.services.job_spec.merge_job_spec),
    with only fields the document actually states -- everything else stays
    null so the Estimator's voice interview fills the gaps, not this function."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set; cannot run document intake")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    data = base64.b64encode(Path(pdf_path).read_bytes()).decode("utf-8")
    response = client.chat.completions.create(
        model="gpt-4.1",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": EXTRACTION_INSTRUCTIONS},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Target schema:\n{json.dumps(schema)}"},
                    {
                        "type": "file",
                        "file": {
                            "filename": Path(pdf_path).name,
                            "file_data": f"data:application/pdf;base64,{data}",
                        },
                    },
                ],
            },
        ],
    )
    return json.loads(response.choices[0].message.content)
