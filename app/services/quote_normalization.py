from __future__ import annotations

import json
from pathlib import Path

from app.db import FeeLineRow, QuoteRow, get_session
from app.schemas.quote import FeeLine, FeeStatus, Quote


def load_expected_categories(vertical_id: str) -> list[str]:
    path = Path("config/verticals") / vertical_id / "quote_taxonomy.json"
    return json.loads(path.read_text())["fee_categories"]


def recompute_completeness(quote_id: str, vertical_id: str) -> float:
    """Run after each log_fee_line webhook so completeness_score is always
    current (plan §5.3: a missing fee is never assumed to be $0)."""
    session = get_session()
    try:
        quote_row = session.get(QuoteRow, quote_id)
        fee_rows = session.query(FeeLineRow).filter_by(quote_id=quote_id).all()
        fee_lines = [FeeLine(category=r.category, status=FeeStatus(r.status), amount=r.amount) for r in fee_rows]
        expected = load_expected_categories(vertical_id)
        temp = Quote(
            quote_id=quote_id,
            call_id=quote_row.call_id,
            business_id=quote_row.business_id,
            job_spec_sha256=quote_row.job_spec_sha256,
            fee_lines=fee_lines,
        )
        score = temp.compute_completeness(expected)
        quote_row.completeness_score = score
        quote_row.known_fee_sum = temp.compute_known_fee_sum()
        session.commit()
        return score
    finally:
        session.close()
