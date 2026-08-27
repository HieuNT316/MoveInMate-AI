"""patch missing form_schema column in checklist_items

Revision ID: 77c7b4d4a1a5
Revises: a2e57ae6de6e
Create Date: 2026-08-28

DB đang đứng ở `a2e57ae6de6e` nhưng thiếu cột `checklist_items.form_schema`.
Cột này được tạo bởi `2a010744775b` — nhánh song song chưa được áp lên.

Migration này chỉ bổ sung cột còn thiếu. Không merge đầy đủ 3 nhánh
vì `8f3a1c2e4b5d` sẽ DROP bảng `applications` — bảng này được tạo bởi
`44325ddaac94` (TRƯỚC branchpoint), không thuộc phạm vi merge.

Sau khi chạy xong, cây vẫn có 2 heads. Gộp bằng `alembic merge`.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "77c7b4d4a1a5"
down_revision: Union[str, Sequence[str], None] = "a2e57ae6de6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Bổ sung cột form_schema còn thiếu."""
    op.add_column(
        "checklist_items",
        sa.Column("form_schema", JSONB, nullable=True),
    )


def downgrade() -> None:
    """Rollback — chỉ chạy khi chắc chắn chưa có dữ liệu."""
    op.drop_column("checklist_items", "form_schema")
