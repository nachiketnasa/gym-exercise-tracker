"""Tests for PR auto-calculation (issue #11).

Mostly unit tests over in-memory :class:`PRInput` fixtures; a few API tests
cover the endpoint, the 404, and the never-logged case.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.metrics import epley_1rm
from app.models import Exercise, ExerciseEntry, WorkoutSession
from app.prs import PRInput, calculate_prs


def _pr(**kw):
    base = dict(entry_id=1, session_id=1, session_date=date(2026, 1, 1))
    base.update(kw)
    return PRInput(**base)


def _by_metric(records):
    return {r.metric: r for r in records}


# --- metric sets --------------------------------------------------------


def test_strength_metric_set_is_exactly_the_three_max_metrics():
    records = calculate_prs("strength", [])
    assert [r.metric for r in records] == [
        "max_weight",
        "max_reps",
        "max_estimated_1rm",
    ]
    assert all(r.value is None for r in records)
    assert all(
        r.achieved_on is None and r.session_id is None and r.entry_id is None
        for r in records
    )


def test_cardio_metric_set_is_exactly_best_pace_and_two_longest():
    records = calculate_prs("cardio", [])
    assert [r.metric for r in records] == [
        "best_pace",
        "longest_distance",
        "longest_duration",
    ]
    assert all(r.value is None for r in records)


# --- happy paths -------------------------------------------------------


def test_max_weight_and_max_reps_take_the_largest_value():
    entries = [
        _pr(entry_id=1, session_date=date(2026, 1, 1), weight=100, reps=5),
        _pr(entry_id=2, session_date=date(2026, 1, 2), weight=120, reps=3),
        _pr(entry_id=3, session_date=date(2026, 1, 3), weight=110, reps=8),
    ]
    got = _by_metric(calculate_prs("strength", entries))

    assert got["max_weight"].value == 120
    assert got["max_weight"].entry_id == 2
    assert got["max_weight"].achieved_on == date(2026, 1, 2)
    assert got["max_reps"].value == 8
    assert got["max_reps"].entry_id == 3


def test_max_estimated_1rm_uses_the_epley_formula():
    entries = [
        _pr(entry_id=1, weight=100, reps=5),  # 100 * (1 + 5/30) = 116.67
        _pr(entry_id=2, weight=140, reps=1),  # 140 * (1 + 1/30) = 144.67
        _pr(entry_id=3, weight=120, reps=10),  # 120 * (1 + 10/30) = 160.0
    ]
    got = _by_metric(calculate_prs("strength", entries))

    assert got["max_estimated_1rm"].value == pytest.approx(epley_1rm(120, 10))
    assert got["max_estimated_1rm"].value == pytest.approx(160.0)
    assert got["max_estimated_1rm"].entry_id == 3


def test_best_pace_is_the_smallest_and_longest_metrics_take_the_largest():
    entries = [
        _pr(entry_id=1, pace_seconds_per_km=330, distance_meters=5000, duration_seconds=1650),
        _pr(entry_id=2, pace_seconds_per_km=300, distance_meters=3000, duration_seconds=900),
        _pr(entry_id=3, pace_seconds_per_km=360, distance_meters=10000, duration_seconds=3600),
    ]
    got = _by_metric(calculate_prs("cardio", entries))

    assert got["best_pace"].value == 300
    assert got["best_pace"].entry_id == 2
    assert got["longest_distance"].value == 10000
    assert got["longest_distance"].entry_id == 3
    assert got["longest_duration"].value == 3600
    assert got["longest_duration"].entry_id == 3


# --- tie-break -------------------------------------------------------


def test_tie_break_prefers_earlier_session_date():
    entries = [
        _pr(entry_id=10, session_date=date(2026, 5, 5), weight=100),
        _pr(entry_id=11, session_date=date(2026, 5, 1), weight=100),
        _pr(entry_id=12, session_date=date(2026, 5, 9), weight=100),
    ]
    got = _by_metric(calculate_prs("strength", entries))
    assert got["max_weight"].entry_id == 11
    assert got["max_weight"].achieved_on == date(2026, 5, 1)


def test_tie_break_on_equal_dates_prefers_smaller_entry_id():
    entries = [
        _pr(entry_id=30, session_date=date(2026, 5, 1), weight=100),
        _pr(entry_id=20, session_date=date(2026, 5, 1), weight=100),
    ]
    got = _by_metric(calculate_prs("strength", entries))
    assert got["max_weight"].entry_id == 20


# --- skipped / incomplete entries -----------------------------------


def test_entries_missing_a_field_are_skipped_for_that_metric_only():
    entries = [
        _pr(entry_id=1, weight=100),  # no reps
        _pr(entry_id=2, reps=12),  # no weight
    ]
    got = _by_metric(calculate_prs("strength", entries))

    assert got["max_weight"].value == 100 and got["max_weight"].entry_id == 1
    assert got["max_reps"].value == 12 and got["max_reps"].entry_id == 2
    # neither entry has both weight and reps -> no 1RM estimate
    assert got["max_estimated_1rm"].value is None
    assert got["max_estimated_1rm"].entry_id is None


def test_zero_reps_disqualifies_the_1rm_estimate_only():
    entries = [_pr(entry_id=1, weight=150, reps=0)]
    got = _by_metric(calculate_prs("strength", entries))
    assert got["max_weight"].value == 150
    assert got["max_estimated_1rm"].value is None


def test_metric_with_no_qualifying_entry_is_null():
    # cardio entries with only pace: distance and duration stay null
    entries = [_pr(entry_id=1, pace_seconds_per_km=300)]
    got = _by_metric(calculate_prs("cardio", entries))
    assert got["best_pace"].value == 300
    assert got["longest_distance"].value is None
    assert got["longest_distance"].achieved_on is None
    assert got["longest_duration"].value is None


# --- API --------------------------------------------------------------


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


def _session_with_entries(db, on_date, exercise_id, entries):
    ws = WorkoutSession(date=on_date)
    for pos, metrics in enumerate(entries):
        ws.entries.append(
            ExerciseEntry(exercise_id=exercise_id, position=pos, **metrics)
        )
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


def test_prs_endpoint_returns_records_with_provenance(client, db_session):
    ex = _exercise(db_session, "Bench", "strength")
    s1 = _session_with_entries(
        db_session, date(2026, 1, 1), ex.id, [{"sets": 5, "reps": 5, "weight": 100}]
    )
    s2 = _session_with_entries(
        db_session, date(2026, 2, 1), ex.id, [{"sets": 3, "reps": 3, "weight": 120}]
    )

    body = client.get(f"/exercises/{ex.id}/prs").json()
    got = {r["metric"]: r for r in body}

    assert got["max_weight"]["value"] == 120.0
    assert got["max_weight"]["achieved_on"] == "2026-02-01"
    assert got["max_weight"]["session_id"] == s2.id
    assert got["max_reps"]["value"] == 5.0
    assert got["max_reps"]["session_id"] == s1.id


def test_prs_for_never_logged_exercise_returns_200_all_null(client, db_session):
    ex = _exercise(db_session, "Overhead Press", "strength")
    resp = client.get(f"/exercises/{ex.id}/prs")
    assert resp.status_code == 200
    body = resp.json()
    assert {r["metric"] for r in body} == {
        "max_weight",
        "max_reps",
        "max_estimated_1rm",
    }
    assert all(r["value"] is None for r in body)


def test_prs_for_unknown_exercise_returns_404(client):
    assert client.get("/exercises/999999/prs").status_code == 404


def test_prs_endpoint_uses_the_right_metric_set_for_cardio(client, db_session):
    ex = _exercise(db_session, "Rowing", "cardio")
    body = client.get(f"/exercises/{ex.id}/prs").json()
    assert {r["metric"] for r in body} == {
        "best_pace",
        "longest_distance",
        "longest_duration",
    }
