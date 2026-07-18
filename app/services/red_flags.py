from __future__ import annotations

import statistics
from typing import Any

from app.schemas.quote import Quote

INSUFFICIENT_DATA = "insufficient_comparison_data"


def below_market_flag(
    candidate: Quote,
    peer_quotes: list[Quote],
    threshold_ratio: float = 0.70,
    minimum_peer_quotes: int = 2,
    completeness_floor: float = 0.5,
) -> dict[str, Any]:
    """30%-below-peer-median rule (plan §9.1). This never fabricates a
    benchmark: if fewer than `minimum_peer_quotes` eligible peers exist, it
    returns insufficient_comparison_data instead of flagging or clearing.
    Eligible peers must have a stated total and pass a completeness floor,
    so an unresolved/near-empty quote can't drag the benchmark down."""
    eligible_peers = [
        q
        for q in peer_quotes
        if q.quote_id != candidate.quote_id
        and q.quoted_total is not None
        and (q.completeness_score or 0.0) >= completeness_floor
    ]
    if len(eligible_peers) < minimum_peer_quotes or candidate.quoted_total is None:
        return {"id": "below_market_30pct", "status": INSUFFICIENT_DATA, "peer_benchmark": None}

    peer_benchmark = statistics.median(q.quoted_total for q in eligible_peers)
    flagged = candidate.quoted_total < threshold_ratio * peer_benchmark
    return {
        "id": "below_market_30pct",
        "status": "flagged" if flagged else "clear",
        "peer_benchmark": peer_benchmark,
        "candidate_total": candidate.quoted_total,
    }


def non_binding_flag(candidate: Quote) -> dict[str, Any]:
    if candidate.estimate_type.value == "non_binding":
        return {"id": "non_binding_estimate", "status": "flagged"}
    return {"id": "non_binding_estimate", "status": "clear"}


def evaluate_red_flags(
    candidate: Quote,
    peer_quotes: list[Quote],
    vertical_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Runs the rules from config/verticals/<id>/vertical.json's
    below_market_rule -- vertical-specific thresholds are data, not code."""
    rule = vertical_config.get("below_market_rule", {})
    flags = [
        below_market_flag(
            candidate,
            peer_quotes,
            threshold_ratio=rule.get("threshold_ratio", 0.70),
            minimum_peer_quotes=rule.get("minimum_peer_quotes", 2),
        ),
        non_binding_flag(candidate),
    ]
    return [f for f in flags if f["status"] == "flagged"]
