from __future__ import annotations

from typing import Any

from app.services.canonicalize import canonical_json


def merge_job_spec(voice_draft: dict[str, Any], document_draft: dict[str, Any] | None) -> dict[str, Any]:
    """document_prefill_voice_resolve_conflicts (plan §7.1): document fields
    seed the draft, voice interview fills gaps. A field is only overwritten
    by voice if the document left it null -- so a stated document fact is
    never silently clobbered by a mis-heard voice answer."""
    if not document_draft:
        return voice_draft

    merged = dict(document_draft)
    for key, value in voice_draft.items():
        if key not in merged or merged[key] is None:
            merged[key] = value
    return merged


def flatten_job_spec_to_dynamic_variables(job_id: str, job_spec_sha256: str, spec: dict[str, Any]) -> dict[str, str]:
    """Single source of truth for what an ElevenLabs agent sees per call
    (plan §5, "reused verbatim"). The canonical JSON is authoritative;
    these flattened fields are convenience variables derived from it, never
    edited directly, so they can never drift from the confirmed spec."""
    origin = spec.get("origin", {})
    destination = spec.get("destination", {})
    return {
        "job_id": job_id,
        "job_spec_sha256": job_spec_sha256,
        "job_spec_json": canonical_json(spec),
        "origin_city": str(origin.get("city", "")),
        "origin_state": str(origin.get("state", "")),
        "destination_city": str(destination.get("city", "")),
        "destination_state": str(destination.get("state", "")),
        "distance_miles": str(spec.get("distance_miles", "")),
        "move_date": str(spec.get("move_date", {}).get("preferred", "")),
    }
