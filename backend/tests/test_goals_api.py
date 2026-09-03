"""API tests for the Goals endpoints (issue #12).

Standard pattern: the per-test ``db_session`` rollback fixture is wired into
FastAPI via ``app.dependency_overrides[get_session]``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.db import get_session
from app.main import app
from app.models import Exercise


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


def _make_exercise(session, name, category):
    exercise = Exercise(name=name, category=category, is_preset=False)
    session.add(exercise)
    session.commit()
    session.refresh(exercise)
    return exercise


@pytest.fixture
def strength_exercise(db_session):
    return _make_exercise(db_session, "Bench Press", "strength")


@pytest.fixture
def cardio_exercise(db_session):
    return _make_exercise(db_session, "5k Run", "cardio")


# --- migration / schema --------------------------------------------------


def test_goals_table_has_the_expected_columns(db_session):
    columns = {c["name"] for c in inspect(db_session.bind).get_columns("goals")}
    assert columns == {
        "id",
        "exercise_id",
        "metric",
        "target_value",
        "unit",
        "description",
        "created_at",
        "updated_at",
    }


# --- POST /exercises/{id}/goals ---------------------------------------


def test_create_goal_returns_201_with_id_and_fields(client, strength_exercise):
    resp = client.post(
        f"/exercises/{strength_exercise.id}/goals",
        json={
            "metric": "weight",
            "target_value": 200,
            "unit": "lb",
            "description": "bench 200lb x5",
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert isinstance(body["id"], int)
    assert body["exercise_id"] == strength_exercise.id
    assert body["metric"] == "weight"
    assert body["target_value"] == 200.0
    assert body["unit"] == "lb"
    assert body["description"] == "bench 200lb x5"
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_create_goal_unit_and_description_are_optional(client, cardio_exercise):
    resp = client.post(
        f"/exercises/{cardio_exercise.id}/goals",
        json={"metric": "duration", "target_value": 1500},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["unit"] is None
    assert body["description"] is None


def test_create_goal_on_unknown_exercise_returns_404(client):
    resp = client.post(
        "/exercises/999999/goals", json={"metric": "weight", "target_value": 100}
    )
    assert resp.status_code == 404


def test_metric_outside_vocabulary_returns_422(client, strength_exercise):
    resp = client.post(
        f"/exercises/{strength_exercise.id}/goals",
        json={"metric": "vertical_leap", "target_value": 100},
    )
    assert resp.status_code == 422


def test_metric_not_valid_for_category_returns_422(client, strength_exercise):
    resp = client.post(
        f"/exercises/{strength_exercise.id}/goals",
        json={"metric": "pace", "target_value": 300},
    )
    assert resp.status_code == 422


@pytest.mark.parametrize("bad", [0, -1, -25.5, "not-a-number"])
def test_non_positive_or_non_numeric_target_returns_422(
    client, strength_exercise, bad
):
    resp = client.post(
        f"/exercises/{strength_exercise.id}/goals",
        json={"metric": "reps", "target_value": bad},
    )
    assert resp.status_code == 422


@pytest.mark.parametrize("metric", ["weight", "reps", "estimated_1rm"])
def test_strength_metric_vocabulary_is_accepted(
    client, strength_exercise, metric
):
    resp = client.post(
        f"/exercises/{strength_exercise.id}/goals",
        json={"metric": metric, "target_value": 100},
    )
    assert resp.status_code == 201


@pytest.mark.parametrize("metric", ["pace", "distance", "duration"])
def test_cardio_metric_vocabulary_is_accepted(client, cardio_exercise, metric):
    resp = client.post(
        f"/exercises/{cardio_exercise.id}/goals",
        json={"metric": metric, "target_value": 100},
    )
    assert resp.status_code == 201


def test_multiple_goals_including_same_metric_are_allowed(
    client, strength_exercise
):
    for target in (150, 175, 200):
        resp = client.post(
            f"/exercises/{strength_exercise.id}/goals",
            json={"metric": "weight", "target_value": target},
        )
        assert resp.status_code == 201

    listed = client.get(f"/exercises/{strength_exercise.id}/goals").json()
    assert len(listed) == 3
    assert {g["metric"] for g in listed} == {"weight"}


# --- GET /exercises/{id}/goals ---------------------------------------


def test_list_goals_returns_all_for_exercise_newest_first(
    client, strength_exercise
):
    first = client.post(
        f"/exercises/{strength_exercise.id}/goals",
        json={"metric": "weight", "target_value": 100},
    ).json()
    second = client.post(
        f"/exercises/{strength_exercise.id}/goals",
        json={"metric": "reps", "target_value": 8},
    ).json()

    listed = client.get(f"/exercises/{strength_exercise.id}/goals").json()

    assert [g["id"] for g in listed] == [second["id"], first["id"]]


def test_list_goals_for_exercise_with_none_returns_empty_list(
    client, strength_exercise
):
    resp = client.get(f"/exercises/{strength_exercise.id}/goals")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_goals_only_returns_that_exercises_goals(
    client, strength_exercise, cardio_exercise
):
    client.post(
        f"/exercises/{strength_exercise.id}/goals",
        json={"metric": "weight", "target_value": 100},
    )
    client.post(
        f"/exercises/{cardio_exercise.id}/goals",
        json={"metric": "pace", "target_value": 300},
    )

    listed = client.get(f"/exercises/{cardio_exercise.id}/goals").json()
    assert len(listed) == 1
    assert listed[0]["metric"] == "pace"


# --- GET /goals/{id} ------------------------------------------------


def test_get_goal_returns_it(client, strength_exercise):
    created = client.post(
        f"/exercises/{strength_exercise.id}/goals",
        json={"metric": "weight", "target_value": 120},
    ).json()

    resp = client.get(f"/goals/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_unknown_goal_returns_404(client):
    assert client.get("/goals/999999").status_code == 404


# --- PATCH /goals/{id} --------------------------------------------


def test_patch_updates_fields_and_refreshes_updated_at(client, strength_exercise):
    created = client.post(
        f"/exercises/{strength_exercise.id}/goals",
        json={"metric": "weight", "target_value": 100, "unit": "kg"},
    ).json()

    resp = client.patch(
        f"/goals/{created['id']}",
        json={"target_value": 140, "unit": "lb", "description": "new plan"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["target_value"] == 140.0
    assert body["unit"] == "lb"
    assert body["description"] == "new plan"
    assert body["metric"] == "weight"  # unchanged
    assert body["updated_at"] > created["updated_at"]


def test_patch_applies_only_supplied_fields(client, strength_exercise):
    created = client.post(
        f"/exercises/{strength_exercise.id}/goals",
        json={"metric": "weight", "target_value": 100, "unit": "kg"},
    ).json()

    body = client.patch(
        f"/goals/{created['id']}", json={"description": "just a note"}
    ).json()

    assert body["target_value"] == 100.0
    assert body["unit"] == "kg"
    assert body["description"] == "just a note"


def test_patch_unknown_goal_returns_404(client):
    assert client.patch("/goals/999999", json={"target_value": 10}).status_code == 404


def test_patch_non_positive_target_returns_422(client, strength_exercise):
    created = client.post(
        f"/exercises/{strength_exercise.id}/goals",
        json={"metric": "weight", "target_value": 100},
    ).json()
    resp = client.patch(f"/goals/{created['id']}", json={"target_value": -1})
    assert resp.status_code == 422


# --- DELETE /goals/{id} -------------------------------------------


def test_delete_goal_returns_204_and_then_404(client, strength_exercise):
    created = client.post(
        f"/exercises/{strength_exercise.id}/goals",
        json={"metric": "weight", "target_value": 100},
    ).json()

    resp = client.delete(f"/goals/{created['id']}")
    assert resp.status_code == 204
    assert resp.content == b""

    assert client.get(f"/goals/{created['id']}").status_code == 404


def test_delete_unknown_goal_returns_404(client):
    assert client.delete("/goals/999999").status_code == 404
