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

## Running the real-call demo (round 1 + round 2)

Requires `ELEVENLABS_AGENT_PHONE_NUMBER_ID` (a Twilio number imported into
the ElevenLabs dashboard) and `PERSONA_{TOUGH,LOWBALL,HARDSELL}_PHONE` env
vars set to real, consenting phone numbers -- never dial a number without
consent.

```bash
.venv/bin/python scripts/run_demo.py   # round 1: dispatches to all 3 personas
.venv/bin/python -c "from scripts.run_demo import dispatch_round_two; dispatch_round_two('persona_lowball')"
.venv/bin/python scripts/reconcile_calls.py
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

- **ElevenLabs API key lacks `convai_write` permission.** `agents/{estimator,caller,closer}.py`
  build configs that validate correctly against the real SDK
  (`elevenlabs==2.58.0`, verified against `/v1/convai/llm/list`), but
  `scripts/provision_agents.py` fails with a 401 until a key with
  Conversational AI write access is generated (ElevenLabs dashboard → API
  Keys → enable Conversational AI).
- **`OPENAI_API_KEY` not set** -- `app/services/document_intake.py` and the
  LLM path in `app/services/narrative.py` raise/fall back accordingly. The
  narrative falls back to a deterministic template automatically; document
  intake has no fallback and will need the key before it can run.
- **`TAVILY_API_KEY` not set** -- `app/services/discovery.py`'s
  `TavilyDiscoveryProvider` will raise until it's set. Not on the critical
  path to the negotiation loop (plan §4.4).
- **No Twilio phone number imported into ElevenLabs yet** -- needed for
  `ELEVENLABS_AGENT_PHONE_NUMBER_ID` before any real outbound call can be
  placed. `TWILIO_ACCOUNT_SID`/`TWILIO_CLIENT_SECRET` are set; the number
  itself still needs importing via the ElevenLabs dashboard's Phone Numbers
  tab.
- **No persona phone numbers recruited yet** -- `PERSONA_*_PHONE` env vars
  in `scripts/run_demo.py` are empty; three consenting people need to be
  lined up before a real rehearsal (plan §8, §11 Phase 5).
- **Lovable frontend not started** -- backend API is ready to be called
  from it (`/jobs`, `/calls/dispatch`, `/jobs/{id}/report`).
