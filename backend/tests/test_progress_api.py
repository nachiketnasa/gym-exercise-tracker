"""Tests for the per-exercise progress API (issue #13).

A few unit tests over in-memory :class:`ProgressInput` fixtures, then API
tests over ORM-built entries covering ordering, aggregation, the validation
errors, and the empty cases.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.metrics import epley_1rm
from app.models import Exercise, ExerciseEntry, WorkoutSession
from app.progress import ProgressInput, progress_series


def _p(day, **kw):
    return ProgressInput(session_date=date(2026, 1, day), **kw)


# --- unit: progress_series -------------------------------------------


def test_series_is_date_ascending_with_one_point_per_date_taking_the_max():
    points = progress_series(
        "weight",
        [
            _p(3, weight=100),
            _p(1, weight=80),
            _p(3, weight=120),  # same date as the first -> max wins
            _p(2, weight=90),
        ],
    )
    assert [(pt.date.day, pt.value) for pt in points] == [
        (1, 80),
        (2, 90),
        (3, 120),
    ]


def test_pace_series_takes_the_minimum_per_date():
    points = progress_series(
        "pace",
        [_p(1, pace_seconds_per_km=320), _p(1, pace_seconds_per_km=300)],
    )
    assert [(pt.date.day, pt.value) for pt in points] == [(1, 300)]


def test_estimated_1rm_series_uses_epley():
    points = progress_series("estimated_1rm", [_p(1, weight=100, reps=5)])
    assert points[0].value == pytest.approx(epley_1rm(100, 5))


def test_entries_missing_the_needed_value_produce_no_point():
    points = progress_series(
        "weight", [_p(1, reps=5), _p(2, weight=100)]
    )
    assert [pt.date.day for pt in points] == [2]


def test_no_entries_gives_empty_series():
    assert progress_series("weight", []) == []


# --- API ------------------------------------------------------------------


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


def _exercise(db, name, category):
    ex = Exercise(name=name, category=category, is_preset=False)
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return ex


def _session(db, on_date, exercise_id, entries):
    ws = WorkoutSession(date=on_date)
    for pos, metrics in enumerate(entries):
        ws.entries.append(
            ExerciseEntry(exercise_id=exercise_id, position=pos, **metrics)
        )
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


@pytest.fixture
def strength_exercise(db_session):
    return _exercise(db_session, "Squat", "strength")


@pytest.fixture
def cardio_exercise(db_session):
    return _exercise(db_session, "Run", "cardio")


def test_returns_200_list_of_date_value_points_ascending_one_per_date(
    client, db_session, strength_exercise
):
    _session(db_session, date(2026, 3, 3), strength_exercise.id, [{"sets": 5, "reps": 5, "weight": 100}])
    _session(db_session, date(2026, 3, 1), strength_exercise.id, [{"sets": 5, "reps": 5, "weight": 90}])
    # second entry on 03-03, higher weight -> that date's point is 110
    _session(db_session, date(2026, 3, 3), strength_exercise.id, [{"sets": 3, "reps": 3, "weight": 110}])

    resp = client.get(
        f"/exercises/{strength_exercise.id}/progress", params={"metric": "weight"}
    )

    assert resp.status_code == 200
    assert resp.json() == [
        {"date": "2026-03-01", "value": 90.0},
        {"date": "2026-03-03", "value": 110.0},
    ]


def test_pace_metric_aggregates_with_the_minimum(client, db_session, cardio_exercise):
    _session(db_session, date(2026, 3, 1), cardio_exercise.id, [{"distance_meters": 5000, "pace_seconds_per_km": 330}])
    _session(db_session, date(2026, 3, 1), cardio_exercise.id, [{"distance_meters": 5000, "pace_seconds_per_km": 300}])

    body = client.get(
        f"/exercises/{cardio_exercise.id}/progress", params={"metric": "pace"}
    ).json()

    assert body == [{"date": "2026-03-01", "value": 300.0}]


def test_estimated_1rm_metric_uses_epley(client, db_session, strength_exercise):
    _session(db_session, date(2026, 3, 1), strength_exercise.id, [{"sets": 5, "reps": 5, "weight": 100}])
    body = client.get(
        f"/exercises/{strength_exercise.id}/progress",
        params={"metric": "estimated_1rm"},
    ).json()
    assert body[0]["value"] == pytest.approx(epley_1rm(100, 5))


def test_incomplete_entries_are_skipped(client, db_session, cardio_exercise):
    # distance-only entry: no pace -> no point
    _session(db_session, date(2026, 3, 1), cardio_exercise.id, [{"distance_meters": 5000}])
    _session(db_session, date(2026, 3, 2), cardio_exercise.id, [{"distance_meters": 5000, "pace_seconds_per_km": 300}])

    body = client.get(
        f"/exercises/{cardio_exercise.id}/progress", params={"metric": "pace"}
    ).json()
    assert [pt["date"] for pt in body] == ["2026-03-02"]


def test_metric_is_required(client, strength_exercise):
    assert (
        client.get(f"/exercises/{strength_exercise.id}/progress").status_code == 422
    )


def test_metric_outside_vocabulary_returns_422(client, strength_exercise):
    resp = client.get(
        f"/exercises/{strength_exercise.id}/progress", params={"metric": "bogus"}
    )
    assert resp.status_code == 422


def test_metric_not_valid_for_category_returns_422(client, strength_exercise):
    resp = client.get(
        f"/exercises/{strength_exercise.id}/progress", params={"metric": "pace"}
    )
    assert resp.status_code == 422


@pytest.fixture
def dated_entries(db_session, strength_exercise):
    for day, weight in [(1, 80), (15, 100), (28, 120)]:
        _session(
            db_session,
            date(2026, 4, day),
            strength_exercise.id,
            [{"sets": 5, "reps": 5, "weight": weight}],
        )
    return strength_exercise


def test_start_and_end_filter_inclusive(client, dated_entries):
    body = client.get(
        f"/exercises/{dated_entries.id}/progress",
        params={"metric": "weight", "start": "2026-04-01", "end": "2026-04-15"},
    ).json()
    assert [pt["date"] for pt in body] == ["2026-04-01", "2026-04-15"]


def test_start_alone_and_end_alone(client, dated_entries):
    after = client.get(
        f"/exercises/{dated_entries.id}/progress",
        params={"metric": "weight", "start": "2026-04-15"},
    ).json()
    assert [pt["date"] for pt in after] == ["2026-04-15", "2026-04-28"]

    before = client.get(
        f"/exercises/{dated_entries.id}/progress",
        params={"metric": "weight", "end": "2026-04-15"},
    ).json()
    assert [pt["date"] for pt in before] == ["2026-04-01", "2026-04-15"]


def test_range_excluding_all_entries_returns_200_empty(client, dated_entries):
    resp = client.get(
        f"/exercises/{dated_entries.id}/progress",
        params={"metric": "weight", "start": "2025-01-01", "end": "2025-12-31"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_start_later_than_end_returns_422(client, strength_exercise):
    resp = client.get(
        f"/exercises/{strength_exercise.id}/progress",
        params={"metric": "weight", "start": "2026-04-28", "end": "2026-04-01"},
    )
    assert resp.status_code == 422


@pytest.mark.parametrize("field", ["start", "end"])
def test_malformed_date_returns_422(client, strength_exercise, field):
    resp = client.get(
        f"/exercises/{strength_exercise.id}/progress",
        params={"metric": "weight", field: "01-04-2026"},
    )
    assert resp.status_code == 422


def test_exercise_with_no_entries_returns_200_empty(client, strength_exercise):
    resp = client.get(
        f"/exercises/{strength_exercise.id}/progress", params={"metric": "weight"}
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_unknown_exercise_returns_404(client):
    resp = client.get("/exercises/999999/progress", params={"metric": "weight"})
    assert resp.status_code == 404
