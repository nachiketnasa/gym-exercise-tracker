"""Tests for the database layer: connection, isolation, and migrations."""

from __future__ import annotations

import os
import subprocess
import sys

from sqlalchemy import text

from tests.conftest import BACKEND_DIR, _alembic_config


def test_select_one_through_db_module(db_session):
    assert db_session.execute(text("SELECT 1")).scalar() == 1


def test_session_is_bound_to_the_test_database(db_session):
    name = db_session.execute(text("SELECT current_database()")).scalar()
    assert name.endswith("_test")
    assert name != "gym_tracker"


def test_inner_commit_is_held_on_a_savepoint(db_session):
    db_session.execute(text("CREATE TEMP TABLE _probe (id int) ON COMMIT DROP"))
    db_session.execute(text("INSERT INTO _probe VALUES (1)"))
    db_session.commit()  # becomes a SAVEPOINT release, not a real COMMIT
    # The table still exists: the outer transaction was never actually committed.
    assert db_session.execute(text("SELECT count(*) FROM _probe")).scalar() == 1


def test_migrations_are_reversible():
    from alembic import command

    cfg = _alembic_config()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")  # leave the schema at head for other tests


def test_db_module_requires_database_url():
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("DATABASE_URL", "TEST_DATABASE_URL")
    }
    result = subprocess.run(
        [sys.executable, "-c", "import app.db"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(BACKEND_DIR),
    )
    assert result.returncode != 0
    assert "DATABASE_URL" in result.stderr
    assert "KeyError" not in result.stderr
