"""create exercises table

Revision ID: 6581509bfa2a
Revises: 2a34eeef0e9d
Create Date: 2026-09-03 20:32:56.464162

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6581509bfa2a'
down_revision: Union[str, Sequence[str], None] = '2a34eeef0e9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'exercises',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column(
            'is_preset',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
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
            "category IN ('strength', 'cardio')", name='ck_exercises_category'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    # Case-insensitive uniqueness on name: a unique index on lower(name).
    op.create_index(
        'ix_exercises_name_lower',
        'exercises',
        [sa.literal_column('lower(name)')],
        unique=True,
    )
    # Postgres has no native ON UPDATE, so keep updated_at current with a
    # BEFORE UPDATE trigger. clock_timestamp() (real wall-clock time), not
    # now()/transaction_timestamp() which is frozen for the whole transaction
    # and so would equal created_at when an insert and a later update share one
    # transaction.
    op.execute(
        """
        CREATE FUNCTION exercises_set_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = clock_timestamp();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER exercises_set_updated_at
        BEFORE UPDATE ON exercises
        FOR EACH ROW EXECUTE FUNCTION exercises_set_updated_at()
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DROP TRIGGER IF EXISTS exercises_set_updated_at ON exercises')
    op.execute('DROP FUNCTION IF EXISTS exercises_set_updated_at()')
    op.drop_index('ix_exercises_name_lower', table_name='exercises')
    op.drop_table('exercises')
