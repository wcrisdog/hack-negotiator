# The Negotiator

Voice-agent MVP for the ElevenLabs × Hack-Nation "The Negotiator" challenge:
an intake agent builds one structured moving-job specification, a Caller
agent phones the market and gathers itemized quotes, and a Closer agent
negotiates using real leverage before a ranked, evidence-backed report is
produced. Full design rationale lives in the plan this repo was built from
(`Useful Info/Negotiator.pdf` is the challenge brief; `submission.md` lists
final deliverables).

## Status

Backend, data contracts, red-flag/ranking logic, vertical config, and the
three ElevenLabs agent configs are implemented and tested (`pytest`, 21
passing, including a full intake→calls→negotiation→report loop test). Real
agent creation and real outbound calls are **not yet live** -- see
[Known blockers](#known-blockers).

## Setup

```bash
python3 -m venv .venv          # needs Python 3.10+ (pydantic v2 requires it)
.venv/bin/pip install -r requirements.txt
cp .env.example .env           # fill in the keys you have
```

## Running the backend

```bash
.venv/bin/uvicorn app.main:app --reload
curl http://localhost:8000/health
```

## Running tests

```bash
.venv/bin/python -m pytest -q
```

## Seeding a demo job and inspecting it

```bash
.venv/bin/python scripts/seed_demo_job.py         # confirmed Rock Hill -> Charlotte job + 3 persona businesses
.venv/bin/python scripts/export_public_dataset.py # writes data/dataset_export/dataset.json (redacted)
```

## Provisioning the real ElevenLabs agents

```bash
.venv/bin/python scripts/provision_agents.py
# copy the printed agent IDs into .env as ELEVENLABS_{ESTIMATOR,CALLER,CLOSER}_AGENT_ID
```

## Running the demo calls (round 1 + round 2)

**Primary path: ElevenLabs widget, human-in-the-loop (no phone number needed).**
The original plan called for real Twilio PSTN calls, but Twilio's trial-
account identity verification couldn't be completed, so the default demo
mechanism is now the browser widget -- a valid setup per the challenge
brief ("answer the calls yourself, playing different counterparts"). This
only needs a working `ELEVENLABS_API_KEY` with `convai_write` scope.

```bash
.venv/bin/uvicorn app.main:app --reload   # keep running in one terminal
.venv/bin/python scripts/seed_demo_job.py
.venv/bin/python -c "from scripts.run_demo import dispatch_round_one_widget; dispatch_round_one_widget()"
# open each printed http://localhost:8000/widget/?agent_id=... link, one at a
# time, and answer as that persona (see personas/*.md)
.venv/bin/python -c "from scripts.run_demo import dispatch_round_two_widget; dispatch_round_two_widget('persona_lowball')"
.venv/bin/python scripts/reconcile_calls.py
```

**Stretch path: real Twilio PSTN calls.** `app.services.calling.place_outbound_call`
and `scripts/run_demo.py`'s `dispatch_round_one`/`dispatch_round_two` still
implement this and remain available if a Twilio number becomes available
later. Requires `ELEVENLABS_AGENT_PHONE_NUMBER_ID` (a Twilio number
imported into the ElevenLabs dashboard) and `PERSONA_{TOUGH,LOWBALL,HARDSELL}_PHONE`
env vars set to real, consenting phone numbers -- never dial a number
without consent.

```bash
.venv/bin/python scripts/run_demo.py   # round 1: dispatches to all 3 personas
.venv/bin/python -c "from scripts.run_demo import dispatch_round_two; dispatch_round_two('persona_lowball')"
```

## Switching verticals (config, not code)

Copy `config/verticals/residential_moving/` to a new directory, edit
`vertical.json`, `quote_taxonomy.json`, `red_flags.json`,
`negotiation_levers.json`, and `job_spec.schema.json` for the new vertical,
and point `app.api.jobs.create_job`'s `vertical_id` at the new folder name.
No Python changes required -- `config/verticals/auto_body_stub/` is a
minimal example proving this.

## Repository layout

See the plan's §12 "Corrected Repository Structure" for the intended full
layout; the current tree matches it except for `frontend/` (Lovable
project, not yet started) and a couple of stretch-scope pieces noted below.

## Known blockers

- **ElevenLabs API key lacks `convai_write` permission -- this is the one
  hard blocker left for a live demo.** `agents/{estimator,caller,closer}.py`
  build configs that validate correctly against the real SDK
  (`elevenlabs==2.58.0`, verified against `/v1/convai/llm/list`), but
  `scripts/provision_agents.py` fails with a 401 until a key with
  Conversational AI write access is generated (ElevenLabs dashboard → API
  Keys → enable Conversational AI).
- **Twilio trial account can't complete identity verification** -- real PSTN
  calling is therefore parked as a stretch path (code still there, see
  above). The MVP calling mechanism is now the ElevenLabs browser widget,
  which needs no Twilio at all.
- **`OPENAI_API_KEY` not set** -- `app/services/document_intake.py` and the
  LLM path in `app/services/narrative.py` raise/fall back accordingly. The
  narrative falls back to a deterministic template automatically; document
  intake has no fallback and will need the key before it can run.
- **`TAVILY_API_KEY` not set** -- `app/services/discovery.py`'s
  `TavilyDiscoveryProvider` will raise until it's set. Not on the critical
  path to the negotiation loop (plan §4.4).
- **No persona humans recruited yet** -- three consenting people need to be
  lined up to open the widget links and role-play (plan §8, §11 Phase 5).
- **Lovable frontend built but decoupled from this backend** -- see the
  frontend's own README note / prior conversation; it currently reads/writes
  its own Supabase tables, not this FastAPI service.
- **Frontend doesn't have a voice-widget or job-spec-confirm UI wired to
  the real ElevenLabs agents/backend yet** -- Screens exist but call
  Supabase directly; connecting to this backend's `/jobs`, `/calls/dispatch`,
  `/jobs/{id}/report` endpoints (and this new `/widget/` page) is unstarted.
