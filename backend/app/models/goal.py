"""The ``Goal`` model (issue #12).

A goal is one target value for one metric of one exercise, e.g. "bench 200lb
x5" or "5k under 25min". An exercise may hold several goals at once, including
more than one on the same metric, so there is no uniqueness constraint here.

The allowed ``metric`` vocabulary lives in ``app.metrics`` and is enforced in
the router (it depends on the linked exercise's category). Goals are user-owned:
``user_id`` is a non-null FK to ``users.id`` and defaults to the seeded local
user (#14).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.users import SEED_USER_ID


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        default=SEED_USER_ID,
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric: Mapped[str] = mapped_column(String, nullable=False)
    target_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        # Refreshed by the ``goals_set_updated_at`` trigger (see the migration).
        server_onupdate=func.now(),
    )

    exercise: Mapped["Exercise"] = relationship()  # noqa: F821
    user: Mapped["User"] = relationship()  # noqa: F821
