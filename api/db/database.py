"""Database session factory."""

from __future__ import annotations

import socket
from collections.abc import Generator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from mindbrew_v2.settings import get_settings

_engine = None
_SessionLocal = None


def _postgres_connect_args(url: str) -> dict:
    """Prefer IPv4 for managed Postgres (Render lacks reliable IPv6 to Supabase direct)."""
    normalized = url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )
    parsed = urlparse(normalized)
    hostname = parsed.hostname
    if not hostname or hostname in {"localhost", "127.0.0.1", "::1"}:
        return {}
    try:
        infos = socket.getaddrinfo(
            hostname, parsed.port or 5432, socket.AF_INET, socket.SOCK_STREAM
        )
    except OSError:
        return {}
    if not infos:
        return {}
    return {"hostaddr": infos[0][4][0]}


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
        elif url.startswith("postgresql"):
            connect_args = _postgres_connect_args(url)
            if connect_args:
                kwargs["connect_args"] = connect_args
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
        conn = "postgresql://" + normalized[len("postgresql+psycopg://") :]
    elif normalized.startswith("postgresql+"):
        conn = "postgresql://" + normalized.split("://", 1)[1]
    else:
        conn = normalized

    hostaddr = _postgres_connect_args(url).get("hostaddr")
    if not hostaddr:
        return conn

    parsed = urlparse(conn)
    query = parse_qs(parsed.query)
    query["hostaddr"] = [hostaddr]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


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
