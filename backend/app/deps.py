"""Shared FastAPI dependencies.

:func:`current_user` resolves the user that owns the rows an endpoint creates
or reads. The app is single-user for now (#14), so it always returns the
seeded local user. It is a plain dependency on purpose: #27 swaps this one
function for a request-scoped implementation (session cookie / token) without
touching a single call site.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.users import ensure_seed_user


def current_user(session: Session = Depends(get_session)) -> User:
    """The user owning this request's data - the seeded local user for now.

    Looks the user up by the well-known seed email and creates it if missing,
    so a freshly created database (or one where the row was removed) still
    works.
    """
    return ensure_seed_user(session)
