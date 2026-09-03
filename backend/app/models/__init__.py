"""ORM models.

Importing this package imports every model module so that ``Base.metadata``
is fully populated (Alembic autogenerate and the test schema setup rely on
that).
"""

from app.models.exercise import Exercise
from app.models.workout import ExerciseEntry, WorkoutSession

__all__ = ["Exercise", "ExerciseEntry", "WorkoutSession"]
