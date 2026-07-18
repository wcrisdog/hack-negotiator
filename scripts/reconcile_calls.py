from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.calling import reconcile_missing_outcomes  # noqa: E402


def main() -> None:
    """Run on a schedule, or before generating a report (plan §7.2, §11
    Phase 3 'Add post-call reconciliation for missing outcomes'): backfills
    documented_decline/tool_failure for any call still unreconciled well
    after it should plausibly have ended."""
    reconciled = reconcile_missing_outcomes(stale_after_minutes=30)
    if reconciled:
        print(f"Reconciled {len(reconciled)} stale call(s): {reconciled}")
    else:
        print("No stale unreconciled calls.")


if __name__ == "__main__":
    main()
