from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Business, Call, FeeLineRow, Job, QuoteRow, get_session  # noqa: E402

OUTPUT_DIR = Path("data/dataset_export")


def _redact_business(business: Business) -> dict:
    """Plan §13 privacy check, §17 deliverable #7: a demo-persona's real
    name/phone never leaves this function -- only a synthetic identifier is
    exported. Discovered businesses (source_type="discovered") keep their
    public name/source_url since that data is already public."""
    if business.source_type == "demo_persona":
        return {
            "business_id": business.business_id,
            "name": "REDACTED (consenting demo persona)",
            "source_type": "demo_persona",
        }
    return {
        "business_id": business.business_id,
        "name": business.name,
        "source_type": business.source_type,
        "source_url": business.source_url,
        "retrieved_at": business.retrieved_at.isoformat() if business.retrieved_at else None,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    session = get_session()
    try:
        jobs = session.query(Job).all()
        businesses = session.query(Business).all()
        calls = session.query(Call).all()
        quotes = session.query(QuoteRow).all()
        fee_lines = session.query(FeeLineRow).all()

        dataset = {
            "jobs": [
                {
                    "job_id": j.job_id,
                    "vertical_id": j.vertical_id,
                    "status": j.status,
                    "job_spec_sha256": j.job_spec_sha256,
                    "spec": j.spec,
                }
                for j in jobs
            ],
            "businesses": [_redact_business(b) for b in businesses],
            "calls": [
                {
                    "call_id": c.call_id,
                    "job_id": c.job_id,
                    "business_id": c.business_id,
                    "agent_role": c.agent_role,
                    "job_spec_sha256_used": c.job_spec_sha256_used,
                    "outcome": c.outcome,
                    "outcome_reason": c.outcome_reason,
                    # Recording/conversation URLs are internal, not part of the public dataset.
                }
                for c in calls
            ],
            "quotes": [
                {
                    "quote_id": q.quote_id,
                    "call_id": q.call_id,
                    "business_id": q.business_id,
                    "job_spec_sha256": q.job_spec_sha256,
                    "estimate_type": q.estimate_type,
                    "quoted_total": q.quoted_total,
                    "known_fee_sum": q.known_fee_sum,
                    "completeness_score": q.completeness_score,
                }
                for q in quotes
            ],
            "fee_lines": [
                {"quote_id": f.quote_id, "category": f.category, "status": f.status, "amount": f.amount}
                for f in fee_lines
            ],
        }

        out_path = OUTPUT_DIR / "dataset.json"
        out_path.write_text(json.dumps(dataset, indent=2, default=str))
        print(f"Exported dataset to {out_path} ({len(jobs)} job(s), {len(calls)} call(s), {len(quotes)} quote(s))")
    finally:
        session.close()


if __name__ == "__main__":
    main()
