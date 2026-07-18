from app.schemas.quote import EstimateType, Quote
from app.services.ranking import price_order, recommend, recommended_order

VERTICAL_CONFIG = {
    "below_market_rule": {
        "comparison": "other_complete_quotes_median",
        "threshold_ratio": 0.70,
        "minimum_peer_quotes": 2,
    }
}


def make_quote(quote_id, total, completeness=0.8, estimate_type=EstimateType.NON_BINDING):
    return Quote(
        quote_id=quote_id,
        call_id=f"call_{quote_id}",
        business_id=f"biz_{quote_id}",
        job_spec_sha256="hash",
        quoted_total=total,
        completeness_score=completeness,
        estimate_type=estimate_type,
    )


def test_price_order_is_pure_price():
    quotes = [make_quote("a", 3000), make_quote("b", 1000), make_quote("c", 2000)]
    ordered = price_order(quotes)
    assert [q.quote_id for q in ordered] == ["b", "c", "a"]


def test_cheapest_red_flagged_quote_is_not_recommended():
    lowball = make_quote("lowball", 500)
    mid = make_quote("mid", 2000)
    high = make_quote("high", 2200)
    quotes = [lowball, mid, high]

    ranked = recommended_order(quotes, VERTICAL_CONFIG)
    assert ranked[0]["quote"].quote_id != "lowball"

    top_pick = recommend(quotes, VERTICAL_CONFIG)
    assert top_pick["quote"].quote_id != "lowball"


def test_recommend_prefers_more_complete_quote_when_prices_tie():
    less_complete = make_quote("less", 2000, completeness=0.4)
    more_complete = make_quote("more", 2000, completeness=0.9)
    peer = make_quote("peer", 2100, completeness=0.9)
    top_pick = recommend([less_complete, more_complete, peer], VERTICAL_CONFIG)
    assert top_pick["quote"].quote_id == "more"
