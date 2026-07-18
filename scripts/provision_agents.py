from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from agents import caller, closer, estimator  # noqa: E402


def main() -> dict:
    """One-time setup (plan §11 Phase 0): creates the three ElevenLabs
    agents and prints the IDs to save into .env. Requires ELEVENLABS_API_KEY
    with the convai_write permission scope -- as of this build the key in
    .env is missing that scope (verified: agent configs validate fine
    against elevenlabs==2.58.0's ConversationalConfig, but agents.create()
    returns 401 missing_permissions). Generate a new key with Conversational
    AI write access before running this."""
    created = {}
    for name, mod, env_var in [
        ("Estimator", estimator, "ELEVENLABS_ESTIMATOR_AGENT_ID"),
        ("Caller", caller, "ELEVENLABS_CALLER_AGENT_ID"),
        ("Closer", closer, "ELEVENLABS_CLOSER_AGENT_ID"),
    ]:
        agent_id = mod.create_agent()
        created[env_var] = agent_id
        print(f"{name}: {agent_id}  ->  set {env_var}={agent_id} in .env")
    return created


if __name__ == "__main__":
    main()
