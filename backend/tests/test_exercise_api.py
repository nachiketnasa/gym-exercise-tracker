"""API tests for the Exercise endpoints (issue #7).

These use the per-test ``db_session`` rollback fixture from ``conftest.py`` via
the standard FastAPI dependency-override pattern, so every request runs inside a
transaction that is rolled back on teardown. Presets are loaded explicitly by a
fixture where a test needs them; nothing depends on a hand-seeded dev database.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.models import Exercise
from app.seed import PRESET_EXERCISES, seed


@pytest.fixture
def client(db_session):
    """A ``TestClient`` whose ``get_session`` dependency uses ``db_session``."""

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def presets(db_session):
    """Load the preset library into the test transaction."""
    seed(db_session)
    return PRESET_EXERCISES


def _make_exercise(session, name: str, category: str = "strength", is_preset=False):
    exercise = Exercise(name=name, category=category, is_preset=is_preset)
    session.add(exercise)
    session.commit()
    session.refresh(exercise)
    return exercise


# --- GET /exercises -----------------------------------------------------------


def test_list_returns_200_and_array_ordered_by_name_with_expected_fields(
    client, db_session
):
    _make_exercise(db_session, "Zercher Squat", "strength")
    _make_exercise(db_session, "Air Bike", "cardio", is_preset=True)
    _make_exercise(db_session, "Muscle-Up", "strength")

    response = client.get("/exercises")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert [item["name"] for item in body] == ["Air Bike", "Muscle-Up", "Zercher Squat"]
    assert set(body[0]) == {
        "id",
        "name",
        "category",
        "is_preset",
        "created_at",
        "updated_at",
    }
    assert body[0]["is_preset"] is True
    assert body[1]["is_preset"] is False


def test_list_includes_presets_and_custom(client, db_session, presets):
    _make_exercise(db_session, "Cable Fly", "strength")

    names = {item["name"] for item in client.get("/exercises").json()}

    assert "Cable Fly" in names
    assert "Bench Press" in names  # a preset


# --- GET /exercises/{id} -----------------------------------------------------


def test_get_by_id_returns_200_with_matching_exercise(client, db_session):
    created = _make_exercise(db_session, "Good Morning", "strength")

    response = client.get(f"/exercises/{created.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created.id
    assert body["name"] == "Good Morning"
    assert body["category"] == "strength"


def test_get_by_id_returns_404_with_json_body_for_unknown_id(client):
    response = client.get("/exercises/999999")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Exercise 999999 not found",
            "details": None,
        }
    }


# --- POST /exercises --------------------------------------------------------


def test_create_returns_201_with_is_preset_false_and_timestamps_and_appears_in_list(
    client,
):
    response = client.post(
        "/exercises", json={"name": "Cable Fly", "category": "strength"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Cable Fly"
    assert body["category"] == "strength"
    assert body["is_preset"] is False
    assert body["created_at"] is not None
    assert body["updated_at"] is not None
    assert isinstance(body["id"], int)

    listed = {item["name"] for item in client.get("/exercises").json()}
    assert "Cable Fly" in listed


def test_create_trims_whitespace_from_name(client, db_session):
    response = client.post(
        "/exercises", json={"name": "  Pendlay Row \t", "category": "strength"}
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Pendlay Row"

    stored = db_session.query(Exercise).filter(Exercise.name == "Pendlay Row").one()
    assert stored.name == "Pendlay Row"


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_create_blank_or_whitespace_name_returns_422(client, name):
    response = client.post(
        "/exercises", json={"name": name, "category": "strength"}
    )
    assert response.status_code == 422


def test_create_name_longer_than_100_chars_returns_422(client):
    response = client.post(
        "/exercises", json={"name": "x" * 101, "category": "strength"}
    )
    assert response.status_code == 422


def test_create_name_exactly_100_chars_is_allowed(client):
    response = client.post(
        "/exercises", json={"name": "y" * 100, "category": "strength"}
    )
    assert response.status_code == 201


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "No Category"},
        {"name": "Bad Category", "category": "mobility"},
        {"name": "Null Category", "category": None},
    ],
)
def test_create_missing_or_bad_category_returns_422(client, payload):
    response = client.post("/exercises", json=payload)
    assert response.status_code == 422


def test_create_duplicate_custom_name_case_insensitive_returns_409_json(
    client, db_session
):
    _make_exercise(db_session, "Cable Fly", "strength")

    response = client.post(
        "/exercises", json={"name": "cABLE fLY", "category": "cardio"}
    )

    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["error"]["code"] == "conflict"


def test_create_duplicate_preset_name_case_insensitive_returns_409_json(
    client, presets
):
    response = client.post(
        "/exercises", json={"name": "bench press", "category": "strength"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_create_ignores_client_supplied_id_is_preset_and_timestamps(
    client, db_session
):
    response = client.post(
        "/exercises",
        json={
            "name": "Sneaky Preset",
            "category": "strength",
            "id": 424242,
            "is_preset": True,
            "created_at": "2000-01-01T00:00:00Z",
            "updated_at": "2000-01-01T00:00:00Z",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] != 424242
    assert body["is_preset"] is False
    assert not body["created_at"].startswith("2000-01-01")
    assert not body["updated_at"].startswith("2000-01-01")

    stored = db_session.get(Exercise, body["id"])
    assert stored.is_preset is False
