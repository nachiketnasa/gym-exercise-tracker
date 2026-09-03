"""initial empty baseline

Revision ID: 2a34eeef0e9d
Revises: 
Create Date: 2026-09-03 19:34:18.849575

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a34eeef0e9d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Baseline revision — intentionally empty. Real tables arrive in #5 and #8."""


def downgrade() -> None:
    """Baseline revision — intentionally empty."""
