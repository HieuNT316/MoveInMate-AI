"""create_phase2_tables

Revision ID: 8f3a1c2e4b5d
Revises: ddfa7af31680
Create Date: 2026-08-25 12:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = '8f3a1c2e4b5d'
down_revision = 'ddfa7af31680'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # push_subscriptions
    op.create_table(
        'push_subscriptions',
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.String(length=500), nullable=False),
        sa.Column('p256dh', sa.String(length=256), nullable=False),
        sa.Column('auth', sa.String(length=128), nullable=False),
        sa.Column('user_agent', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('subscription_id'),
        sa.UniqueConstraint('endpoint')
    )
    op.create_index('idx_push_subscriptions_user', 'push_subscriptions', ['user_id'])

    # roles
    op.create_table(
        'roles',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('role_name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('role_id'),
        sa.UniqueConstraint('role_name')
    )

    # permissions
    op.create_table(
        'permissions',
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.Column('permission_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('permission_id'),
        sa.UniqueConstraint('permission_name')
    )

    # role_permissions
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.role_id']),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.permission_id']),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    # departments
    op.create_table(
        'departments',
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('lead_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('department_id')
    )

    # staff_assignments
    op.create_table(
        'staff_assignments',
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['department_id'], ['departments.department_id']),
        sa.PrimaryKeyConstraint('assignment_id'),
        sa.UniqueConstraint('user_id', 'department_id')
    )

    # tickets
    op.create_table(
        'tickets',
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='open', nullable=True),
        sa.Column('priority', sa.String(length=20), server_default='normal', nullable=True),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.user_id']),
        sa.PrimaryKeyConstraint('ticket_id')
    )
    op.create_index('idx_tickets_user', 'tickets', ['user_id'])
    op.create_index('idx_tickets_status', 'tickets', ['status'])
    op.create_index('idx_tickets_assigned', 'tickets', ['assigned_to'])

    # ticket_messages
    op.create_table(
        'ticket_messages',
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('sender_type', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.ticket_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('message_id')
    )
    op.create_index('idx_messages_ticket', 'ticket_messages', ['ticket_id'])

    # notifications
    op.create_table(
        'notifications',
        sa.Column('notification_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('is_read', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('notification_id')
    )
    op.create_index('idx_notifications_user', 'notifications', ['user_id', 'is_read', 'created_at'])

    # audit_log
    op.create_table(
        'audit_log',
        sa.Column('audit_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('audit_id')
    )

    # user_badges
    op.create_table(
        'user_badges',
        sa.Column('badge_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('badge_key', sa.String(length=50), nullable=False),
        sa.Column('earned_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('badge_id'),
        sa.UniqueConstraint('user_id', 'badge_key')
    )

    # usage_logs (cost tracking)
    op.create_table(
        'usage_logs',
        sa.Column('log_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('operation', sa.String(length=50), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(10, 6), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('log_id')
    )

    # Add department_id column to existing users table
    # Note: 'role' column already exists in users from bc8e9803f056_create_core_tables
    op.add_column('users', sa.Column('department_id', sa.Integer(), nullable=True))

    # Add version and assigned_to columns to applications for optimistic locking
    # Check if applications table exists (may not exist if branched migration downgraded it)
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'applications')"
    ))
    applications_exists = result.scalar()

    if applications_exists:
        op.add_column('applications', sa.Column('version', sa.Integer(), server_default='1', nullable=True))
        op.add_column('applications', sa.Column('assigned_to', sa.Integer(), nullable=True))
        op.create_index('idx_applications_assigned', 'applications', ['assigned_to'])


def downgrade() -> None:
    # Reverse all changes
    # Use if_exists=True because other migrations in branched chains may have
    # already modified or dropped these objects

    # Check if applications table exists before dropping columns
    # (it may have been dropped by a branched migration's downgrade)
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'applications')"
    ))
    applications_exists = result.scalar()

    if applications_exists:
        op.drop_index('idx_applications_assigned', 'applications', if_exists=True)
        op.drop_column('applications', 'assigned_to', if_exists=True)
        op.drop_column('applications', 'version', if_exists=True)

    op.drop_table('usage_logs', if_exists=True)
    op.drop_table('user_badges', if_exists=True)
    op.drop_table('audit_log', if_exists=True)
    op.drop_index('idx_notifications_user', 'notifications', if_exists=True)
    op.drop_table('notifications', if_exists=True)
    op.drop_index('idx_messages_ticket', 'ticket_messages', if_exists=True)
    op.drop_table('ticket_messages', if_exists=True)
    op.drop_index('idx_tickets_assigned', 'tickets', if_exists=True)
    op.drop_index('idx_tickets_status', 'tickets', if_exists=True)
    op.drop_index('idx_tickets_user', 'tickets', if_exists=True)
    op.drop_table('tickets', if_exists=True)
    # Drop staff_assignments BEFORE departments (FK dependency)
    op.drop_table('staff_assignments', if_exists=True)
    op.drop_table('departments', if_exists=True)
    op.drop_table('role_permissions', if_exists=True)
    op.drop_table('permissions', if_exists=True)
    op.drop_table('roles', if_exists=True)
    op.drop_index('idx_push_subscriptions_user', 'push_subscriptions', if_exists=True)
    op.drop_table('push_subscriptions', if_exists=True)
    op.drop_column('users', 'department_id', if_exists=True)
