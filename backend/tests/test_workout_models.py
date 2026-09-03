"""Tests for the WorkoutSession / ExerciseEntry models and their migration (#8).

These use the per-test ``db_session`` rollback fixture from ``conftest.py``:
each test runs inside a transaction that is rolled back on teardown, so nothing
is left in the database.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import Exercise, ExerciseEntry, WorkoutSession


def _exercise(session, name: str, category: str) -> Exercise:
    exercise = Exercise(name=name, category=category)
    session.add(exercise)
    session.commit()
    session.refresh(exercise)
    return exercise


def test_session_with_notes_and_one_strength_and_one_cardio_entry(db_session):
    bench = _exercise(db_session, "Bench Press", "strength")
    run = _exercise(db_session, "Treadmill Run", "cardio")

    workout = WorkoutSession(date=date(2026, 9, 3), notes="felt strong")
    # Added out of position order on purpose to prove ``order_by`` sorts them.
    workout.entries.append(
        ExerciseEntry(
            exercise_id=run.id,
            position=2,
            duration_seconds=1800,
            distance_meters=Decimal("5000.00"),
            pace_seconds_per_km=Decimal("360.00"),
        )
    )
    workout.entries.append(
        ExerciseEntry(
            exercise_id=bench.id,
            position=1,
            sets=3,
            reps=8,
            weight=Decimal("60.00"),
            weight_unit="kg",
        )
    )
    db_session.add(workout)
    db_session.commit()
    workout_id = workout.id
    db_session.expunge_all()

    loaded = db_session.get(WorkoutSession, workout_id)
    assert loaded.date == date(2026, 9, 3)
    assert loaded.notes == "felt strong"
    assert loaded.created_at.tzinfo is not None
    assert loaded.updated_at.tzinfo is not None

    assert [e.position for e in loaded.entries] == [1, 2]
    strength, cardio = loaded.entries

    assert strength.exercise_id == bench.id
    assert strength.exercise.name == "Bench Press"
    assert strength.session.id == workout_id
    assert strength.sets == 3
    assert strength.reps == 8
    assert strength.weight == Decimal("60.00")
    assert strength.weight_unit == "kg"
    assert strength.duration_seconds is None
    assert strength.distance_meters is None
    assert strength.pace_seconds_per_km is None

    assert cardio.exercise_id == run.id
    assert cardio.duration_seconds == 1800
    assert cardio.distance_meters == Decimal("5000.00")
    assert cardio.pace_seconds_per_km == Decimal("360.00")
    assert cardio.sets is None
    assert cardio.reps is None
    assert cardio.weight is None
    assert cardio.weight_unit is None


def test_notes_defaults_to_null_when_omitted(db_session):
    workout = WorkoutSession(date=date(2026, 9, 3))
    db_session.add(workout)
    db_session.commit()
    db_session.refresh(workout)

    assert workout.notes is None


def test_deleting_a_session_cascades_to_its_entries(db_session):
    bench = _exercise(db_session, "Bench Press", "strength")
    workout = WorkoutSession(date=date(2026, 9, 3))
    workout.entries.append(ExerciseEntry(exercise_id=bench.id, position=1))
    workout.entries.append(ExerciseEntry(exercise_id=bench.id, position=2))
    db_session.add(workout)
    db_session.commit()
    workout_id = workout.id

    db_session.execute(
        WorkoutSession.__table__.delete().where(
            WorkoutSession.__table__.c.id == workout_id
        )
    )
    db_session.commit()

    remaining = db_session.query(ExerciseEntry).filter_by(
        session_id=workout_id
    ).count()
    assert remaining == 0


def test_entry_with_nonexistent_session_id_raises_integrity_error(db_session):
    bench = _exercise(db_session, "Bench Press", "strength")
    db_session.add(
        ExerciseEntry(session_id=999999, exercise_id=bench.id, position=1)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_entry_with_nonexistent_exercise_id_raises_integrity_error(db_session):
    workout = WorkoutSession(date=date(2026, 9, 3))
    db_session.add(workout)
    db_session.commit()

    db_session.add(
        ExerciseEntry(session_id=workout.id, exercise_id=999999, position=1)
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_deleting_an_exercise_with_entries_raises_integrity_error(db_session):
    bench = _exercise(db_session, "Bench Press", "strength")
    workout = WorkoutSession(date=date(2026, 9, 3))
    workout.entries.append(ExerciseEntry(exercise_id=bench.id, position=1))
    db_session.add(workout)
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            Exercise.__table__.delete().where(
                Exercise.__table__.c.id == bench.id
            )
        )
        db_session.commit()


def test_invalid_weight_unit_raises_a_database_error(db_session):
    bench = _exercise(db_session, "Bench Press", "strength")
    workout = WorkoutSession(date=date(2026, 9, 3))
    workout.entries.append(
        ExerciseEntry(exercise_id=bench.id, position=1, weight_unit="stone")
    )
    db_session.add(workout)
    with pytest.raises(DBAPIError) as excinfo:
        db_session.commit()
    assert "ck_exercise_entries_weight_unit" in str(excinfo.value).lower()


def test_updated_at_is_bumped_by_the_trigger_on_update(db_session):
    import time

    workout = WorkoutSession(date=date(2026, 9, 3))
    db_session.add(workout)
    db_session.commit()
    db_session.refresh(workout)
    original_updated_at = workout.updated_at
    original_created_at = workout.created_at

    time.sleep(0.01)
    workout.notes = "added later"
    db_session.commit()
    db_session.refresh(workout)

    assert workout.updated_at > original_updated_at
    assert workout.created_at == original_created_at
