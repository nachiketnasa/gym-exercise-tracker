"""Exercise endpoints: list all, fetch one, create a custom exercise.

Presets are created only by the seed (issue #6); this router never sets
``is_preset``, so everything created here is a custom exercise. Editing and
deleting are out of scope (issue #26).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Exercise
from app.schemas import ExerciseCreate, ExerciseRead

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("", response_model=list[ExerciseRead])
def list_exercises(session: Session = Depends(get_session)) -> list[Exercise]:
    """Return every exercise (presets and custom), ordered by name."""
    return list(session.scalars(select(Exercise).order_by(Exercise.name.asc())))


@router.get("/{exercise_id}", response_model=ExerciseRead)
def get_exercise(
    exercise_id: int, session: Session = Depends(get_session)
) -> Exercise:
    """Return one exercise by id, or 404 if it does not exist."""
    exercise = session.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise {exercise_id} not found",
        )
    return exercise


@router.post("", response_model=ExerciseRead, status_code=status.HTTP_201_CREATED)
def create_exercise(
    payload: ExerciseCreate, session: Session = Depends(get_session)
) -> Exercise:
    """Create a custom exercise.

    Returns 409 (never a 500 from the DB unique index) when an exercise with
    the same name already exists, case-insensitively, whether preset or custom.
    """
    name = payload.name  # already trimmed by the schema

    existing = session.scalar(
        select(Exercise.id).where(func.lower(Exercise.name) == name.lower())
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An exercise named {name!r} already exists",
        )

    exercise = Exercise(name=name, category=payload.category, is_preset=False)
    session.add(exercise)
    try:
        session.commit()
    except IntegrityError:  # concurrent insert raced us to the same name
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An exercise named {name!r} already exists",
        ) from None
    session.refresh(exercise)
    return exercise
