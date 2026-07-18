from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import calls, jobs, reports
from app.db import init_db
from app.webhooks import agent_tools, post_call


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="The Negotiator", lifespan=lifespan)

app.include_router(jobs.router)
app.include_router(calls.router)
app.include_router(reports.router)
app.include_router(agent_tools.router)
app.include_router(post_call.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
