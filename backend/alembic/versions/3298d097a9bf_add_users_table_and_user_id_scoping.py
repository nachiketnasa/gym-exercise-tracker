"""add users table and user_id scoping

Single-user scoping stub (issue #14).

* Creates the ``users`` table (with the standard ``updated_at`` BEFORE UPDATE
  trigger, same pattern as ``2a26dd45dcb9``).
* Inserts the one seeded local user with a well-known id (``1`` /
  ``local@example.com``) — kept in sync with ``app.users.SEED_USER``.
* Adds a non-null ``user_id`` FK to ``workout_sessions`` and ``goals``. Both
  are added nullable, every pre-existing row is backfilled with the seeded
  user's id, then the column is altered to NOT NULL.

Tables NOT touched: ``exercises`` and ``exercise_entries`` are not user-owned
(the exercise library is shared; an entry is owned transitively through its
session).

Revision ID: 3298d097a9bf
Revises: 2a26dd45dcb9
Create Date: 2026-09-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3298d097a9bf'
down_revision: Union[str, Sequence[str], None] = '2a26dd45dcb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: Well-known local user — mirrors ``app.users.SEED_USER``.
_SEED_USER_ID = 1
_SEED_USER_EMAIL = "local@example.com"
_SEED_USER_NAME = "Local User"


def _create_updated_at_trigger(table: str) -> None:
    """BEFORE UPDATE trigger keeping ``table.updated_at`` current.

    Same pattern as 2a26dd45dcb9: ``clock_timestamp()`` rather than ``now()``
    so an insert and a later update in one transaction get distinct timestamps.
    """
    op.execute(
        f"""
        CREATE FUNCTION {table}_set_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = clock_timestamp();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {table}_set_updated_at
        BEFORE UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION {table}_set_updated_at()
        """
    )


def _drop_updated_at_trigger(table: str) -> None:
    op.execute(f'DROP TRIGGER IF EXISTS {table}_set_updated_at ON {table}')
    op.execute(f'DROP FUNCTION IF EXISTS {table}_set_updated_at()')


def _add_user_id(table: str) -> None:
    """Add a non-null ``user_id`` FK to ``table``, backfilling existing rows."""
    op.add_column(
        table, sa.Column('user_id', sa.Integer(), nullable=True)
    )
    op.execute(
        sa.text(
            f'UPDATE {table} SET user_id = :uid WHERE user_id IS NULL'
        ).bindparams(uid=_SEED_USER_ID)
    )
    op.alter_column(table, 'user_id', nullable=False)
    op.create_index(f'ix_{table}_user_id', table, ['user_id'])
    op.create_foreign_key(
        f'fk_{table}_user_id_users',
        table,
        'users',
        ['user_id'],
        ['id'],
        ondelete='RESTRICT',
    )


def _drop_user_id(table: str) -> None:
    op.drop_constraint(f'fk_{table}_user_id_users', table, type_='foreignkey')
    op.drop_index(f'ix_{table}_user_id', table_name=table)
    op.drop_column(table, 'user_id')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    _create_updated_at_trigger('users')

    # Seed the one local user with its well-known id, then move the identity
    # sequence past it so future inserts do not collide.
    op.execute(
        sa.text(
            "INSERT INTO users (id, email, name) VALUES (:id, :email, :name)"
        ).bindparams(
            id=_SEED_USER_ID, email=_SEED_USER_EMAIL, name=_SEED_USER_NAME
        )
    )
    op.execute(
        "SELECT setval("
        "pg_get_serial_sequence('users', 'id'), "
        "(SELECT MAX(id) FROM users))"
    )

    _add_user_id('workout_sessions')
    _add_user_id('goals')


def downgrade() -> None:
    """Downgrade schema."""
    _drop_user_id('goals')
    _drop_user_id('workout_sessions')
    _drop_updated_at_trigger('users')
    op.drop_table('users')
