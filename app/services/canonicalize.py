from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(spec: dict[str, Any]) -> str:
    """Stable-key-ordered, whitespace-minimal JSON so the same logical spec
    always produces the same string and the same hash (plan §2, §5.1)."""
    return json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def spec_hash(spec: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(spec).encode("utf-8")).hexdigest()


def confirm_job_spec(spec: dict[str, Any]) -> tuple[str, str]:
    """Freeze a draft spec: returns (canonical_json, job_spec_sha256). Call
    once, at the moment the user clicks Confirm in the dashboard -- never
    recompute afterward, since every call must reuse this exact hash."""
    cjson = canonical_json(spec)
    return cjson, hashlib.sha256(cjson.encode("utf-8")).hexdigest()
