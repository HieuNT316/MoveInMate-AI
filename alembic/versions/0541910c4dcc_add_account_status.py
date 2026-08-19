"""add account status

Revision ID: 0541910c4dcc
Revises: 4b4ea98a4e85
Create Date: 2026-08-18 23:31:47.430918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0541910c4dcc'
down_revision: Union[str, Sequence[str], None] = '4b4ea98a4e85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ba bước, không gộp: thêm nullable → backfill → mới khoá NOT NULL.
    op.add_column("users", sa.Column("account_status", sa.String(length=20)))
    op.execute("UPDATE users SET account_status = 'active'")
    op.alter_column(
        "users",
        "account_status",
        nullable=False,
        server_default="active",
        existing_type=sa.String(length=20),
    )


def downgrade() -> None:
    op.drop_column("users", "account_status")
