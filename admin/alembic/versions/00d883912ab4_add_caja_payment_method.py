"""add caja payment method

Revision ID: 00d883912ab4
Revises: 4008fa146ddb
Create Date: 2026-06-14 04:32:25.099208

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00d883912ab4'
down_revision: Union[str, Sequence[str], None] = '4008fa146ddb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():

    op.create_check_constraint(

        "ck_expense_method_valid",

        "expense_payments",

        "method IN ('cash','card','sinpe','caja')"

    )

def downgrade():

    op.drop_constraint(

        "ck_expense_method_valid",

        "expense_payments",

        type_="check"

    )