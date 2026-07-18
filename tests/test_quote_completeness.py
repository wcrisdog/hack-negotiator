from app.schemas.quote import FeeLine, FeeStatus, Quote


def make_quote(fee_lines):
    return Quote(quote_id="q1", call_id="c1", business_id="b1", job_spec_sha256="hash", fee_lines=fee_lines)


def test_missing_fee_is_not_zero():
    quote = make_quote([FeeLine(category="base_labor_or_linehaul", status=FeeStatus.QUOTED, amount=1000)])
    assert quote.compute_known_fee_sum() == 1000
    completeness = quote.compute_completeness(["base_labor_or_linehaul", "fuel_surcharge"])
    assert completeness == 0.5  # fuel_surcharge unresolved, never assumed $0


def test_not_applicable_counts_as_resolved():
    quote = make_quote(
        [
            FeeLine(category="base_labor_or_linehaul", status=FeeStatus.QUOTED, amount=1000),
            FeeLine(category="elevator_fee", status=FeeStatus.NOT_APPLICABLE),
        ]
    )
    completeness = quote.compute_completeness(["base_labor_or_linehaul", "elevator_fee"])
    assert completeness == 1.0


def test_unknown_and_refused_do_not_contribute_amount():
    quote = make_quote(
        [
            FeeLine(category="base_labor_or_linehaul", status=FeeStatus.QUOTED, amount=1000),
            FeeLine(category="fuel_surcharge", status=FeeStatus.UNKNOWN),
            FeeLine(category="stair_fee", status=FeeStatus.REFUSED),
        ]
    )
    assert quote.compute_known_fee_sum() == 1000


def test_unknown_and_refused_do_not_count_as_complete():
    quote = make_quote(
        [
            FeeLine(category="fuel_surcharge", status=FeeStatus.UNKNOWN),
            FeeLine(category="stair_fee", status=FeeStatus.REFUSED),
        ]
    )
    assert quote.compute_completeness(["fuel_surcharge", "stair_fee"]) == 0.0
