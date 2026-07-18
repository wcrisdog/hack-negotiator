from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"


class DocumentRef(BaseModel):
    type: str
    file_id: str


class SourceProvenance(BaseModel):
    voice_interview: bool = False
    documents: list[DocumentRef] = Field(default_factory=list)
    merge_strategy: str = "document_prefill_voice_resolve_conflicts"


class JobEnvelope(BaseModel):
    """Generic envelope (plan §5.1). `spec` holds the vertical-specific
    payload, validated against that vertical's own JSON Schema in
    config/verticals/<id>/job_spec.schema.json -- never against Python code,
    so switching verticals means swapping a config file."""

    job_id: str
    vertical_id: str
    status: JobStatus = JobStatus.DRAFT
    spec_version: int = 1
    source_provenance: SourceProvenance = Field(default_factory=SourceProvenance)
    spec: dict[str, Any] = Field(default_factory=dict)
    confirmed_at: str | None = None
    canonical_json: str | None = None
    job_spec_sha256: str | None = None
