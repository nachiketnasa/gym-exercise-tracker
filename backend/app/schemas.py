"""Pydantic request/response models for the API.

Kept separate from the SQLAlchemy ORM models in ``app.models``: these describe
the JSON shapes clients send and receive, and deliberately expose only what a
caller is allowed to set.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

#: A name is trimmed of surrounding whitespace first, then must be 1-100
#: characters. A whitespace-only name therefore fails (it trims to "").
ExerciseName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class ExerciseCreate(BaseModel):
    """Input for ``POST /exercises``.

    Only ``name`` and ``category`` are accepted. ``id``, ``is_preset`` and the
    timestamps are server-owned and simply not part of this model, so any
    client-supplied values for them are ignored.
    """

    model_config = ConfigDict(extra="ignore")

    name: ExerciseName
    category: Literal["strength", "cardio"]


class ExerciseRead(BaseModel):
    """A single exercise as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    is_preset: bool
    created_at: datetime
    updated_at: datetime
