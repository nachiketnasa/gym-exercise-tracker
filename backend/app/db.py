"""Database engine, session factory, and declarative base.

The connection URL comes entirely from the ``DATABASE_URL`` environment
variable. Nothing here hardcodes a host, database name, or credentials, and
there is no silent fallback to a default connection.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Shared declarative base that all ORM models import and subclass."""


def _resolve_database_url() -> str:
    """Return the SQLAlchemy URL from ``DATABASE_URL``.

    Raises a clear error (naming the variable) when it is unset, and
    normalises the scheme so SQLAlchemy uses the psycopg 3 driver.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Export it or put it in a .env file, e.g. "
            "DATABASE_URL=postgresql://gym:gym@localhost:5432/gym_tracker"
        )
    for scheme in ("postgresql://", "postgres://"):
        if url.startswith(scheme):
            return "postgresql+psycopg://" + url[len(scheme):]
    return url


DATABASE_URL = _resolve_database_url()

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_session() -> Iterator[Session]:
    """Yield a session and close it afterwards (usable as a FastAPI dependency)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
