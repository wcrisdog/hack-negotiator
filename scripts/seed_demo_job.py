from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Business, Job, get_session, init_db  # noqa: E402
from app.services.canonicalize import confirm_job_spec  # noqa: E402

DEMO_JOB_ID = "job_demo_rockhill_charlotte"

# The brief's own worked example (plan §1 Context, §3.2): real distance and
# cities, a made-up but internally-consistent inventory for rehearsal.
DEMO_SPEC = {
    "origin": {
        "city": "Rock Hill",
        "state": "SC",
        "unit_type": "apartment",
        "bedrooms": 2,
        "floor": 2,
        "elevator": False,
        "stairs_count": 14,
        "long_carry_ft": 40,
    },
    "destination": {"city": "Charlotte", "state": "NC", "unit_type": "apartment", "floor": 1, "elevator": True},
    "distance_miles": 45,
    "move_date": {"preferred": "2026-08-08", "flexible_window_days": 3},
    "inventory": {
        "rooms": [
            {
                "name": "living_room",
                "items": [{"item": "sofa", "quantity": 1}, {"item": "tv_55in", "quantity": 1, "fragile": True}],
            }
        ],
        "boxes_estimate": 25,
        "special_items": [],
    },
    "services": {
        "packing": "requested",
        "disassembly_reassembly": "requested",
        "storage": "not_requested",
        "valuation_preference": "full_value_protection",
    },
}

DEMO_PERSONAS = [
    ("persona_tough", "Tough Movers Co."),
    ("persona_lowball", "Budget Movers"),
    ("persona_hardsell", "Premier Relocation"),
]


def main() -> dict:
    """Plan §11 Phase 5 rehearsal aid: seeds the Rock Hill -> Charlotte demo
    job (already confirmed, so scripts/run_demo.py can dispatch immediately)
    and the three persona businesses. Idempotent -- safe to re-run."""
    init_db()
    session = get_session()
    try:
        canonical_json, job_spec_sha256 = confirm_job_spec(DEMO_SPEC)
        job = Job(
            job_id=DEMO_JOB_ID,
            vertical_id="residential_moving",
            status="confirmed",
            spec=DEMO_SPEC,
            canonical_json=canonical_json,
            job_spec_sha256=job_spec_sha256,
            confirmed_at=datetime.now(timezone.utc),
        )
        session.merge(job)

        for business_id, name in DEMO_PERSONAS:
            session.merge(Business(business_id=business_id, name=name, source_type="demo_persona"))

        session.commit()
        print(f"Seeded {DEMO_JOB_ID}, job_spec_sha256={job_spec_sha256}")
        for business_id, name in DEMO_PERSONAS:
            print(f"  persona business: {business_id} ({name})")
        return {"job_id": DEMO_JOB_ID, "job_spec_sha256": job_spec_sha256}
    finally:
        session.close()


if __name__ == "__main__":
    main()
