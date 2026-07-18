from datetime import datetime, timedelta, timezone

from app.db import Business, Call, Job, get_session
from app.services.calling import reconcile_missing_outcomes


def test_stale_unreconciled_call_gets_documented_decline():
    session = get_session()
    session.merge(Business(business_id="persona_stale_test", name="Stale Test", source_type="demo_persona"))
    session.merge(
        Job(job_id="job_recon_test", vertical_id="residential_moving", status="confirmed", job_spec_sha256="h")
    )
    session.merge(
        Call(
            call_id="call_stale_test",
            job_id="job_recon_test",
            business_id="persona_stale_test",
            agent_role="caller",
            job_spec_sha256_used="h",
            reconciled=False,
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
    )
    session.commit()
    session.close()

    reconciled_ids = reconcile_missing_outcomes(stale_after_minutes=30)
    assert "call_stale_test" in reconciled_ids

    session = get_session()
    refreshed = session.get(Call, "call_stale_test")
    assert refreshed.outcome == "documented_decline"
    assert refreshed.outcome_reason == "tool_failure"
    assert refreshed.reconciled is True
    session.close()


def test_fresh_unreconciled_call_is_left_alone():
    session = get_session()
    session.merge(Business(business_id="persona_fresh_test", name="Fresh Test", source_type="demo_persona"))
    session.merge(
        Job(job_id="job_recon_fresh", vertical_id="residential_moving", status="confirmed", job_spec_sha256="h")
    )
    session.merge(
        Call(
            call_id="call_fresh_test",
            job_id="job_recon_fresh",
            business_id="persona_fresh_test",
            agent_role="caller",
            job_spec_sha256_used="h",
            reconciled=False,
            created_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    session.close()

    reconciled_ids = reconcile_missing_outcomes(stale_after_minutes=30)
    assert "call_fresh_test" not in reconciled_ids
