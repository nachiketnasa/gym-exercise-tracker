"""Workout logging endpoints (issue #9).

Owns session creation and reading plus the exercise-entry sub-resource:

* ``POST /sessions`` - create a session, optionally with all its entries
* ``GET /sessions/{id}`` - read a full session with its ordered entries
* ``POST /sessions/{id}/entries`` - append one entry
* ``PATCH /sessions/{id}/entries/{entry_id}`` - update an entry's metric fields
* ``DELETE /sessions/{id}/entries/{entry_id}`` - remove an entry

``GET /sessions`` (listing/pagination) belongs to #10 and is not here.

Validation contract: bad request bodies return 422, unknown ids return 404.
The category-dependent checks (an entry may only carry the metric fields for
its exercise's category, and must carry the minimum required set) live here
because they need the ``Exercise`` row. The minimum required set is:

* strength: ``sets`` and ``reps``
* cardio: ``duration_seconds`` or ``distance_meters``
"""

from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import current_user
from app.models import Exercise, ExerciseEntry, User, WorkoutSession
from app.schemas import (
    CARDIO_METRIC_FIELDS,
    SESSIONS_PAGE_SIZE_DEFAULT,
    SESSIONS_PAGE_SIZE_MAX,
    STRENGTH_METRIC_FIELDS,
    EntryCreate,
    EntryRead,
    EntryUpdate,
    SessionCreate,
    SessionList,
    SessionRead,
    SessionSummary,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


#: FastAPI's own body-validation failures use 422; the category-dependent
#: checks in this module raise the same status by hand.
HTTP_422 = 422


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status_code=HTTP_422, detail=message)


