"""add embed status

Revision ID: c61901e1d717
Revises: 0541910c4dcc
Create Date: 2026-08-19 00:27:26.029881

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c61901e1d717'
down_revision: Union[str, Sequence[str], None] = '0541910c4dcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("documents", sa.Column("embed_status", sa.String(length=20)))
    op.execute("UPDATE documents SET embed_status = 'ready'")
    op.alter_column(
        "documents",
        "embed_status",
        nullable=False,
        server_default="ready",
        existing_type=sa.String(length=20),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("documents", "embed_status")
