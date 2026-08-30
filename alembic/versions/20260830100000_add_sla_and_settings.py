"""them sla_business_days, system_settings va index cho audit_log

Revision ID: e1b7c3d9a204
Revises: d3843431fd64

Ba thay doi phuc vu Report API (docs/superpowers/specs/2026-08-29-report-settings-badge-design.md):

1. `checklist_items.sla_business_days` — thoi han xu ly tinh bang SO NGAY.
   `processing_time` la chuoi hien thi ("1-3 ngay lam viec", "Theo lich nha
   mang") nen khong tinh duoc onTimeRate. NULL = thu tuc khong co SLA cua BQL.

2. `system_settings` — key-value cho cau hinh doc duoc trong report query.
   `setting_key` lam primary key luon, khong them cot id thua.

3. Index tren audit_log(action, created_at) — moi report query deu loc theo
   hai cot nay de lay moc chuyen trang thai ho so.

`user_badges` KHONG tao o day: migration 8f3a1c2e4b5d da tao san.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "e1b7c3d9a204"
down_revision: Union[str, Sequence[str], None] = "d3843431fd64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Cung dinh nghia voi src/models/db.py: JSONB tren Postgres, JSON tren SQLite.
JSONType = sa.JSON().with_variant(JSONB, "postgresql")


def upgrade() -> None:
    op.add_column(
        "checklist_items",
        sa.Column("sla_business_days", sa.Integer(), nullable=True),
    )

    op.create_table(
        "system_settings",
        sa.Column("setting_key", sa.String(length=100), nullable=False),
        sa.Column("setting_value", JSONType, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("setting_key"),
    )

    op.create_index(
        "idx_audit_action_created",
        "audit_log",
        ["action", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_audit_action_created", table_name="audit_log")
    op.drop_table("system_settings")
    op.drop_column("checklist_items", "sla_business_days")
