"""Read-only analytics for one exercise: personal records (#11) and the
per-metric progress series (#13).

Both endpoints hang off ``/exercises/{exercise_id}`` and are computed on read
from logged exercise entries - no tables, no migrations. The metric vocabulary
comes from ``app.metrics`` (shared with the Goals API, #12); the calculations
live in the pure-Python modules ``app.prs`` and ``app.progress``.

Validation contract: unknown exercise -> 404, bad query params -> 422.
"""

from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.metrics import ALL_METRICS, is_valid_metric, metrics_for_category
from app.models import Exercise, ExerciseEntry, WorkoutSession
from app.progress import ProgressInput, progress_series
from app.prs import PRInput, calculate_prs
from app.schemas import PRRead, ProgressPointRead

router = APIRouter(prefix="/exercises", tags=["analytics"])

_ENTRY_COLUMNS = (
    ExerciseEntry.id,
    ExerciseEntry.session_id,
    WorkoutSession.date,
    ExerciseEntry.weight,
    ExerciseEntry.reps,
    ExerciseEntry.distance_meters,
    ExerciseEntry.duration_seconds,
    ExerciseEntry.pace_seconds_per_km,
)


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status_code=422, detail=message)


def _load_exercise(session: Session, exercise_id: int) -> Exercise:
    exercise = session.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise {exercise_id} not found",
        )
    return exercise


def _entry_rows(
    session: Session,
    exercise_id: int,
    *,
    start: date_type | None = None,
    end: date_type | None = None,
):
    stmt = (
        select(*_ENTRY_COLUMNS)
        .join(WorkoutSession, ExerciseEntry.session_id == WorkoutSession.id)
        .where(ExerciseEntry.exercise_id == exercise_id)
    )
    if start is not None:
        stmt = stmt.where(WorkoutSession.date >= start)
    if end is not None:
        stmt = stmt.where(WorkoutSession.date <= end)
    return session.execute(stmt).all()


@router.get("/{exercise_id}/prs", response_model=list[PRRead])
def get_prs(
    exercise_id: int, session: Session = Depends(get_session)
) -> list:
    """Personal records for the exercise, one per metric of its category."""
    exercise = _load_exercise(session, exercise_id)
    entries = [
        PRInput(
            entry_id=row.id,
            session_id=row.session_id,
            session_date=row.date,
            weight=row.weight,
            reps=row.reps,
            distance_meters=row.distance_meters,
            duration_seconds=row.duration_seconds,
            pace_seconds_per_km=row.pace_seconds_per_km,
        )
        for row in _entry_rows(session, exercise_id)
    ]
    return calculate_prs(exercise.category, entries)


@router.get("/{exercise_id}/progress", response_model=list[ProgressPointRead])
def get_progress(
    exercise_id: int,
    metric: str = Query(..., description="A metric valid for the exercise's category"),
    start: date_type | None = Query(None),
    end: date_type | None = Query(None),
    session: Session = Depends(get_session),
) -> list:
    """Date-ascending ``{date, value}`` points for one metric of the exercise."""
    exercise = _load_exercise(session, exercise_id)

    if not is_valid_metric(exercise.category, metric):
        if metric not in ALL_METRICS:
            raise _unprocessable(
                f"unknown metric {metric!r}; expected one of {sorted(ALL_METRICS)}"
            )
        raise _unprocessable(
            f"metric {metric!r} is not valid for a {exercise.category} exercise; "
            f"expected one of {list(metrics_for_category(exercise.category))}"
        )

    if start is not None and end is not None and start > end:
        raise _unprocessable("'start' must not be later than 'end'")

    entries = [
        ProgressInput(
            session_date=row.date,
            weight=row.weight,
            reps=row.reps,
            distance_meters=row.distance_meters,
            duration_seconds=row.duration_seconds,
            pace_seconds_per_km=row.pace_seconds_per_km,
        )
        for row in _entry_rows(session, exercise_id, start=start, end=end)
    ]
    return progress_series(metric, entries)
