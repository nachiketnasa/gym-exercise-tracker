"""Goals API (issue #12).

A goal is one target value for one metric of one exercise. Endpoints:

* ``POST   /exercises/{exercise_id}/goals`` - create a goal
* ``GET    /exercises/{exercise_id}/goals`` - list an exercise's goals, newest first
* ``GET    /goals/{goal_id}``               - read one goal
* ``PATCH  /goals/{goal_id}``               - update target_value / unit / description
* ``DELETE /goals/{goal_id}``               - remove a goal (204)

Validation contract (shared with the rest of the API): unknown ids return 404,
bad input returns 422. The allowed ``metric`` vocabulary comes from
``app.metrics`` and depends on the exercise's category. Multiple goals per
exercise are allowed, including several on the same metric - no create is
rejected as a duplicate.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import current_user
from app.metrics import ALL_METRICS, is_valid_metric, metrics_for_category
from app.models import Exercise, Goal, User
from app.schemas import GoalCreate, GoalRead, GoalUpdate

router = APIRouter(tags=["goals"])


def _not_found(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status_code=422, detail=message)


def _load_exercise(session: Session, exercise_id: int) -> Exercise:
    exercise = session.get(Exercise, exercise_id)
    if exercise is None:
        raise _not_found(f"Exercise {exercise_id} not found")
    return exercise


def _load_goal(
    session: Session, goal_id: int, *, user_id: int | None = None
) -> Goal:
    goal = session.get(Goal, goal_id)
    if goal is None or (user_id is not None and goal.user_id != user_id):
        raise _not_found(f"Goal {goal_id} not found")
    return goal


def _check_metric(metric: str, category: str) -> None:
    """422 if ``metric`` is unknown or not valid for ``category``."""
    if metric not in ALL_METRICS:
        raise _unprocessable(
            f"unknown metric {metric!r}; expected one of {sorted(ALL_METRICS)}"
        )
    if not is_valid_metric(category, metric):
        raise _unprocessable(
            f"metric {metric!r} is not valid for a {category} exercise; "
            f"expected one of {list(metrics_for_category(category))}"
        )


@router.post(
    "/exercises/{exercise_id}/goals",
    response_model=GoalRead,
    status_code=status.HTTP_201_CREATED,
    tags=["exercises"],
)
def create_goal(
    exercise_id: int,
    payload: GoalCreate,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> Goal:
    exercise = _load_exercise(session, exercise_id)
    _check_metric(payload.metric, exercise.category)

    goal = Goal(
        exercise_id=exercise_id,
        user_id=user.id,
        metric=payload.metric,
        target_value=payload.target_value,
        unit=payload.unit,
        description=payload.description,
    )
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return goal


@router.get(
    "/exercises/{exercise_id}/goals",
    response_model=list[GoalRead],
    tags=["exercises"],
)
def list_goals(
    exercise_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> list[Goal]:
    _load_exercise(session, exercise_id)
    return list(
        session.scalars(
            select(Goal)
            .where(Goal.exercise_id == exercise_id, Goal.user_id == user.id)
            .order_by(Goal.created_at.desc(), Goal.id.desc())
        )
    )


@router.get("/goals/{goal_id}", response_model=GoalRead)
def get_goal(
    goal_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
) -> Goal:
    return _load_goal(session, goal_id, user_id=user.id)


@router.patch("/goals/{goal_id}", response_model=GoalRead)
def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    session: Session = Depends(get_session),
) -> Goal:
    goal = _load_goal(session, goal_id)
    updates = payload.model_dump(exclude_unset=True)
    if updates:
        for name, value in updates.items():
            setattr(goal, name, value)
        session.commit()
        session.refresh(goal)
    return goal


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int, session: Session = Depends(get_session)
) -> Response:
    goal = _load_goal(session, goal_id)
    session.delete(goal)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
