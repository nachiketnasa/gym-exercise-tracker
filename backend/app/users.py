"""The single seeded local user (issue #14).

The app is single-user for now. Exactly one row exists in ``users`` - the
"local" user defined by :data:`SEED_USER` - and every user-owned row points at
it. :func:`ensure_seed_user` inserts that row idempotently; it is safe to call
on every app startup and from tests.

The migration that creates the ``users`` table inserts the same row (with the
same well-known id) so a freshly migrated database already has it; this helper
is the re-runnable seed and the safety net for a database where the row was
removed.

``user_id`` columns on the user-owned models default to :data:`SEED_USER_ID`,
so code (and existing tests) that build those rows without naming an owner
still get the local user.

Authentication (#27) will replace the ``current_user`` dependency in
:mod:`app.deps`; this seed and model stay.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

#: Well-known id of the local user. The create-users migration inserts this id
#: explicitly and the user-owned models use it as their ``user_id`` default, so
#: it is stable across every environment.
SEED_USER_ID = 1

#: The one local user. ``email`` is the stable lookup key used everywhere.
SEED_USER: dict[str, object] = {
    "id": SEED_USER_ID,
    "email": "local@example.com",
    "name": "Local User",
}


def ensure_seed_user(session: Session):
    """Return the seeded local user, creating it if the row is missing.

    Idempotent: matched by :data:`SEED_USER` email, so running it twice leaves
    exactly one such user and never raises a unique-constraint error. The
    caller owns the session lifecycle; this commits its own insert.
    """
    from app.models import User

    user = session.scalar(select(User).where(User.email == SEED_USER["email"]))
    if user is None:
        user = User(
            id=SEED_USER["id"],
            email=SEED_USER["email"],
            name=SEED_USER["name"],
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user
