from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.db import Call, FeeLineRow, Job, QuoteRow, get_session
from app.schemas.quote import FeeLine, Quote
from app.services.narrative import generate_narrative
from app.services.ranking import price_order, recommended_order

router = APIRouter(prefix="/jobs", tags=["reports"])


def _vertical_config(vertical_id: str) -> dict:
    path = Path("config/verticals") / vertical_id / "vertical.json"
    return json.loads(path.read_text())


@router.get("/{job_id}/report")
def get_report(job_id: str) -> dict:
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")

        calls = session.query(Call).filter_by(job_id=job_id).all()
        call_hashes = {c.job_spec_sha256_used for c in calls}
        quote_rows = session.query(QuoteRow).filter(QuoteRow.call_id.in_([c.call_id for c in calls])).all()

        quotes: list[Quote] = []
        for qr in quote_rows:
            fee_rows = session.query(FeeLineRow).filter_by(quote_id=qr.quote_id).all()
            fee_lines = [
                FeeLine(category=fr.category, status=fr.status, amount=fr.amount, unit=fr.unit) for fr in fee_rows
            ]
            quotes.append(
                Quote(
                    quote_id=qr.quote_id,
                    call_id=qr.call_id,
                    business_id=qr.business_id,
                    job_spec_sha256=qr.job_spec_sha256,
                    estimate_type=qr.estimate_type,
                    fee_lines=fee_lines,
                    quoted_total=qr.quoted_total,
                    known_fee_sum=qr.known_fee_sum,
                    completeness_score=qr.completeness_score,
                )
            )

        vertical_config = _vertical_config(job.vertical_id)
        price_ranked = price_order(quotes)
        recommended = recommended_order(quotes, vertical_config)

        report = {
            "job_id": job.job_id,
            "job_spec_sha256": job.job_spec_sha256,
            # Plan §13 "Verbatim reuse" proof: every call's stamped hash must
            # equal the job's single confirmed hash.
            "verbatim_reuse_proof": {
                "all_calls_used_same_hash": call_hashes.issubset({job.job_spec_sha256}),
                "hashes_seen": list(call_hashes),
            },
            "calls": [
                {
                    "call_id": c.call_id,
                    "business_id": c.business_id,
                    "agent_role": c.agent_role,
                    "outcome": c.outcome,
                    "outcome_reason": c.outcome_reason,
                    "conversation_id": c.conversation_id,
                    "recording_url": c.recording_url,
                }
                for c in calls
            ],
            "price_order": [q.quote_id for q in price_ranked],
            "recommended_order": [
                {
                    "quote_id": e["quote"].quote_id,
                    "business_id": e["quote"].business_id,
                    "quoted_total": e["quote"].quoted_total,
                    "completeness_score": e["completeness_score"],
                    "requires_clarification": e["requires_clarification"],
                    "red_flags": e["red_flags"],
                }
                for e in recommended
            ],
        }
        report["narrative"] = generate_narrative(report)
        return report
    finally:
        session.close()
