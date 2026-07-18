from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import calls, jobs, reports
from app.db import init_db
from app.webhooks import agent_tools, post_call


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="The Negotiator", lifespan=lifespan)

# Allows a Lovable-hosted frontend (or any other origin) to call this API
# directly once it's reachable at a public URL. CORS_ALLOW_ORIGINS is a
# comma-separated list; defaults to "*" for hackathon-speed dev -- tighten
# this to the actual frontend origin before anything resembling production.
_allow_origins = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(calls.router)
app.include_router(reports.router)
app.include_router(agent_tools.router)
app.include_router(post_call.router)

# Serves web_widget/index.html at /widget/?agent_id=... -- the human-in-the-
# loop calling page a persona opens to "answer" (plan pivot: no Twilio
# number available; see app.services.calling.set_agent_dynamic_variables).
app.mount("/widget", StaticFiles(directory="web_widget", html=True), name="widget")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
