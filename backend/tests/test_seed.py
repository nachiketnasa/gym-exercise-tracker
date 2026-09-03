"""Tests for the preset exercise seed (issue #6).

These use the per-test ``db_session`` rollback fixture from ``conftest.py``, so
each seed run happens inside a transaction that is rolled back on teardown.
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import Exercise
from app.seed import PRESET_EXERCISES, seed


def _preset_count(session) -> int:
    return session.scalar(
        select(func.count()).select_from(Exercise).where(Exercise.is_preset.is_(True))
    )


def test_seed_inserts_every_preset_with_expected_category(db_session):
    inserted, already = seed(db_session)

    assert inserted == len(PRESET_EXERCISES)
    assert already == 0
    assert _preset_count(db_session) == len(PRESET_EXERCISES)

    by_lower_name = {
        name.lower(): category
        for name, category in db_session.execute(
            select(Exercise.name, Exercise.category).where(Exercise.is_preset.is_(True))
        )
    }
    for name, category in (
        ("bench press", "strength"),
        ("back squat", "strength"),
        ("deadlift", "strength"),
        ("overhead press", "strength"),
        ("barbell row", "strength"),
        ("pull-up", "strength"),
        ("running", "cardio"),
        ("cycling", "cardio"),
        ("rowing", "cardio"),
    ):
        assert by_lower_name[name] == category


def test_seeding_twice_leaves_preset_count_unchanged(db_session):
    first_inserted, first_already = seed(db_session)
    count_after_first = _preset_count(db_session)

    second_inserted, second_already = seed(db_session)

    assert first_inserted == len(PRESET_EXERCISES)
    assert first_already == 0
    assert second_inserted == 0
    assert second_already == len(PRESET_EXERCISES)
    assert _preset_count(db_session) == count_after_first


def test_manually_deleted_preset_is_reinserted(db_session):
    seed(db_session)

    deadlift = db_session.scalar(
        select(Exercise).where(func.lower(Exercise.name) == "deadlift")
    )
    db_session.delete(deadlift)
    db_session.commit()
    assert _preset_count(db_session) == len(PRESET_EXERCISES) - 1

    inserted, already = seed(db_session)

    assert inserted == 1
    assert already == len(PRESET_EXERCISES) - 1
    assert _preset_count(db_session) == len(PRESET_EXERCISES)


def test_seed_leaves_custom_exercises_untouched(db_session):
    custom = Exercise(name="My Custom Curl", category="strength", is_preset=False)
    db_session.add(custom)
    db_session.commit()
    db_session.refresh(custom)
    original_updated_at = custom.updated_at

    seed(db_session)

    db_session.refresh(custom)
    assert custom.is_preset is False
    assert custom.updated_at == original_updated_at
    assert (
        db_session.scalar(
            select(Exercise).where(Exercise.name == "My Custom Curl")
        )
        is not None
    )


def test_preset_list_shape():
    assert 15 <= len(PRESET_EXERCISES) <= 25
    categories = [p["category"] for p in PRESET_EXERCISES]
    assert categories.count("cardio") >= 3
    assert set(categories) == {"strength", "cardio"}
    assert categories.count("strength") + categories.count("cardio") == len(
        PRESET_EXERCISES
    )
