from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class CallOutcome(str, Enum):
    ITEMIZED_QUOTE = "itemized_quote"
    CALLBACK_COMMITTED = "callback_committed"
    DOCUMENTED_DECLINE = "documented_decline"


class OutcomeReason(str, Enum):
    NO_ANSWER = "no_answer"
    HUNG_UP = "hung_up"
    REFUSED_TO_QUOTE = "refused_to_quote"
    INVALID_NUMBER = "invalid_number"
    TOOL_FAILURE = "tool_failure"


class CallOutcomeRecord(BaseModel):
    """Terminal record for a call (plan §5.4). Reconciliation
    (app/services/calling.py::reconcile_missing_outcomes and the post-call
    webhook) writes one of these for every call, including calls the agent
    never got to close itself -- hang-up, no-answer, tool failure -- so no
    call stays ambiguous."""

    call_id: str
    conversation_id: str | None = None
    outcome: CallOutcome
    reason: OutcomeReason | None = None
    reconciled: bool = False
