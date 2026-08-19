"""add partial unique index on open applications

Revision ID: a2e57ae6de6e
Revises: c61901e1d717
Create Date: 2026-08-19 01:04:14.532045

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2e57ae6de6e'
down_revision: Union[str, Sequence[str], None] = 'c61901e1d717'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Chốt chặn ở tầng DB cho quy tắc "một hồ sơ đang mở cho mỗi mục checklist"
    # (xem get_open_application trong src/services/store.py). Trước khi tạo unique
    # index, đóng các hồ sơ trùng đang mở nếu có — CREATE UNIQUE INDEX sẽ thất bại
    # nếu dữ liệu hiện có đã vi phạm, và migration chạy lúc container khởi động
    # nên lỗi ở đây làm cả service crash-loop. Giữ lại bản ghi mới nhất (theo
    # created_at, application_id), các bản trùng còn lại chuyển sang 'rejected'
    # kèm bql_note giải thích — đây là trạng thái ĐÓNG hợp lệ, không phải bịa
    # thêm trạng thái mới.
    op.execute(
        """
        UPDATE applications
        SET status = 'rejected',
            bql_note = 'Tự động đóng: trùng hồ sơ đang mở khác cho cùng thủ tục '
                       '(dọn dữ liệu khi thêm ràng buộc chống nộp trùng).'
        WHERE application_id IN (
            SELECT application_id FROM (
                SELECT
                    application_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_id, checklist_item_id
                        ORDER BY created_at DESC, application_id DESC
                    ) AS rn
                FROM applications
                WHERE status NOT IN ('delivered', 'rejected')
            ) ranked
            WHERE rn > 1
        )
        """
    )
    op.create_index(
        "uq_open_application_per_item",
        "applications",
        ["user_id", "checklist_item_id"],
        unique=True,
        postgresql_where=sa.text("status NOT IN ('delivered', 'rejected')"),
        sqlite_where=sa.text("status NOT IN ('delivered', 'rejected')"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_open_application_per_item", table_name="applications")
