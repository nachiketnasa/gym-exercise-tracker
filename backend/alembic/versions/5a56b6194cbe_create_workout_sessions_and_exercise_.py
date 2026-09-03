"""create workout_sessions and exercise_entries

Revision ID: 5a56b6194cbe
Revises: 6581509bfa2a
Create Date: 2026-09-03 21:16:39.199682

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a56b6194cbe'
down_revision: Union[str, Sequence[str], None] = '6581509bfa2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_updated_at_trigger(table: str) -> None:
    """Keep ``table.updated_at`` current with a BEFORE UPDATE trigger.

    Mirrors ``6581509bfa2a`` (the exercises table): Postgres has no native
    ON UPDATE, and ``clock_timestamp()`` (real wall-clock time) is used rather
    than ``now()``/``transaction_timestamp()``, which is frozen for the whole
    transaction and so would equal ``created_at`` when an insert and a later
    update share one transaction (as they do in the rollback-per-test fixture).
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


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'workout_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
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
    )
    op.create_table(
        'exercise_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.SmallInteger(), nullable=False),
        # Strength metrics (all nullable).
        sa.Column('sets', sa.Integer(), nullable=True),
        sa.Column('reps', sa.Integer(), nullable=True),
        sa.Column('weight', sa.Numeric(precision=7, scale=2), nullable=True),
        sa.Column('weight_unit', sa.Text(), nullable=True),
        # Cardio metrics (all nullable).
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column(
            'distance_meters', sa.Numeric(precision=10, scale=2), nullable=True
        ),
        sa.Column(
            'pace_seconds_per_km',
            sa.Numeric(precision=8, scale=2),
            nullable=True,
        ),
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
        sa.CheckConstraint(
            "weight_unit IN ('kg', 'lb')",
            name='ck_exercise_entries_weight_unit',
        ),
        sa.ForeignKeyConstraint(
            ['session_id'],
            ['workout_sessions.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['exercise_id'],
            ['exercises.id'],
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # Autogenerate does not emit triggers; add them by hand, mirroring
    # 6581509bfa2a.
    _create_updated_at_trigger('workout_sessions')
    _create_updated_at_trigger('exercise_entries')


def downgrade() -> None:
    """Downgrade schema."""
    _drop_updated_at_trigger('exercise_entries')
    _drop_updated_at_trigger('workout_sessions')
    op.drop_table('exercise_entries')
    op.drop_table('workout_sessions')
