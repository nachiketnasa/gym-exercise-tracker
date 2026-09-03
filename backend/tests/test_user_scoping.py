"""Single-user scoping stub (issue #14).

The app is single-user for now: one seeded local user, and every workout
session and goal carries a non-null ``user_id`` pointing at it. These tests
check that rows created through the existing API get stamped with the seeded
user's id, that the seed is idempotent, and that the ``users`` table / model
look as expected. The rest of the suite (``test_*_api.py``) covers the
"contract unchanged" side: no request or response body gained a ``user_id``.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select

from app.db import get_session
from app.deps import current_user
from app.main import app
from app.models import Goal, User, WorkoutSession
from app.users import SEED_USER, SEED_USER_ID, ensure_seed_user


@pytest.fixture
def client(db_session):
    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def seed_user(db_session):
    return ensure_seed_user(db_session)


# --- schema / model ------------------------------------------------------


def test_users_table_has_the_expected_columns(db_session):
    columns = {c["name"] for c in inspect(db_session.bind).get_columns("users")}
    assert columns == {"id", "email", "name", "created_at", "updated_at"}


def test_user_owned_tables_have_a_non_null_user_id_fk(db_session):
    insp = inspect(db_session.bind)
    for table in ("workout_sessions", "goals"):
        cols = {c["name"]: c for c in insp.get_columns(table)}
        assert "user_id" in cols, f"{table} is missing user_id"
        assert cols["user_id"]["nullable"] is False
        fk_targets = {
            fk["referred_table"] for fk in insp.get_foreign_keys(table)
        }
        assert "users" in fk_targets, f"{table}.user_id has no FK to users"


def test_shared_tables_are_not_user_scoped(db_session):
    insp = inspect(db_session.bind)
    for table in ("exercises", "exercise_entries"):
        cols = {c["name"] for c in insp.get_columns(table)}
        assert "user_id" not in cols, f"{table} should not be user-scoped"


# --- seed idempotency ---------------------------------------------------


def test_seed_user_has_a_stable_well_known_id(db_session):
    user = ensure_seed_user(db_session)
    assert user.id == SEED_USER_ID
    assert user.email == SEED_USER["email"]


def test_seeding_the_user_twice_leaves_exactly_one_row(db_session):
    ensure_seed_user(db_session)
    ensure_seed_user(db_session)

    count = db_session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.email == SEED_USER["email"])
    )
    assert count == 1


def test_current_user_dependency_returns_the_seeded_user(db_session):
    assert current_user(db_session).id == SEED_USER_ID


# --- rows created through the API get the owner id ---------------------


def test_creating_a_session_stamps_the_seeded_user_id(client, db_session, seed_user):
    resp = client.post("/sessions", json={"date": "2026-09-01", "notes": "x"})
    assert resp.status_code == 201
    assert "user_id" not in resp.json()  # response contract unchanged

    row = db_session.scalar(
        select(WorkoutSession).where(WorkoutSession.id == resp.json()["id"])
    )
    assert row.user_id == seed_user.id == SEED_USER_ID


def test_creating_a_goal_stamps_the_seeded_user_id(client, db_session, seed_user):
    from app.models import Exercise

    exercise = Exercise(name="Scoped Press", category="strength", is_preset=False)
    db_session.add(exercise)
    db_session.commit()
    db_session.refresh(exercise)

    resp = client.post(
        f"/exercises/{exercise.id}/goals",
        json={"metric": "weight", "target_value": 100},
    )
    assert resp.status_code == 201
    assert "user_id" not in resp.json()  # response contract unchanged

    row = db_session.scalar(select(Goal).where(Goal.id == resp.json()["id"]))
    assert row.user_id == seed_user.id == SEED_USER_ID


def test_session_list_and_detail_only_return_the_current_users_rows(
    client, db_session, seed_user
):
    mine = client.post("/sessions", json={"date": "2026-09-01"}).json()["id"]

    # A session owned by a different user must be invisible.
    other = User(email="other@example.com", name="Other")
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)
    hidden = WorkoutSession(date=date(2026, 9, 2))
    hidden.user_id = other.id
    db_session.add(hidden)
    db_session.commit()
    db_session.refresh(hidden)

    listed = {item["id"] for item in client.get("/sessions").json()["items"]}
    assert mine in listed
    assert hidden.id not in listed

    assert client.get(f"/sessions/{mine}").status_code == 200
    assert client.get(f"/sessions/{hidden.id}").status_code == 404


def test_goal_list_and_detail_only_return_the_current_users_rows(
    client, db_session, seed_user
):
    from app.models import Exercise

    exercise = Exercise(name="Shared Squat", category="strength", is_preset=False)
    db_session.add(exercise)
    db_session.commit()
    db_session.refresh(exercise)

    mine = client.post(
        f"/exercises/{exercise.id}/goals",
        json={"metric": "weight", "target_value": 100},
    ).json()["id"]

    other = User(email="other2@example.com", name="Other")
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)
    hidden = Goal(exercise_id=exercise.id, metric="weight", target_value=200)
    hidden.user_id = other.id
    db_session.add(hidden)
    db_session.commit()
    db_session.refresh(hidden)

    listed = {
        g["id"] for g in client.get(f"/exercises/{exercise.id}/goals").json()
    }
    assert mine in listed
    assert hidden.id not in listed

    assert client.get(f"/goals/{mine}").status_code == 200
    assert client.get(f"/goals/{hidden.id}").status_code == 404
