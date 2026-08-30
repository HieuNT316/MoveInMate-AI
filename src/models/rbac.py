"""RBAC models - Permission enum and role-permission mappings."""

from enum import Enum


class Permission(str, Enum):
    """All available permissions in the system."""

    # Applications
    VIEW_ALL_APPLICATIONS = "view_all_applications"
    VIEW_DEPARTMENT_APPLICATIONS = "view_department_applications"
    VIEW_ASSIGNED_APPLICATIONS = "view_assigned_applications"
    PROCESS_APPLICATION = "process_application"
    APPROVE_APPLICATION = "approve_application"
    BATCH_APPROVE = "batch_approve"

    # Tickets
    VIEW_ALL_TICKETS = "view_all_tickets"
    VIEW_DEPARTMENT_TICKETS = "view_department_tickets"
    ASSIGN_TICKET = "assign_ticket"
    REPLY_TICKET = "reply_ticket"

    # Users
    MANAGE_USERS = "manage_users"
    VIEW_USERS = "view_users"

    # Reports
    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"

    # Settings
    MANAGE_SETTINGS = "manage_settings"
    MANAGE_DEPARTMENTS = "manage_departments"
    MANAGE_FAQ = "manage_faq"

    # System
    AUDIT_LOG = "audit_log"


ROLE_PERMISSIONS: dict[str, list[Permission]] = {
    "super_admin": list(Permission),
    "admin": [
        Permission.VIEW_ALL_APPLICATIONS,
        Permission.PROCESS_APPLICATION,
        Permission.APPROVE_APPLICATION,
        Permission.BATCH_APPROVE,
        Permission.VIEW_ALL_TICKETS,
        Permission.ASSIGN_TICKET,
        Permission.REPLY_TICKET,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
        Permission.MANAGE_FAQ,
        # `super_admin` có quyền này từ đầu nhưng KHÔNG nằm trong `ROLES` của
        # src/models/db.py — không tài khoản nào mang được vai đó, nên trước
        # 30/08 quyền này thực tế không thuộc về ai. Tài khoản BQL là `admin`.
        Permission.MANAGE_SETTINGS,
    ],
    "manager": [
        Permission.VIEW_DEPARTMENT_APPLICATIONS,
        Permission.PROCESS_APPLICATION,
        Permission.APPROVE_APPLICATION,
        Permission.BATCH_APPROVE,
        Permission.VIEW_DEPARTMENT_TICKETS,
        Permission.ASSIGN_TICKET,
        Permission.REPLY_TICKET,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
    ],
    "staff": [
        Permission.VIEW_ASSIGNED_APPLICATIONS,
        Permission.PROCESS_APPLICATION,
        Permission.VIEW_REPORTS,
    ],
    "resident": [],  # No admin permissions
}
