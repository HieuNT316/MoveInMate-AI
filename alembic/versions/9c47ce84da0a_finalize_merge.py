"""finalize migration tree consolidation

Revision ID: 9c47ce84da0a
Revises: 0fa843848af8

No-op migration. Lang duy tri tien trinh da merge thanh cong.
Chi ton tai de cay Alembic chi con 1 head.

DB hien dang o: 0fa843848af8
Cac revision con lai:
- 77c7b4d4a1a5: da cham dut (replaced by 06882dad3f88)
- Cac revision khac: da duoc merge vao 0fa843848af8
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "9c47ce84da0a"
down_revision: Union[str, Sequence[str], None] = "0fa843848af8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op."""
    pass


def downgrade() -> None:
    """No-op."""
    pass
