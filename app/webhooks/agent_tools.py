from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import Call, CallEvent, Job, QuoteRow, get_session

router = APIRouter(prefix="/webhooks/agent-tools", tags=["agent-tools"])


def _already_processed(session, call_id: str, idempotency_key: str, event_type: str, payload: dict) -> bool:
    """Idempotent webhook ingestion (plan §10): ElevenLabs may retry a tool
    call; a retried log_fee_line/log_outcome must not double-count."""
    existing = session.query(CallEvent).filter_by(idempotency_key=idempotency_key).first()
    if existing:
        return True
    session.add(CallEvent(call_id=call_id, idempotency_key=idempotency_key, event_type=event_type, payload=payload))
    return False


class SubmitJobSpecRequest(BaseModel):
    job_id: str
    spec: dict


@router.post("/submit_job_spec")
def submit_job_spec(req: SubmitJobSpecRequest) -> dict:
    """Estimator tool (plan §7.1): writes a DRAFT only. This never sets
    status to confirmed or computes job_spec_sha256 -- only
    app.api.jobs.confirm_job (the dashboard Confirm action) does that, so a
    voice-only "yes that's right" can never become the hash calls reuse."""
    session = get_session()
    try:
        job = session.get(Job, req.job_id)
        if job is None:
            job = Job(job_id=req.job_id, vertical_id="residential_moving", status="draft")
            session.add(job)
        if job.status == "confirmed":
            raise HTTPException(status_code=409, detail="job already confirmed; start a new job to change the spec")
        job.spec = req.spec
        session.commit()
        return {"job_id": job.job_id, "status": job.status}
    finally:
        session.close()


class GetJobSpecRequest(BaseModel):
    call_id: str


@router.post("/get_job_spec")
def get_job_spec(req: GetJobSpecRequest) -> dict:
    """Caller/Closer tool: fetch the canonical spec for this call. Returns
    the hash the call was dispatched with, so a prompt bug can never cause
    an agent to act on a spec other than the one the job was confirmed with."""
    session = get_session()
    try:
        call = session.get(Call, req.call_id)
        if call is None:
            raise HTTPException(status_code=404, detail="call not found")
        job = session.get(Job, call.job_id)
        return {"job_spec_sha256": call.job_spec_sha256_used, "spec": job.spec}
    finally:
        session.close()


class LogFeeLineRequest(BaseModel):
    call_id: str
    quote_id: str
    category: str
    status: str
    amount: float | None = None
    unit: str = "total"
    idempotency_key: str


@router.post("/log_fee_line")
def log_fee_line(req: LogFeeLineRequest) -> dict:
    """Caller/Closer tool, called incrementally as each fee is stated (plan
    §7.2) -- smaller typed tools are safer than one large end-of-call
    payload. `status` must be one of quoted/included/not_applicable/unknown/
    refused; a missing fee is never silently treated as $0."""
    from app.db import FeeLineRow
    from app.services.quote_normalization import recompute_completeness

    session = get_session()
    try:
        if _already_processed(session, req.call_id, req.idempotency_key, "log_fee_line", req.model_dump()):
            session.commit()
            return {"status": "duplicate_ignored"}

        quote = session.get(QuoteRow, req.quote_id)
        if quote is None:
            call = session.get(Call, req.call_id)
            if call is None:
                raise HTTPException(status_code=404, detail="call not found")
            quote = QuoteRow(
                quote_id=req.quote_id,
                call_id=req.call_id,
                business_id=call.business_id,
                job_spec_sha256=call.job_spec_sha256_used,
            )
            session.add(quote)

        session.add(
            FeeLineRow(quote_id=req.quote_id, category=req.category, status=req.status, amount=req.amount, unit=req.unit)
        )
        session.commit()

        job = session.get(Job, session.get(Call, req.call_id).job_id)
        recompute_completeness(req.quote_id, job.vertical_id)
        return {"status": "logged"}
    finally:
        session.close()


class SetQuoteTotalRequest(BaseModel):
    call_id: str
    quote_id: str
    quoted_total: float
    estimate_type: str = "unknown"
    idempotency_key: str


@router.post("/set_quote_total")
def set_quote_total(req: SetQuoteTotalRequest) -> dict:
    session = get_session()
    try:
        if _already_processed(session, req.call_id, req.idempotency_key, "set_quote_total", req.model_dump()):
            session.commit()
            return {"status": "duplicate_ignored"}
        quote = session.get(QuoteRow, req.quote_id)
        if quote is None:
            raise HTTPException(status_code=404, detail="quote not found; log a fee line first")
        quote.quoted_total = req.quoted_total
        quote.estimate_type = req.estimate_type
        session.commit()
        return {"status": "logged"}
    finally:
        session.close()


class LogAssumptionRequest(BaseModel):
    call_id: str
    quote_id: str
    assumption: str
    idempotency_key: str


@router.post("/log_assumption_or_exclusion")
def log_assumption_or_exclusion(req: LogAssumptionRequest) -> dict:
    session = get_session()
    try:
        if _already_processed(session, req.call_id, req.idempotency_key, "log_assumption", req.model_dump()):
            session.commit()
            return {"status": "duplicate_ignored"}
        quote = session.get(QuoteRow, req.quote_id)
        if quote is None:
            raise HTTPException(status_code=404, detail="quote not found")
        session.commit()
        return {"status": "logged"}
    finally:
        session.close()


class LogOutcomeRequest(BaseModel):
    call_id: str
    outcome: str
    reason: str | None = None
    idempotency_key: str


@router.post("/log_outcome")
def log_outcome(req: LogOutcomeRequest) -> dict:
    """Caller/Closer must call this before intentional hang-up (plan §7.2).
    Calls that end without it get reconciled later by the post-call webhook
    or app.services.calling.reconcile_missing_outcomes -- never left null."""
    session = get_session()
    try:
        if _already_processed(session, req.call_id, req.idempotency_key, "log_outcome", req.model_dump()):
            session.commit()
            return {"status": "duplicate_ignored"}
        call = session.get(Call, req.call_id)
        if call is None:
            raise HTTPException(status_code=404, detail="call not found")
        call.outcome = req.outcome
        call.outcome_reason = req.reason
        call.reconciled = True
        session.commit()
        return {"status": "logged"}
    finally:
        session.close()


class GetBestQuoteSoFarRequest(BaseModel):
    job_id: str
    exclude_business_id: str
    minimum_completeness: float = 0.5


@router.post("/get_best_quote_so_far")
def get_best_quote_so_far(req: GetBestQuoteSoFarRequest) -> dict:
    """Live leverage lookup for the Closer (plan §7.3, §8 anti-staging
    protocol). Only ever returns a quote that actually exists in the
    database with a stated total -- the agent can never be fed a number
    that wasn't really quoted, and the eligibility floor keeps a barely-
    itemized quote from being used as fake leverage."""
    session = get_session()
    try:
        calls = session.query(Call).filter_by(job_id=req.job_id).all()
        call_ids = [c.call_id for c in calls if c.business_id != req.exclude_business_id]
        candidates = (
            session.query(QuoteRow)
            .filter(QuoteRow.call_id.in_(call_ids))
            .filter(QuoteRow.quoted_total.isnot(None))
            .all()
        )
        candidates = [
            q for q in candidates if (q.completeness_score is None or q.completeness_score >= req.minimum_completeness)
        ]
        if not candidates:
            return {"available": False}
        best = min(candidates, key=lambda q: q.quoted_total)
        return {
            "available": True,
            "quote_id": best.quote_id,
            "business_id": best.business_id,
            "quoted_total": best.quoted_total,
        }
    finally:
        session.close()
