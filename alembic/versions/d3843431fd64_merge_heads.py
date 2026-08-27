"""merge final alembic heads into one

Revision ID: d3843431fd64
Revises: ('77c7b4d4a1a5', '9c47ce84da0a')

Gop 2 heads cuoi cung ve 1:
- 77c7b4d4a1a5: patch form_schema (chain tu a2e57ae6de6e)
- 9c47ce84da0a: finalize merge (chain tu 0fa843848af8)

DB da o 9c47ce84da0a. Khong can lam gi them.
Migration nay chi la anchor de dong cua cay.
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "d3843431fd64"
down_revision: Union[str, Sequence[str], None] = (
    "77c7b4d4a1a5",
    "9c47ce84da0a",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op."""
    pass


def downgrade() -> None:
    """No-op."""
    pass
