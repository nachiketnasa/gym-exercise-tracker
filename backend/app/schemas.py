"""Pydantic request/response models for the API.

Kept separate from the SQLAlchemy ORM models in ``app.models``: these describe
the JSON shapes clients send and receive, and deliberately expose only what a
caller is allowed to set.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveFloat,
    PositiveInt,
    StringConstraints,
    model_validator,
)

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


# --- Workout logging (issue #9) ----------------------------------------------

#: Metric fields that belong to a strength exercise.
STRENGTH_METRIC_FIELDS: tuple[str, ...] = ("sets", "reps", "weight", "weight_unit")
#: Metric fields that belong to a cardio exercise.
CARDIO_METRIC_FIELDS: tuple[str, ...] = (
    "duration_seconds",
    "distance_meters",
    "pace_seconds_per_km",
)

WeightUnit = Literal["kg", "lb"]


class EntryCreate(BaseModel):
    """Input for creating one exercise entry.

    Non-positive numbers are rejected here (422); the cross-field checks that
    depend on the exercise's category (wrong-category fields, missing required
    fields, unknown ``exercise_id``) are done in the router where the DB is
    available.
    """

    model_config = ConfigDict(extra="ignore")

    exercise_id: int

    # Strength metrics.
    sets: PositiveInt | None = None
    reps: PositiveInt | None = None
    weight: PositiveFloat | None = None
    weight_unit: WeightUnit | None = None

    # Cardio metrics.
    duration_seconds: PositiveInt | None = None
    distance_meters: PositiveFloat | None = None
    pace_seconds_per_km: PositiveFloat | None = None


class EntryUpdate(BaseModel):
    """Input for ``PATCH`` on an entry: every metric field is optional.

    Only the fields present in the request body are applied. ``exercise_id`` is
    fixed once an entry is created and is not part of this model.
    """

    model_config = ConfigDict(extra="ignore")

    sets: PositiveInt | None = None
    reps: PositiveInt | None = None
    weight: PositiveFloat | None = None
    weight_unit: WeightUnit | None = None

    duration_seconds: PositiveInt | None = None
    distance_meters: PositiveFloat | None = None
    pace_seconds_per_km: PositiveFloat | None = None


class EntryRead(BaseModel):
    """One exercise entry as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    exercise_id: int
    position: int

    sets: int | None
    reps: int | None
    weight: float | None
    weight_unit: str | None

    duration_seconds: int | None
    distance_meters: float | None
    pace_seconds_per_km: float | None


class SessionCreate(BaseModel):
    """Input for ``POST /sessions``.

    ``date`` defaults to today when omitted and must not be in the future.
    ``entries`` may be omitted (empty session) or carry the full list to
    create in one request.
    """

    model_config = ConfigDict(extra="ignore")

    date: date_type = Field(default_factory=date_type.today)
    notes: str | None = None
    entries: list[EntryCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _reject_future_date(self) -> SessionCreate:
        if self.date > date_type.today():
            raise ValueError("date must not be in the future")
        return self


class SessionRead(BaseModel):
    """A workout session with its ordered entries."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    notes: str | None
    entries: list[EntryRead]


# --- Workout history / listing (issue #10) ----------------------------------

#: Default and maximum ``page_size`` for ``GET /sessions``.
SESSIONS_PAGE_SIZE_DEFAULT = 20
SESSIONS_PAGE_SIZE_MAX = 100


class SessionSummary(BaseModel):
    """One session as it appears in the history list."""

    id: int
    date: date_type
    #: Number of distinct exercises logged in the session.
    exercise_count: int
    #: Up to 3 exercise names, most entries first then name ascending.
    primary_lifts: list[str]


class SessionList(BaseModel):
    """A page of :class:`SessionSummary` items plus pagination metadata."""

    items: list[SessionSummary]
    page: int
    page_size: int
    #: Total sessions matching the (optional) date filter, across all pages.
    total: int


# --- Goals (issue #12) -----------------------------------------------------


class GoalCreate(BaseModel):
    """Input for ``POST /exercises/{exercise_id}/goals``.

    ``target_value`` must be a positive number (zero, negative and non-numeric
    are rejected here with 422). Whether ``metric`` is valid for the exercise's
    category is checked in the router, where the ``Exercise`` row is available.
    """

    model_config = ConfigDict(extra="ignore")

    metric: str
    target_value: PositiveFloat
    unit: str | None = None
    description: str | None = None


class GoalUpdate(BaseModel):
    """Input for ``PATCH /goals/{id}``: every field is optional.

    Only the fields present in the request body are applied. ``metric`` and
    ``exercise_id`` are fixed once a goal is created and are not part of this
    model.
    """

    model_config = ConfigDict(extra="ignore")

    target_value: PositiveFloat | None = None
    unit: str | None = None
    description: str | None = None


class GoalRead(BaseModel):
    """One goal as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    exercise_id: int
    metric: str
    target_value: float
    unit: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime
