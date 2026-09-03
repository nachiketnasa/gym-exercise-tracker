"""Shared test fixtures for the database layer.

Tests run against a dedicated database (``gym_tracker_test`` by default) so the
dev data in ``gym_tracker`` is never touched. The database name is taken from
``TEST_DATABASE_URL`` when set, otherwise it is derived from ``DATABASE_URL`` by
appending ``_test`` to its name. The test database is created and migrated to
``head`` automatically on the first run, so a fresh ``docker compose up -d db``
plus ``cp .env.example .env`` at the repo root is all that is needed.

The ``db_session`` fixture is deliberately generic so #5, #6, and #8 can reuse
it: each test gets a session wrapped in a transaction that is rolled back on
teardown, with inner ``commit()`` calls held on a SAVEPOINT.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


def _load_repo_dotenv() -> None:
    """Populate os.environ from the repo-root .env (without overriding real env vars)."""
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _normalise(url: str) -> str:
    for scheme in ("postgresql://", "postgres://"):
        if url.startswith(scheme):
            return "postgresql+psycopg://" + url[len(scheme) :]
    return url


_load_repo_dotenv()

_dev_url = os.environ.get("DATABASE_URL")
if not _dev_url:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy .env.example to .env at the repo root "
        "(cp .env.example .env) or export DATABASE_URL before running the tests."
    )


def _resolve_test_url() -> str:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return _normalise(explicit)
    dev = make_url(_normalise(_dev_url))
    return dev.set(database=f"{dev.database}_test").render_as_string(hide_password=False)


TEST_DATABASE_URL = _resolve_test_url()

# Point the whole db layer (and Alembic, which reads it via app.db) at the test
# database for the duration of the test session. DATABASE_URL stays the single
# source of the connection.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app import db  # noqa: E402  (import after DATABASE_URL is set)


def _ensure_test_database() -> None:
    target = make_url(TEST_DATABASE_URL)
    admin = create_engine(
        target.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    try:
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": target.database},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    finally:
        admin.dispose()


def _alembic_config():
    from alembic.config import Config

    return Config(str(BACKEND_DIR / "alembic.ini"))


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database():
    """Create the test database (if needed) and bring its schema to head."""
    from alembic import command

    _ensure_test_database()
    command.upgrade(_alembic_config(), "head")
    yield


@pytest.fixture
def db_session(migrated_test_database):
    """A session bound to a connection-level transaction that is rolled back.

    Inner ``session.commit()`` calls are converted to SAVEPOINT releases and a
    fresh SAVEPOINT is opened, so the outer transaction can always be rolled
    back on teardown, leaving the database untouched between tests.
    """
    connection = db.engine.connect()
    transaction = connection.begin()
    session = db.SessionLocal(
        bind=connection, join_transaction_mode="create_savepoint"
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
