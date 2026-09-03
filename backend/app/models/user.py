"""The ``User`` model (issue #14 - single-user scoping stub).

The app is single-user for now: exactly one row lives in ``users``, the seeded
local user (see :mod:`app.users`). Every user-owned row (``workout_sessions``,
``goals``) carries a non-null ``user_id`` foreign key to it.

Real authentication - logging in and resolving the current user from the
request - is #27. Until then the ``current_user`` dependency in :mod:`app.deps`
always returns this one user, and this model just needs to exist and be stable.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    #: Stable, well-known identifier for the local user. Unique, not null.
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        # Refreshed by the ``users_set_updated_at`` trigger (see the migration).
        server_onupdate=func.now(),
    )
