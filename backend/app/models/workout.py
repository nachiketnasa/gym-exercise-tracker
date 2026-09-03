"""The ``WorkoutSession`` and ``ExerciseEntry`` models.

A ``WorkoutSession`` records a workout done on a ``date`` with optional
``notes`` and audit timestamps. Each ``ExerciseEntry`` links a session to an
``Exercise`` at a fixed ``position`` and carries both the strength metric
columns (``sets`` / ``reps`` / ``weight`` / ``weight_unit``) and the cardio
metric columns (``duration_seconds`` / ``distance_meters`` /
``pace_seconds_per_km``). All metric columns are nullable; nothing here ties
which ones are set to the linked exercise's category — that validation lives in
the logging API (#9).

Workout sessions are user-owned: ``user_id`` is a non-null foreign key to
``users.id`` (#14). It defaults to the seeded local user so callers that do not
name an owner still get a valid row while the app is single-user.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.users import SEED_USER_ID

#: The units ``weight`` may be recorded in. Enforced in the database by the
#: ``ck_exercise_entries_weight_unit`` CHECK constraint (see the migration).
WEIGHT_UNITS: tuple[str, ...] = ("kg", "lb")


class WorkoutSession(Base):
    """A workout done on a given date.

    ``user_id`` is a non-null FK to ``users.id`` and defaults to the seeded
    local user (#14).
    """

    __tablename__ = "workout_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        default=SEED_USER_ID,
    )
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        # The database refreshes this via the ``workout_sessions_set_updated_at``
        # trigger (see the migration); this marker tells SQLAlchemy to re-read
        # the value from the row after an UPDATE.
        server_onupdate=func.now(),
    )

    entries: Mapped[list["ExerciseEntry"]] = relationship(
        back_populates="session",
        order_by="ExerciseEntry.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    user: Mapped["User"] = relationship()  # noqa: F821


class ExerciseEntry(Base):
    """One exercise performed within a :class:`WorkoutSession`."""

    __tablename__ = "exercise_entries"

    __table_args__ = (
        CheckConstraint(
            "weight_unit IN ('kg', 'lb')",
            name="ck_exercise_entries_weight_unit",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), nullable=False
    )
    #: Stable ordering of entries within a session.
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Strength metrics (all nullable).
    sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    weight_unit: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Cardio metrics (all nullable).
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    pace_seconds_per_km: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        server_onupdate=func.now(),
    )

    session: Mapped["WorkoutSession"] = relationship(back_populates="entries")
    exercise: Mapped["Exercise"] = relationship()  # noqa: F821
