"""create goals table

Revision ID: 2a26dd45dcb9
Revises: 5a56b6194cbe
Create Date: 2026-09-03 21:33:39.143376

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a26dd45dcb9'
down_revision: Union[str, Sequence[str], None] = '5a56b6194cbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_updated_at_trigger(table: str) -> None:
    """BEFORE UPDATE trigger keeping ``table.updated_at`` current.

    Same pattern as 6581509bfa2a / 5a56b6194cbe: ``clock_timestamp()`` rather
    than ``now()`` so an insert and a later update in one transaction (the
    rollback-per-test fixture) get distinct timestamps.
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
        'goals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('metric', sa.String(), nullable=False),
        sa.Column(
            'target_value', sa.Numeric(precision=10, scale=2), nullable=False
        ),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ['exercise_id'], ['exercises.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_goals_exercise_id', 'goals', ['exercise_id'])
    _create_updated_at_trigger('goals')


def downgrade() -> None:
    """Downgrade schema."""
    _drop_updated_at_trigger('goals')
    op.drop_index('ix_goals_exercise_id', table_name='goals')
    op.drop_table('goals')
