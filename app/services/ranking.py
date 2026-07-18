from __future__ import annotations

from typing import Any

from app.schemas.quote import Quote
from app.services.red_flags import evaluate_red_flags


def price_order(quotes: list[Quote]) -> list[Quote]:
    """Raw price ranking (plan §9.2, ranking #1). Never hides a quote -- a
    judge should be able to see every stated total, complete or not."""
    return sorted(
        quotes,
        key=lambda q: (q.quoted_total is None, q.quoted_total if q.quoted_total is not None else float("inf")),
    )


def recommended_order(quotes: list[Quote], vertical_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Risk-adjusted ranking (plan §9.2, ranking #2). A red-flagged or
    low-completeness quote is demoted and annotated -- never silently
    removed, and never auto-declared the winner just for being cheapest."""
    entries = []
    for q in quotes:
        peers = [p for p in quotes if p.quote_id != q.quote_id]
        flags = evaluate_red_flags(q, peers, vertical_config)
        # Only the below-market rule gates recommendation (plan §9.2: "a
        # suspiciously low quote ... is not automatically declared the
        # winner"). Other flags (e.g. non_binding_estimate) still show up in
        # red_flags for transparency and nudge the tiebreaker below, but a
        # merely non-binding quote is not "requiring clarification".
        blocking_flags = [f for f in flags if f["id"] == "below_market_30pct"]
        entries.append(
            {
                "quote": q,
                "red_flags": flags,
                "requires_clarification": bool(blocking_flags),
                "completeness_score": q.completeness_score or 0.0,
            }
        )

    def sort_key(entry: dict[str, Any]) -> tuple:
        q = entry["quote"]
        return (
            entry["requires_clarification"],
            q.estimate_type.value != "binding",
            -(entry["completeness_score"]),
            q.quoted_total if q.quoted_total is not None else float("inf"),
        )

    return sorted(entries, key=sort_key)


def recommend(quotes: list[Quote], vertical_config: dict[str, Any]) -> dict[str, Any] | None:
    """Top pick among quotes that don't require clarification. Returns None
    if every quote is flagged -- that's a real outcome to surface, not an
    error to swallow."""
    ranked = recommended_order(quotes, vertical_config)
    clean = [e for e in ranked if not e["requires_clarification"]]
    return clean[0] if clean else None
