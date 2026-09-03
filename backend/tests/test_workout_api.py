"""API tests for the Workout logging endpoints (issue #9).

Same pattern as ``test_exercise_api.py``: the per-test ``db_session`` rollback
fixture is wired into FastAPI via ``app.dependency_overrides[get_session]``, so
every request runs inside a transaction rolled back on teardown.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

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


@pytest.fixture
def strength_exercise(db_session):
    return _make_exercise(db_session, "Back Squat", "strength")


@pytest.fixture
def cardio_exercise(db_session):
    return _make_exercise(db_session, "Treadmill Run", "cardio")


def _make_exercise(session, name, category):
    exercise = Exercise(name=name, category=category, is_preset=False)
    session.add(exercise)
    session.commit()
    session.refresh(exercise)
    return exercise


def _strength_entry(exercise_id, **overrides):
    payload = {"exercise_id": exercise_id, "sets": 5, "reps": 5, "weight": 100.0}
    payload.update(overrides)
    return payload


def _cardio_entry(exercise_id, **overrides):
    payload = {"exercise_id": exercise_id, "duration_seconds": 1800, "distance_meters": 5000.0}
    payload.update(overrides)
    return payload


TODAY = date.today().isoformat()


# --- POST /sessions ---------------------------------------------------------


def test_create_empty_session_returns_201_with_id_date_notes_and_empty_entries(client):
    response = client.post("/sessions", json={"date": TODAY, "notes": "leg day"})

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["date"] == TODAY
    assert body["notes"] == "leg day"
    assert body["entries"] == []


def test_create_session_with_entries_persists_and_echoes_them_all(
    client, strength_exercise, cardio_exercise
):
    response = client.post(
        "/sessions",
        json={
            "date": TODAY,
            "entries": [
                _strength_entry(strength_exercise.id),
                _cardio_entry(cardio_exercise.id),
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert [e["exercise_id"] for e in body["entries"]] == [
        strength_exercise.id,
        cardio_exercise.id,
    ]
    assert [e["position"] for e in body["entries"]] == [0, 1]
    assert body["entries"][0]["sets"] == 5
    assert body["entries"][1]["duration_seconds"] == 1800

    # persisted: a fresh GET returns the same entries
    fetched = client.get(f"/sessions/{body['id']}").json()
    assert len(fetched["entries"]) == 2


def test_date_defaults_to_today_when_omitted(client):
    body = client.post("/sessions", json={}).json()
    assert body["date"] == TODAY


def test_notes_is_null_when_omitted(client):
    response = client.post("/sessions", json={})
    assert response.status_code == 201
    assert response.json()["notes"] is None


def test_future_date_is_rejected_with_422(client):
    future = (date.today() + timedelta(days=1)).isoformat()
    response = client.post("/sessions", json={"date": future})
    assert response.status_code == 422


def test_malformed_date_is_rejected_with_422(client):
    response = client.post("/sessions", json={"date": "03-09-2026"})
    assert response.status_code == 422


# --- GET /sessions/{id} ----------------------------------------------------


def test_get_session_returns_200_with_date_notes_and_ordered_entries(
    client, strength_exercise, cardio_exercise
):
    created = client.post(
        "/sessions",
        json={
            "date": TODAY,
            "notes": "mixed",
            "entries": [
                _cardio_entry(cardio_exercise.id),
                _strength_entry(strength_exercise.id),
            ],
        },
    ).json()

    response = client.get(f"/sessions/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["date"] == TODAY
    assert body["notes"] == "mixed"
    assert [e["position"] for e in body["entries"]] == [0, 1]
    assert body["entries"][0]["exercise_id"] == cardio_exercise.id
    assert set(body["entries"][0]) == {
        "id",
        "exercise_id",
        "position",
        "sets",
        "reps",
        "weight",
        "weight_unit",
        "duration_seconds",
        "distance_meters",
        "pace_seconds_per_km",
    }


def test_get_session_unknown_id_returns_404(client):
    response = client.get("/sessions/999999")
    assert response.status_code == 404


# --- POST /sessions/{id}/entries -----------------------------------------


def test_add_entry_appends_and_is_included_in_subsequent_get(
    client, strength_exercise
):
    session_id = client.post("/sessions", json={}).json()["id"]

    response = client.post(
        f"/sessions/{session_id}/entries", json=_strength_entry(strength_exercise.id)
    )

    assert response.status_code == 201
    entry = response.json()
    assert isinstance(entry["id"], int)
    assert entry["position"] == 0

    fetched = client.get(f"/sessions/{session_id}").json()
    assert [e["id"] for e in fetched["entries"]] == [entry["id"]]


def test_add_entry_appends_at_the_end(client, strength_exercise, cardio_exercise):
    session_id = client.post(
        "/sessions", json={"entries": [_strength_entry(strength_exercise.id)]}
    ).json()["id"]

    entry = client.post(
        f"/sessions/{session_id}/entries", json=_cardio_entry(cardio_exercise.id)
    ).json()
    assert entry["position"] == 1


def test_add_entry_on_unknown_session_returns_404(client, strength_exercise):
    response = client.post(
        "/sessions/999999/entries", json=_strength_entry(strength_exercise.id)
    )
    assert response.status_code == 404


# --- PATCH /sessions/{id}/entries/{entry_id} ----------------------------


def test_patch_updates_supplied_metric_fields_and_returns_updated_entry(
    client, strength_exercise
):
    session_id = client.post("/sessions", json={}).json()["id"]
    entry = client.post(
        f"/sessions/{session_id}/entries", json=_strength_entry(strength_exercise.id)
    ).json()

    response = client.patch(
        f"/sessions/{session_id}/entries/{entry['id']}", json={"reps": 8, "weight": 110.0}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reps"] == 8
    assert body["weight"] == 110.0
    assert body["sets"] == 5  # untouched


def test_patch_on_unknown_session_returns_404(client):
    response = client.patch("/sessions/999999/entries/1", json={"reps": 8})
    assert response.status_code == 404


def test_patch_entry_from_a_different_session_returns_404(
    client, strength_exercise
):
    a = client.post(
        "/sessions", json={"entries": [_strength_entry(strength_exercise.id)]}
    ).json()
    b = client.post("/sessions", json={}).json()
    other_entry_id = a["entries"][0]["id"]

    response = client.patch(
        f"/sessions/{b['id']}/entries/{other_entry_id}", json={"reps": 8}
    )
    assert response.status_code == 404


def test_patch_with_wrong_category_field_returns_422(client, strength_exercise):
    session_id = client.post("/sessions", json={}).json()["id"]
    entry = client.post(
        f"/sessions/{session_id}/entries", json=_strength_entry(strength_exercise.id)
    ).json()

    response = client.patch(
        f"/sessions/{session_id}/entries/{entry['id']}", json={"duration_seconds": 600}
    )
    assert response.status_code == 422


def test_patch_with_non_positive_value_returns_422(client, strength_exercise):
    session_id = client.post("/sessions", json={}).json()["id"]
    entry = client.post(
        f"/sessions/{session_id}/entries", json=_strength_entry(strength_exercise.id)
    ).json()

    response = client.patch(
        f"/sessions/{session_id}/entries/{entry['id']}", json={"reps": 0}
    )
    assert response.status_code == 422


# --- DELETE /sessions/{id}/entries/{entry_id} --------------------------


def test_delete_entry_returns_204_and_removes_it(client, strength_exercise):
    session_id = client.post("/sessions", json={}).json()["id"]
    entry = client.post(
        f"/sessions/{session_id}/entries", json=_strength_entry(strength_exercise.id)
    ).json()

    response = client.delete(f"/sessions/{session_id}/entries/{entry['id']}")

    assert response.status_code == 204
    assert response.content == b""
    fetched = client.get(f"/sessions/{session_id}").json()
    assert fetched["entries"] == []


def test_delete_on_unknown_session_returns_404(client):
    response = client.delete("/sessions/999999/entries/1")
    assert response.status_code == 404


def test_delete_entry_from_a_different_session_returns_404(client, strength_exercise):
    a = client.post(
        "/sessions", json={"entries": [_strength_entry(strength_exercise.id)]}
    ).json()
    b = client.post("/sessions", json={}).json()
    other_entry_id = a["entries"][0]["id"]

    response = client.delete(f"/sessions/{b['id']}/entries/{other_entry_id}")
    assert response.status_code == 404


# --- Entry metric validation -------------------------------------------


def test_entry_with_unknown_exercise_id_returns_422(client):
    response = client.post("/sessions", json={"entries": [_strength_entry(999999)]})
    assert response.status_code == 422


def test_strength_fields_on_a_cardio_exercise_return_422(client, cardio_exercise):
    response = client.post(
        "/sessions",
        json={"entries": [{"exercise_id": cardio_exercise.id, "sets": 3, "reps": 3}]},
    )
    assert response.status_code == 422


def test_cardio_fields_on_a_strength_exercise_return_422(client, strength_exercise):
    response = client.post(
        "/sessions",
        json={
            "entries": [
                {"exercise_id": strength_exercise.id, "sets": 3, "reps": 3, "duration_seconds": 60}
            ]
        },
    )
    assert response.status_code == 422


def test_strength_entry_missing_required_fields_returns_422(client, strength_exercise):
    response = client.post(
        "/sessions",
        json={"entries": [{"exercise_id": strength_exercise.id, "weight": 100.0}]},
    )
    assert response.status_code == 422


def test_cardio_entry_missing_required_fields_returns_422(client, cardio_exercise):
    response = client.post(
        "/sessions",
        json={"entries": [{"exercise_id": cardio_exercise.id, "pace_seconds_per_km": 300.0}]},
    )
    assert response.status_code == 422


def test_cardio_entry_with_only_distance_is_accepted(client, cardio_exercise):
    response = client.post(
        "/sessions",
        json={"entries": [{"exercise_id": cardio_exercise.id, "distance_meters": 5000.0}]},
    )
    assert response.status_code == 201


@pytest.mark.parametrize("field", ["sets", "reps", "weight"])
def test_non_positive_strength_value_returns_422(client, strength_exercise, field):
    response = client.post(
        "/sessions",
        json={"entries": [_strength_entry(strength_exercise.id, **{field: 0})]},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("field", ["duration_seconds", "distance_meters"])
def test_non_positive_cardio_value_returns_422(client, cardio_exercise, field):
    response = client.post(
        "/sessions",
        json={"entries": [_cardio_entry(cardio_exercise.id, **{field: -1})]},
    )
    assert response.status_code == 422


def test_add_entry_with_unknown_exercise_on_valid_session_returns_422(client):
    session_id = client.post("/sessions", json={}).json()["id"]
    response = client.post(
        f"/sessions/{session_id}/entries", json=_strength_entry(999999)
    )
    assert response.status_code == 422


# --- General ----------------------------------------------------------------


def test_validation_errors_are_json_bodies(client):
    response = client.post("/sessions", json={"date": "not-a-date"})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert "detail" in response.json()
