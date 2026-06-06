"""Database session factory."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from mindbrew_v2.settings import get_settings

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        url = normalize_database_url(settings.database_url)
        kwargs: dict = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            if ":memory:" in url:
                kwargs["poolclass"] = StaticPool
        _engine = create_engine(url, **kwargs)
    return _engine


def normalize_database_url(url: str) -> str:
    """Normalize Postgres URLs for SQLAlchemy (psycopg v3 driver)."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


def psycopg_conn_string(url: str) -> str:
    """Strip SQLAlchemy driver suffix for raw psycopg / LangGraph PostgresSaver."""
    normalized = normalize_database_url(url)
    if normalized.startswith("postgresql+psycopg://"):
        return "postgresql://" + normalized[len("postgresql+psycopg://") :]
    if normalized.startswith("postgresql+"):
        return "postgresql://" + normalized.split("://", 1)[1]
    return normalized


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
