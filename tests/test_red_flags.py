from app.schemas.quote import Quote
from app.services.red_flags import INSUFFICIENT_DATA, below_market_flag


def make_quote(quote_id, total, completeness=0.8):
    return Quote(
        quote_id=quote_id,
        call_id=f"call_{quote_id}",
        business_id=f"biz_{quote_id}",
        job_spec_sha256="hash",
        quoted_total=total,
        completeness_score=completeness,
    )


def test_insufficient_peers_does_not_fabricate_benchmark():
    candidate = make_quote("a", 1000)
    result = below_market_flag(candidate, peer_quotes=[])
    assert result["status"] == INSUFFICIENT_DATA
    assert result["peer_benchmark"] is None


def test_flags_when_30pct_below_peer_median():
    candidate = make_quote("a", 1000)
    peers = [make_quote("b", 2000), make_quote("c", 2200)]
    result = below_market_flag(candidate, peer_quotes=peers)
    assert result["status"] == "flagged"
    assert result["peer_benchmark"] == 2100


def test_clear_when_within_range():
    candidate = make_quote("a", 2000)
    peers = [make_quote("b", 2000), make_quote("c", 2200)]
    result = below_market_flag(candidate, peer_quotes=peers)
    assert result["status"] == "clear"


def test_low_completeness_peers_are_excluded():
    candidate = make_quote("a", 1000)
    peers = [make_quote("b", 2000, completeness=0.1), make_quote("c", 2200, completeness=0.1)]
    result = below_market_flag(candidate, peer_quotes=peers)
    assert result["status"] == INSUFFICIENT_DATA
