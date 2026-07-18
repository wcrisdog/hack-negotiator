from __future__ import annotations

import json
import os

TEMPLATE_FALLBACK = (
    "Report for job {job_id}: {n_quotes} quote(s) gathered. "
    "Top recommendation: {top_business} at ${top_total} "
    "(completeness {top_completeness:.0%}). "
    "See red_flags and recommended_order for full detail."
)


def _template_narrative(report: dict) -> str:
    recs = report.get("recommended_order") or []
    if not recs:
        return f"Report for job {report.get('job_id')}: no quotes gathered yet."
    top = recs[0]
    return TEMPLATE_FALLBACK.format(
        job_id=report.get("job_id"),
        n_quotes=len(recs),
        top_business=top.get("business_id"),
        top_total=top.get("quoted_total"),
        top_completeness=top.get("completeness_score") or 0.0,
    )


def generate_narrative(report: dict) -> str:
    """Plan §9.3: an LLM may write prose from the already-validated report,
    but must not introduce any fact/number absent from it. Falls back to a
    deterministic template if OPENAI_API_KEY is unset or the call fails --
    the report must work even without the LLM step (plan §9.3)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _template_narrative(report)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4.1",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Write a short, plain-language paragraph summarizing this "
                        "moving-quote comparison for a consumer. Use ONLY the facts "
                        "and numbers in the JSON below. Do not introduce any price, "
                        "fee, or claim that is not present in the JSON."
                    ),
                },
                {"role": "user", "content": json.dumps(report)},
            ],
        )
        return (response.choices[0].message.content or "").strip() or _template_narrative(report)
    except Exception:
        return _template_narrative(report)
