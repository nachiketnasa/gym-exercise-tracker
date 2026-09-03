"""The ``Exercise`` model.

An exercise has a name, a category (``strength`` or ``cardio``), a flag marking
whether it is a built-in preset or a user-created custom entry, and audit
timestamps. Exercises are shared, not user-owned (see issue #14), so there is no
``user_id`` column here.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

#: The categories an exercise may have. Enforced in the database by
#: ``ck_exercises_category`` (see the migration).
CATEGORIES: tuple[str, ...] = ("strength", "cardio")


class Exercise(Base):
    __tablename__ = "exercises"

    __table_args__ = (
        CheckConstraint(
            "category IN ('strength', 'cardio')",
            name="ck_exercises_category",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    is_preset: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        # The database also refreshes this via the ``exercises_set_updated_at``
        # trigger (see the migration); this marker tells SQLAlchemy to re-read
        # the value from the row after an UPDATE.
        server_onupdate=func.now(),
    )


# Case-insensitive uniqueness on name: "Bench Press" and "bench press" cannot
# both exist. A unique index on lower(name).
Index(
    "ix_exercises_name_lower",
    func.lower(Exercise.name),
    unique=True,
)
