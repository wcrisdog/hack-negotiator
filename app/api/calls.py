from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.jobs import assert_confirmed
from app.db import Business, Call, Job, get_session

router = APIRouter(prefix="/calls", tags=["calls"])


class DispatchRequest(BaseModel):
    job_id: str
    business_ids: list[str]
    agent_role: str = "caller"


@router.post("/dispatch")
def dispatch_calls(req: DispatchRequest) -> dict:
    """Creates Call rows stamped with the job's confirmed hash, proving
    verbatim reuse (plan §2, §13 test: 'Verbatim reuse'). The actual
    ElevenLabs/Twilio outbound_call() invocation (app.services.calling) is
    a separate step so this endpoint stays testable without live
    credentials -- see scripts/run_demo.py for the wiring that calls both."""
    session = get_session()
    try:
        job = session.get(Job, req.job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        assert_confirmed(job)

        created = []
        for business_id in req.business_ids:
            business = session.get(Business, business_id)
            if business is None:
                raise HTTPException(status_code=404, detail=f"business {business_id} not found")
            call = Call(
                call_id=f"call_{uuid.uuid4().hex[:8]}",
                job_id=job.job_id,
                business_id=business_id,
                agent_role=req.agent_role,
                job_spec_sha256_used=job.job_spec_sha256,
            )
            session.add(call)
            created.append(call.call_id)
        session.commit()
        return {"job_spec_sha256": job.job_spec_sha256, "call_ids": created}
    finally:
        session.close()
