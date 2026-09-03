"""API tests for the Workout history endpoint ``GET /sessions`` (issue #10).

Sessions and entries are built directly through the ORM (not the logging API)
so tests can pin ``date`` and ``created_at`` for the ordering checks. The
per-test ``db_session`` rollback fixture is wired into FastAPI the usual way.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.models import Exercise, ExerciseEntry, WorkoutSession


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


def _exercise(db, name, category="strength"):
    ex = Exercise(name=name, category=category, is_preset=False)
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return ex


def _session(db, on_date, exercise_ids=(), created_at=None):
    ws = WorkoutSession(date=on_date)
    if created_at is not None:
        ws.created_at = created_at
    for pos, ex_id in enumerate(exercise_ids):
        ws.entries.append(
            ExerciseEntry(
                exercise_id=ex_id, position=pos, sets=5, reps=5, weight=100
            )
        )
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


def _dt(day):
    return datetime(2026, 1, day, 12, 0, tzinfo=timezone.utc)


# --- shape -----------------------------------------------------------------


def test_response_has_items_page_page_size_and_total(client, db_session):
    ex = _exercise(db_session, "Squat")
    _session(db_session, date(2026, 2, 1), [ex.id])

    body = client.get("/sessions").json()

    assert set(body) == {"items", "page", "page_size", "total"}
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 1
    item = body["items"][0]
    assert set(item) == {"id", "date", "exercise_count", "primary_lifts"}
    assert item["date"] == "2026-02-01"


def test_no_sessions_returns_empty_items_page_1_total_0(client):
    body = client.get("/sessions").json()
    assert body == {"items": [], "page": 1, "page_size": 20, "total": 0}


# --- summary content -----------------------------------------------------


def test_exercise_count_is_distinct_and_primary_lifts_ordered_and_capped(
    client, db_session
):
    a = _exercise(db_session, "Bench")
    b = _exercise(db_session, "Deadlift")
    c = _exercise(db_session, "Curl")
    d = _exercise(db_session, "Row")
    # Bench x3, Deadlift x2, Curl x1, Row x1 -> count 4;
    # primary_lifts: Bench, Deadlift, then Curl (name asc beats Row).
    _session(
        db_session,
        date(2026, 3, 1),
        [a.id, a.id, a.id, b.id, b.id, c.id, d.id],
    )

    item = client.get("/sessions").json()["items"][0]

    assert item["exercise_count"] == 4
    assert item["primary_lifts"] == ["Bench", "Deadlift", "Curl"]


def test_session_with_no_entries_has_zero_count_and_empty_primary_lifts(
    client, db_session
):
    _session(db_session, date(2026, 3, 2), [])

    item = client.get("/sessions").json()["items"][0]

    assert item["exercise_count"] == 0
    assert item["primary_lifts"] == []


# --- ordering ------------------------------------------------------------


def test_items_ordered_by_date_descending(client, db_session):
    ex = _exercise(db_session, "Squat")
    _session(db_session, date(2026, 1, 10), [ex.id])
    _session(db_session, date(2026, 1, 30), [ex.id])
    _session(db_session, date(2026, 1, 20), [ex.id])

    dates = [i["date"] for i in client.get("/sessions").json()["items"]]

    assert dates == ["2026-01-30", "2026-01-20", "2026-01-10"]


def test_same_date_tie_break_prefers_newer_created_at_then_higher_id(
    client, db_session
):
    ex = _exercise(db_session, "Squat")
    same = date(2026, 4, 1)
    # Inserted first -> lower id, but newer created_at: must come first.
    newer = _session(db_session, same, [ex.id], created_at=_dt(5))
    # Inserted second -> higher id, older created_at: must come last.
    older = _session(db_session, same, [ex.id], created_at=_dt(1))
    # Third: same date, same created_at as `newer`; id tie-break -> before newer.
    same_ts = _session(db_session, same, [ex.id], created_at=_dt(5))

    ids = [i["id"] for i in client.get("/sessions").json()["items"]]

    assert ids == [same_ts.id, newer.id, older.id]


# --- pagination --------------------------------------------------------


def test_page_and_page_size_paginate_and_total_is_full_count(client, db_session):
    ex = _exercise(db_session, "Squat")
    for day in range(1, 8):  # 7 sessions, dates 2026-05-01..07
        _session(db_session, date(2026, 5, day), [ex.id])

    page1 = client.get("/sessions", params={"page": 1, "page_size": 3}).json()
    page3 = client.get("/sessions", params={"page": 3, "page_size": 3}).json()

    assert page1["total"] == 7 and page3["total"] == 7
    assert [i["date"] for i in page1["items"]] == [
        "2026-05-07",
        "2026-05-06",
        "2026-05-05",
    ]
    assert [i["date"] for i in page3["items"]] == ["2026-05-01"]  # 7 % 3 == 1


def test_page_past_the_end_returns_200_empty_items_and_correct_total(
    client, db_session
):
    ex = _exercise(db_session, "Squat")
    _session(db_session, date(2026, 6, 1), [ex.id])
    _session(db_session, date(2026, 6, 2), [ex.id])

    resp = client.get("/sessions", params={"page": 5, "page_size": 20})

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 2
    assert body["page"] == 5


def test_page_size_over_maximum_returns_422(client):
    assert client.get("/sessions", params={"page_size": 101}).status_code == 422


def test_page_size_at_maximum_is_accepted(client):
    assert client.get("/sessions", params={"page_size": 100}).status_code == 200


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page": -1},
        {"page": "two"},
        {"page_size": 0},
        {"page_size": -5},
        {"page_size": "ten"},
    ],
)
def test_out_of_range_or_non_integer_pagination_returns_422(client, params):
    assert client.get("/sessions", params=params).status_code == 422


# --- date filtering ---------------------------------------------------


@pytest.fixture
def three_dated_sessions(db_session):
    ex = _exercise(db_session, "Squat")
    _session(db_session, date(2026, 7, 1), [ex.id])
    _session(db_session, date(2026, 7, 15), [ex.id])
    _session(db_session, date(2026, 7, 31), [ex.id])
    return ex


def test_start_and_end_filter_inclusive_on_both_ends(client, three_dated_sessions):
    body = client.get(
        "/sessions", params={"start": "2026-07-01", "end": "2026-07-15"}
    ).json()

    assert [i["date"] for i in body["items"]] == ["2026-07-15", "2026-07-01"]
    assert body["total"] == 2


def test_start_alone_leaves_the_upper_bound_open(client, three_dated_sessions):
    body = client.get("/sessions", params={"start": "2026-07-15"}).json()
    assert [i["date"] for i in body["items"]] == ["2026-07-31", "2026-07-15"]
    assert body["total"] == 2


def test_end_alone_leaves_the_lower_bound_open(client, three_dated_sessions):
    body = client.get("/sessions", params={"end": "2026-07-15"}).json()
    assert [i["date"] for i in body["items"]] == ["2026-07-15", "2026-07-01"]
    assert body["total"] == 2


def test_total_reflects_the_filtered_count_not_the_whole_table(
    client, three_dated_sessions
):
    body = client.get(
        "/sessions", params={"start": "2026-07-10", "end": "2026-07-20"}
    ).json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_range_matching_no_sessions_returns_200_empty_and_total_0(
    client, three_dated_sessions
):
    resp = client.get(
        "/sessions", params={"start": "2025-01-01", "end": "2025-12-31"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_start_later_than_end_returns_422(client):
    resp = client.get(
        "/sessions", params={"start": "2026-07-31", "end": "2026-07-01"}
    )
    assert resp.status_code == 422


@pytest.mark.parametrize("field", ["start", "end"])
def test_malformed_date_returns_422(client, field):
    assert client.get("/sessions", params={field: "31-07-2026"}).status_code == 422
    assert client.get("/sessions", params={field: "not-a-date"}).status_code == 422
