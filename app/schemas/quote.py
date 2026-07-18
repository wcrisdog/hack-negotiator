from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.call_outcome import CallOutcome


class FeeStatus(str, Enum):
    QUOTED = "quoted"
    INCLUDED = "included"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"
    REFUSED = "refused"


class EstimateType(str, Enum):
    BINDING = "binding"
    NON_BINDING = "non_binding"
    UNKNOWN = "unknown"


class Evidence(BaseModel):
    conversation_id: str
    start_ms: int | None = None
    end_ms: int | None = None
    transcript_excerpt: str | None = None


class FeeLine(BaseModel):
    category: str
    status: FeeStatus
    amount: float | None = None
    unit: str = "total"
    evidence: Evidence | None = None


class Deposit(BaseModel):
    amount: float | None = None
    payment_method: str | None = None


class Quote(BaseModel):
    """Plan §5.3. `unknown`/`refused` fee lines are never converted to $0 --
    completeness_score exists precisely so a comparison can show "how much
    of this quote do we actually know" instead of silently assuming zero."""

    quote_id: str
    call_id: str
    business_id: str
    job_spec_sha256: str
    currency: str = "USD"
    estimate_type: EstimateType = EstimateType.UNKNOWN
    fee_lines: list[FeeLine] = Field(default_factory=list)
    quoted_total: float | None = None
    known_fee_sum: float | None = None
    completeness_score: float | None = None
    assumptions: list[str] = Field(default_factory=list)
    valid_until: str | None = None
    deposit: Deposit | None = None
    outcome: CallOutcome | None = None
    is_revision: bool = False
    previous_amount: float | None = None

    def compute_known_fee_sum(self) -> float:
        return sum(fl.amount for fl in self.fee_lines if fl.amount is not None)

    def compute_completeness(self, expected_categories: list[str]) -> float:
        """Fraction of expected fee categories that are resolved -- quoted,
        included, or explicitly not_applicable. `unknown`/`refused` count as
        unresolved, not as zero and not as complete."""
        if not expected_categories:
            return 1.0
        resolved = {
            fl.category
            for fl in self.fee_lines
            if fl.status in (FeeStatus.QUOTED, FeeStatus.INCLUDED, FeeStatus.NOT_APPLICABLE)
        }
        return len(resolved & set(expected_categories)) / len(expected_categories)
