from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import Job, get_session
from app.services.canonicalize import confirm_job_spec

router = APIRouter(prefix="/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    vertical_id: str
    spec: dict = {}


class ConfirmJobRequest(BaseModel):
    spec: dict


@router.post("")
def create_job(req: CreateJobRequest) -> dict:
    session = get_session()
    try:
        job = Job(job_id=f"job_{uuid.uuid4().hex[:8]}", vertical_id=req.vertical_id, status="draft", spec=req.spec)
        session.add(job)
        session.commit()
        return {"job_id": job.job_id, "status": job.status}
    finally:
        session.close()


@router.post("/{job_id}/confirm")
def confirm_job(job_id: str, req: ConfirmJobRequest) -> dict:
    """User confirmation gate (plan §2, §3.1, §15): this is the only place a
    job's spec is canonicalized and hashed. Nothing else may set
    job_spec_sha256, and app.api.calls.assert_confirmed is the only path
    that reads it back for dispatch."""
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        canonical_json, job_spec_sha256 = confirm_job_spec(req.spec)
        job.spec = req.spec
        job.canonical_json = canonical_json
        job.job_spec_sha256 = job_spec_sha256
        job.status = "confirmed"
        job.confirmed_at = datetime.now(timezone.utc)
        session.commit()
        return {"job_id": job.job_id, "status": job.status, "job_spec_sha256": job_spec_sha256}
    finally:
        session.close()


@router.get("/{job_id}")
def get_job(job_id: str) -> dict:
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return {
            "job_id": job.job_id,
            "vertical_id": job.vertical_id,
            "status": job.status,
            "spec": job.spec,
            "job_spec_sha256": job.job_spec_sha256,
        }
    finally:
        session.close()


def assert_confirmed(job: Job) -> None:
    """Dispatch guard (plan §2 row "User confirms the job spec before
    calls", §15): calling a job that is not confirmed is a hard 409, not a
    warning."""
    if job.status != "confirmed" or not job.job_spec_sha256:
        raise HTTPException(status_code=409, detail="job is not confirmed; cannot dispatch calls")
