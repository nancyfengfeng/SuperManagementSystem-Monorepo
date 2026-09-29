"""add created_at

Revision ID: 2a0d45bd2886
Revises: f1dd7e628c51
Create Date: 2026-06-07 09:59:57.992989

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = '2a0d45bd2886'
down_revision: Union[str, Sequence[str], None] = 'f1dd7e628c51'
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.add_column(
        'expenses',
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP")
        )
    )

    op.add_column(
        'incomes',
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP")
        )
    )


def downgrade() -> None:

    op.drop_column('incomes', 'created_at')
    op.drop_column('expenses', 'created_at')