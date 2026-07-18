from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Plan §4.1/§10: Postgres via Supabase (provisioned through Lovable) is the
# target. Falls back to a local SQLite file when DATABASE_URL is unset, so
# the backend and its tests run before Supabase is provisioned.
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./data/negotiator.db"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True)
    vertical_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft")
    spec_version = Column(Integer, nullable=False, default=1)
    spec = Column(JSON, nullable=False, default=dict)
    source_provenance = Column(JSON, nullable=False, default=dict)
    canonical_json = Column(String, nullable=True)
    job_spec_sha256 = Column(String, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class Business(Base):
    __tablename__ = "businesses"

    business_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    # demo_persona (private, consenting human role-player) | discovered
    # (public, via app.services.discovery) -- never merged silently (plan §4.4).
    source_type = Column(String, nullable=False, default="demo_persona")
    source_url = Column(String, nullable=True)
    retrieved_at = Column(DateTime, nullable=True)


class Call(Base):
    __tablename__ = "calls"

    call_id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.job_id"), nullable=False)
    business_id = Column(String, ForeignKey("businesses.business_id"), nullable=False)
    agent_role = Column(String, nullable=False)  # caller | closer
    conversation_id = Column(String, nullable=True)
    # Immutable proof of verbatim reuse (plan §2, §13): the confirmed job's
    # hash at dispatch time. Never recomputed after the call is created.
    job_spec_sha256_used = Column(String, nullable=False)
    outcome = Column(String, nullable=True)
    outcome_reason = Column(String, nullable=True)
    reconciled = Column(Boolean, default=False)
    transcript = Column(JSON, nullable=True)
    recording_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class CallEvent(Base):
    __tablename__ = "call_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(String, ForeignKey("calls.call_id"), nullable=False)
    idempotency_key = Column(String, nullable=False, unique=True)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=utcnow)


class QuoteRow(Base):
    __tablename__ = "quotes"

    quote_id = Column(String, primary_key=True)
    call_id = Column(String, ForeignKey("calls.call_id"), nullable=False)
    business_id = Column(String, ForeignKey("businesses.business_id"), nullable=False)
    job_spec_sha256 = Column(String, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    estimate_type = Column(String, nullable=False, default="unknown")
    quoted_total = Column(Float, nullable=True)
    known_fee_sum = Column(Float, nullable=True)
    completeness_score = Column(Float, nullable=True)
    is_revision = Column(Boolean, default=False)
    previous_amount = Column(Float, nullable=True)
    outcome = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class FeeLineRow(Base):
    __tablename__ = "fee_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quote_id = Column(String, ForeignKey("quotes.quote_id"), nullable=False)
    category = Column(String, nullable=False)
    status = Column(String, nullable=False)
    amount = Column(Float, nullable=True)
    unit = Column(String, nullable=False, default="total")
    conversation_id = Column(String, nullable=True)
    start_ms = Column(Integer, nullable=True)
    end_ms = Column(Integer, nullable=True)
    transcript_excerpt = Column(String, nullable=True)


class NegotiationDelta(Base):
    __tablename__ = "negotiation_deltas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(String, ForeignKey("calls.call_id"), nullable=False)
    candidate_business_id = Column(String, nullable=False)
    prior_quote_total = Column(Float, nullable=True)
    leverage_quote_total = Column(Float, nullable=True)
    leverage_quote_id = Column(String, nullable=True)
    revised_quote_total = Column(Float, nullable=True)
    changed_terms = Column(JSON, nullable=False, default=list)
    price_delta = Column(Float, nullable=True)


class RedFlagRow(Base):
    __tablename__ = "red_flags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quote_id = Column(String, ForeignKey("quotes.quote_id"), nullable=False)
    rule_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    peer_benchmark = Column(Float, nullable=True)


def init_db() -> None:
    if DATABASE_URL.startswith("sqlite"):
        os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()
