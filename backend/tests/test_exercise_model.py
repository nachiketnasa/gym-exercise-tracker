"""Tests for the Exercise model and its migration (issue #5).

These use the per-test ``db_session`` rollback fixture from ``conftest.py``: each
test runs inside a transaction that is rolled back on teardown, so nothing is
left in the database.
"""

from __future__ import annotations

import time

import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import Exercise


def test_create_and_read_back_strength_and_cardio(db_session):
    strength = Exercise(name="Bench Press", category="strength")
    cardio = Exercise(name="Treadmill Run", category="cardio")
    db_session.add_all([strength, cardio])
    db_session.commit()
    db_session.refresh(strength)
    db_session.refresh(cardio)

    for ex, category in ((strength, "strength"), (cardio, "cardio")):
        loaded = db_session.get(Exercise, ex.id)
        assert loaded is not None
        assert loaded.category == category
        assert loaded.is_preset is False
        assert loaded.created_at is not None
        assert loaded.updated_at is not None
        assert loaded.created_at.tzinfo is not None
        assert loaded.updated_at.tzinfo is not None


def test_invalid_category_is_rejected_by_the_database(db_session):
    db_session.add(Exercise(name="Yoga Flow", category="flexibility"))
    with pytest.raises(DBAPIError) as excinfo:
        db_session.commit()
    # It is the CHECK constraint that fails, not a Python-side validation.
    assert "ck_exercises_category" in str(excinfo.value).lower()


def test_name_uniqueness_is_case_insensitive(db_session):
    db_session.add(Exercise(name="Bench Press", category="strength"))
    db_session.commit()

    db_session.add(Exercise(name="bench press", category="strength"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_updated_at_changes_after_modify_and_commit(db_session):
    ex = Exercise(name="Deadlift", category="strength")
    db_session.add(ex)
    db_session.commit()
    db_session.refresh(ex)
    original_updated_at = ex.updated_at
    original_created_at = ex.created_at

    time.sleep(0.01)

    ex.category = "cardio"
    db_session.commit()
    db_session.refresh(ex)

    assert ex.updated_at > original_updated_at
    # created_at is untouched by the update.
    assert ex.created_at == original_created_at
