"""add form_schema and form_data JSONB columns

Revision ID: 2a010744775b
Revises: c61901e1d717
Create Date: 2026-08-19 22:34:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '2a010744775b'
down_revision: Union[str, Sequence[str], None] = 'c61901e1d717'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "checklist_items",
        sa.Column("form_schema", JSONB, nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("form_data", JSONB, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("applications", "form_data")
    op.drop_column("checklist_items", "form_schema")