def _not_found(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


def _load_exercise(session: Session, exercise_id: int) -> Exercise:
    exercise = session.get(Exercise, exercise_id)
    if exercise is None:
        raise _unprocessable(f"exercise {exercise_id} does not exist")
    return exercise


def _validate_metric_fields(
    category: str, values: dict[str, object], *, require_minimum: bool
) -> None:
    """Reject wrong-category metric fields and (optionally) missing required ones.

    ``values`` holds the metric fields the caller supplied (a value of ``None``
    counts as "not supplied").
    """
    wrong = (
        CARDIO_METRIC_FIELDS if category == "strength" else STRENGTH_METRIC_FIELDS
    )
    offending = [name for name in wrong if values.get(name) is not None]
    if offending:
        raise _unprocessable(
            f"{', '.join(sorted(offending))} not valid for a {category} exercise"
        )

    if not require_minimum:
        return

    if category == "strength":
        if values.get("sets") is None or values.get("reps") is None:
            raise _unprocessable("a strength entry requires 'sets' and 'reps'")
    else:
        if (
            values.get("duration_seconds") is None
            and values.get("distance_meters") is None
        ):
            raise _unprocessable(
                "a cardio entry requires 'duration_seconds' or 'distance_meters'"
            )


_METRIC_FIELDS = STRENGTH_METRIC_FIELDS + CARDIO_METRIC_FIELDS


def _build_entry(session: Session, payload: EntryCreate, position: int) -> ExerciseEntry:
    exercise = _load_exercise(session, payload.exercise_id)
    data = payload.model_dump()
    _validate_metric_fields(
        exercise.category,
        {name: data[name] for name in _METRIC_FIELDS},
        require_minimum=True,
    )
    return ExerciseEntry(
        exercise_id=payload.exercise_id,
        position=position,
        **{name: data[name] for name in _METRIC_FIELDS},
    )


def _load_session(
    session: Session, session_id: int, *, user_id: int | None = None
) -> WorkoutSession:
    workout = session.get(WorkoutSession, session_id)
    if workout is None or (user_id is not None and workout.user_id != user_id):
        raise _not_found(f"session {session_id} not found")
    return workout


def _load_entry(
    session: Session, workout: WorkoutSession, entry_id: int
) -> ExerciseEntry:
    entry = session.get(ExerciseEntry, entry_id)
    if entry is None or entry.session_id != workout.id:
        raise _not_found(
            f"entry {entry_id} not found on session {workout.id}"
        )
    return entry


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> WorkoutSession:
    workout = WorkoutSession(
        date=payload.date, notes=payload.notes, user_id=user.id
    )
    for position, entry_payload in enumerate(payload.entries):
        workout.entries.append(_build_entry(session, entry_payload, position))
    session.add(workout)
    session.commit()
    session.refresh(workout)
    return workout


def _summarise(workout: WorkoutSession) -> SessionSummary:
    """Build the history summary for one session from its loaded entries."""
    # exercise_id -> [entry count, exercise name]
    tally: dict[int, list] = {}
    for entry in workout.entries:
        slot = tally.setdefault(entry.exercise_id, [0, entry.exercise.name])
        slot[0] += 1
    # Most entries first, then name ascending; take the top 3 names.
    ordered = sorted(tally.values(), key=lambda pair: (-pair[0], pair[1]))
    return SessionSummary(
        id=workout.id,
        date=workout.date,
        exercise_count=len(tally),
        primary_lifts=[name for _count, name in ordered[:3]],
    )


@router.get("", response_model=SessionList)
def list_sessions(
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(
        SESSIONS_PAGE_SIZE_DEFAULT, ge=1, le=SESSIONS_PAGE_SIZE_MAX
    ),
    start: date_type | None = Query(None),
    end: date_type | None = Query(None),
) -> SessionList:
    """Paginated workout history, newest first, each item a short summary.

    ``page`` defaults to 1 and ``page_size`` to
    ``SESSIONS_PAGE_SIZE_DEFAULT`` (20), capped at ``SESSIONS_PAGE_SIZE_MAX``
    (100). ``start``/``end`` (ISO ``YYYY-MM-DD``) filter by session date,
    inclusive on both ends and each usable alone. Malformed dates are rejected
    by FastAPI with 422; ``start`` later than ``end`` is rejected below.
    """
    if start is not None and end is not None and start > end:
        raise _unprocessable("'start' must not be later than 'end'")

    where = [WorkoutSession.user_id == user.id]
    if start is not None:
        where.append(WorkoutSession.date >= start)
    if end is not None:
        where.append(WorkoutSession.date <= end)

    total = session.scalar(
        select(func.count()).select_from(WorkoutSession).where(*where)
    )

    workouts = (
        session.scalars(
            select(WorkoutSession)
            .where(*where)
            .order_by(
                WorkoutSession.date.desc(),
                WorkoutSession.created_at.desc(),
                WorkoutSession.id.desc(),
            )
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        .unique()
        .all()
    )

    return SessionList(
        items=[_summarise(w) for w in workouts],
        page=page,
        page_size=page_size,
        total=total or 0,
    )


@router.get("/{session_id}", response_model=SessionRead)
def get_session_by_id(
    session_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> WorkoutSession:
    return _load_session(session, session_id, user_id=user.id)


@router.post(
    "/{session_id}/entries",
    response_model=EntryRead,
    status_code=status.HTTP_201_CREATED,
)
def add_entry(
    session_id: int,
    payload: EntryCreate,
    session: Session = Depends(get_session),
) -> ExerciseEntry:
    workout = _load_session(session, session_id)
    next_position = max((e.position for e in workout.entries), default=-1) + 1
    entry = _build_entry(session, payload, next_position)
    workout.entries.append(entry)
    session.commit()
    session.refresh(entry)
    return entry


@router.patch("/{session_id}/entries/{entry_id}", response_model=EntryRead)
def update_entry(
    session_id: int,
    entry_id: int,
    payload: EntryUpdate,
    session: Session = Depends(get_session),
) -> ExerciseEntry:
    workout = _load_session(session, session_id)
    entry = _load_entry(session, workout, entry_id)

    updates = payload.model_dump(exclude_unset=True)
    if updates:
        _validate_metric_fields(
            entry.exercise.category, updates, require_minimum=False
        )
        for name, value in updates.items():
            setattr(entry, name, value)
        session.commit()
        session.refresh(entry)
    return entry


@router.delete(
    "/{session_id}/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_entry(
    session_id: int,
    entry_id: int,
    session: Session = Depends(get_session),
) -> Response:
    workout = _load_session(session, session_id)
    entry = _load_entry(session, workout, entry_id)
    session.delete(entry)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
