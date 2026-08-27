"""merge Phase 2 tables into main branch

Revision ID: 0fa843848af8
Revises: ('06882dad3f88', '8f3a1c2e4b5d')

Gop 2 heads ve 1:
- 06882dad3f88: form_schema patch (no-op chain tu 2a010744775b)
- 8f3a1c2e4b5d: Phase 2 tables (roles, permissions, departments, tickets, ...)

DB dang dung o 06882dad3f88. Upgrade se tao Phase 2 tables neu chua co.
Downgrade ve 06882dad3f88 se drop Phase 2 tables.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "0fa843848af8"
down_revision: Union[str, Sequence[str], None] = (
    "06882dad3f88",
    "8f3a1c2e4b5d",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Gop - tao Phase 2 tables neu chua co."""
    conn = op.get_bind()

    # Kiem tra bang da ton tai chua
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = 'roles')"
    ))
    if result.scalar():
        return  # Da co, khong lam gi

    # === Tao roles ===
    op.create_table(
        "roles",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("role_name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("role_id"),
        sa.UniqueConstraint("role_name"),
    )

    # === Tao permissions ===
    op.create_table(
        "permissions",
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column("permission_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("permission_id"),
        sa.UniqueConstraint("permission_name"),
    )

    # === Tao role_permissions ===
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.role_id"]),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.permission_id"]),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    # === Them department_id vao users ===
    op.add_column("users", sa.Column("department_id", sa.Integer(), nullable=True))
    op.create_index("idx_users_department", "users", ["department_id"])

    # === Them assigned_to, version vao applications ===
    op.add_column("applications", sa.Column("assigned_to", sa.Integer(), nullable=True))
    op.add_column("applications", sa.Column("version", sa.Integer(), nullable=True, server_default="1"))
    op.create_index("idx_applications_assigned", "applications", ["assigned_to"])

    # === Tao departments ===
    op.create_table(
        "departments",
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("lead_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("department_id"),
    )

    # === Tao staff_assignments ===
    op.create_table(
        "staff_assignments",
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["department_id"], ["departments.department_id"]),
        sa.PrimaryKeyConstraint("assignment_id"),
        sa.UniqueConstraint("user_id", "department_id"),
    )
    op.create_index("idx_staff_user", "staff_assignments", ["user_id"])
    op.create_index("idx_staff_dept", "staff_assignments", ["department_id"])

    # === Tao push_subscriptions ===
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(length=500), nullable=False),
        sa.Column("p256dh", sa.String(length=100), nullable=False),
        sa.Column("auth", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
    )
    op.create_index("idx_push_user", "push_subscriptions", ["user_id"])

    # === Tao tickets ===
    op.create_table(
        "tickets",
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("assigned_to", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("ticket_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.user_id"], ondelete="SET NULL"),
    )
    op.create_index("idx_tickets_user", "tickets", ["user_id"])
    op.create_index("idx_tickets_status", "tickets", ["status"])
    op.create_index("idx_tickets_assigned", "tickets", ["assigned_to"])

    # === Tao ticket_messages ===
    op.create_table(
        "ticket_messages",
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=True),
        sa.Column("sender_type", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("message_id"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.ticket_id"], ondelete="CASCADE"),
    )
    op.create_index("idx_messages_ticket", "ticket_messages", ["ticket_id"])

    # === Tao notifications ===
    op.create_table(
        "notifications",
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("data", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("notification_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
    )
    op.create_index("idx_notifications_user", "notifications", ["user_id", "is_read", "created_at"])

    # === Tao audit_log ===
    op.create_table(
        "audit_log",
        sa.Column("audit_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("old_value", JSONB(), nullable=True),
        sa.Column("new_value", JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("audit_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="SET NULL"),
    )
    op.create_index("idx_audit_resource", "audit_log", ["resource_type", "resource_id"])

    # === Tao user_badges ===
    op.create_table(
        "user_badges",
        sa.Column("badge_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("badge_key", sa.String(length=50), nullable=False),
        sa.Column("earned_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("badge_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
    )
    op.create_index("idx_badges_user", "user_badges", ["user_id"])

    # === Tao usage_logs ===
    op.create_table(
        "usage_logs",
        sa.Column("log_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("log_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="SET NULL"),
    )
    op.create_index("idx_usage_user", "usage_logs", ["user_id"])


def downgrade() -> None:
    """Rollback Phase 2 tables theo dung dependency order."""
    op.drop_index("idx_usage_user", table_name="usage_logs")
    op.drop_table("usage_logs", if_exists=True)
    op.drop_index("idx_badges_user", table_name="user_badges")
    op.drop_table("user_badges", if_exists=True)
    op.drop_index("idx_audit_resource", table_name="audit_log")
    op.drop_table("audit_log", if_exists=True)
    op.drop_index("idx_notifications_user", table_name="notifications")
    op.drop_table("notifications", if_exists=True)
    op.drop_index("idx_messages_ticket", table_name="ticket_messages")
    op.drop_table("ticket_messages", if_exists=True)
    op.drop_index("idx_tickets_assigned", table_name="tickets")
    op.drop_index("idx_tickets_status", table_name="tickets")
    op.drop_index("idx_tickets_user", table_name="tickets")
    op.drop_table("tickets", if_exists=True)
    op.drop_index("idx_push_user", table_name="push_subscriptions")
    op.drop_table("push_subscriptions", if_exists=True)
    op.drop_index("idx_staff_dept", table_name="staff_assignments")
    op.drop_index("idx_staff_user", table_name="staff_assignments")
    op.drop_table("staff_assignments", if_exists=True)
    op.drop_table("departments", if_exists=True)
    op.drop_index("idx_applications_assigned", table_name="applications")
    op.drop_column("applications", "version")
    op.drop_column("applications", "assigned_to")
    op.drop_index("idx_users_department", table_name="users")
    op.drop_column("users", "department_id")
    op.drop_table("role_permissions", if_exists=True)
    op.drop_table("permissions", if_exists=True)
    op.drop_table("roles", if_exists=True)
