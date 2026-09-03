"""Seed the preset exercise library.

Running ``uv run python -m app.seed`` (from ``backend/``, after
``alembic upgrade head``) loads a fixed library of common exercises into the
database, each tagged as a preset (``is_preset = True``) with the correct
category.

The seed is idempotent:

* presets are matched to existing rows by case-insensitive name;
* a second run inserts nothing and changes no counts;
* a preset that was manually deleted is re-inserted on the next run;
* rows with ``is_preset = False`` (custom exercises) are never touched, and
  preset rows are never deleted.

It is a standalone script, deliberately not an Alembic data migration, so it
can be re-run freely.
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_repo_dotenv() -> None:
    """Populate ``os.environ`` from the repo-root ``.env`` (mirrors conftest).

    ``app.db`` reads ``DATABASE_URL`` at import time with no fallback, so this
    runs before the ``app.*`` imports below. Real environment variables win
    (``setdefault``), and a missing ``.env`` is fine.
    """
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_repo_dotenv()

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Exercise  # noqa: E402
from app.users import ensure_seed_user  # noqa: E402

#: The preset exercise library, defined as data: 22 entries (4 ``cardio``, the
#: rest ``strength``). The exact list is visible here on purpose.
PRESET_EXERCISES: list[dict[str, str]] = [
    # strength
    {"name": "Bench Press", "category": "strength"},
    {"name": "Back Squat", "category": "strength"},
    {"name": "Deadlift", "category": "strength"},
    {"name": "Overhead Press", "category": "strength"},
    {"name": "Barbell Row", "category": "strength"},
    {"name": "Pull-Up", "category": "strength"},
    {"name": "Chin-Up", "category": "strength"},
    {"name": "Front Squat", "category": "strength"},
    {"name": "Romanian Deadlift", "category": "strength"},
    {"name": "Incline Bench Press", "category": "strength"},
    {"name": "Dumbbell Shoulder Press", "category": "strength"},
    {"name": "Dumbbell Bicep Curl", "category": "strength"},
    {"name": "Tricep Pushdown", "category": "strength"},
    {"name": "Lat Pulldown", "category": "strength"},
    {"name": "Seated Cable Row", "category": "strength"},
    {"name": "Leg Press", "category": "strength"},
    {"name": "Hip Thrust", "category": "strength"},
    {"name": "Walking Lunge", "category": "strength"},
    # cardio
    {"name": "Running", "category": "cardio"},
    {"name": "Cycling", "category": "cardio"},
    {"name": "Rowing", "category": "cardio"},
    {"name": "Jump Rope", "category": "cardio"},
]


def seed(session: Session) -> tuple[int, int]:
    """Insert any missing presets into ``session``'s database.

    Existing exercises (preset or custom) are matched by case-insensitive name,
    so nothing is duplicated and no unique-index violation is possible. Returns
    ``(inserted, already_existed)``. The caller owns the session lifecycle; this
    commits the inserts.
    """
    existing_lower = {
        name.lower() for name in session.scalars(select(Exercise.name))
    }

    inserted = 0
    already = 0
    for preset in PRESET_EXERCISES:
        if preset["name"].lower() in existing_lower:
            already += 1
            continue
        session.add(
            Exercise(
                name=preset["name"],
                category=preset["category"],
                is_preset=True,
            )
        )
        inserted += 1

    session.commit()
    return inserted, already


def main() -> None:
    session = SessionLocal()
    try:
        ensure_seed_user(session)
        inserted, already = seed(session)
    finally:
        session.close()
    print(f"{inserted} inserted, {already} already existed")


if __name__ == "__main__":
    main()
