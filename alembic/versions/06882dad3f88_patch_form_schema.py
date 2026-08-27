"""patch missing form_schema column in checklist_items

Revision ID: 06882dad3f88
Revises: 2a010744775b

DB đang đứng ở 2a010744775b sau khi upgrade head.
Cột form_schema đã tồn tại trên DB từ revision này.

Migration này là NO-OP — không làm gì cả.
Nó chỉ dùng để gộp 3 heads về 1.

Sau khi có migration này:
  alembic heads   # chỉ còn 1 head: 06882dad3f88
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "06882dad3f88"
down_revision: Union[str, Sequence[str], None] = "2a010744775b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op — cột đã tồn tại từ 2a010744775b."""
    pass


def downgrade() -> None:
    """No-op."""
    pass
