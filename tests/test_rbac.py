"""Tests for RBAC middleware and permission system."""

from src.middleware.rbac import can_access_application, has_permission
from src.models.rbac import Permission


class TestHasPermission:
    """Test has_permission function."""

    def test_super_admin_has_all_permissions(self):
        """Super admin should have all permissions."""
        user = {"role": "super_admin"}
        for perm in Permission:
            assert has_permission(user, perm), f"super_admin should have {perm}"

    def test_admin_has_application_permissions(self):
        """Admin should have application-related permissions."""
        user = {"role": "admin"}
        assert has_permission(user, Permission.VIEW_ALL_APPLICATIONS)
        assert has_permission(user, Permission.PROCESS_APPLICATION)
        assert has_permission(user, Permission.APPROVE_APPLICATION)
        assert has_permission(user, Permission.BATCH_APPROVE)
        assert has_permission(user, Permission.MANAGE_FAQ)

    def test_admin_has_ticket_permissions(self):
        """Admin should have ticket-related permissions."""
        user = {"role": "admin"}
        assert has_permission(user, Permission.VIEW_ALL_TICKETS)
        assert has_permission(user, Permission.ASSIGN_TICKET)
        assert has_permission(user, Permission.REPLY_TICKET)

    def test_admin_has_report_permissions(self):
        """Admin should have report permissions."""
        user = {"role": "admin"}
        assert has_permission(user, Permission.VIEW_REPORTS)
        assert has_permission(user, Permission.EXPORT_REPORTS)

    def test_admin_missing_critical_permissions(self):
        """Admin should NOT have some super_admin-only permissions."""
        user = {"role": "admin"}
        assert not has_permission(user, Permission.MANAGE_USERS)
        assert not has_permission(user, Permission.MANAGE_DEPARTMENTS)
        assert not has_permission(user, Permission.MANAGE_SETTINGS)
        assert not has_permission(user, Permission.AUDIT_LOG)

    def test_manager_has_department_application_permissions(self):
        """Manager should have department-scoped application permissions."""
        user = {"role": "manager"}
        assert has_permission(user, Permission.VIEW_DEPARTMENT_APPLICATIONS)
        assert has_permission(user, Permission.PROCESS_APPLICATION)
        assert has_permission(user, Permission.APPROVE_APPLICATION)

    def test_manager_has_department_ticket_permissions(self):
        """Manager should have department-scoped ticket permissions."""
        user = {"role": "manager"}
        assert has_permission(user, Permission.VIEW_DEPARTMENT_TICKETS)
        assert has_permission(user, Permission.ASSIGN_TICKET)
        assert has_permission(user, Permission.REPLY_TICKET)

    def test_manager_missing_all_application_permissions(self):
        """Manager should NOT have all-applications permissions."""
        user = {"role": "manager"}
        assert not has_permission(user, Permission.VIEW_ALL_APPLICATIONS)
        assert not has_permission(user, Permission.VIEW_ALL_TICKETS)

    def test_staff_has_assigned_application_permission(self):
        """Staff should have limited application permissions."""
        user = {"role": "staff"}
        assert has_permission(user, Permission.VIEW_ASSIGNED_APPLICATIONS)
        assert has_permission(user, Permission.PROCESS_APPLICATION)
        assert has_permission(user, Permission.VIEW_REPORTS)

    def test_staff_missing_broad_permissions(self):
        """Staff should NOT have broad permissions."""
        user = {"role": "staff"}
        assert not has_permission(user, Permission.VIEW_ALL_APPLICATIONS)
        assert not has_permission(user, Permission.VIEW_DEPARTMENT_APPLICATIONS)
        assert not has_permission(user, Permission.APPROVE_APPLICATION)
        assert not has_permission(user, Permission.MANAGE_USERS)
        assert not has_permission(user, Permission.EXPORT_REPORTS)

    def test_resident_has_no_admin_permissions(self):
        """Resident should have NO admin permissions."""
        user = {"role": "resident"}
        assert not has_permission(user, Permission.VIEW_ALL_APPLICATIONS)
        assert not has_permission(user, Permission.APPROVE_APPLICATION)
        assert not has_permission(user, Permission.MANAGE_USERS)
        assert not has_permission(user, Permission.VIEW_REPORTS)

    def test_resident_has_empty_permission_list(self):
        """Resident should have no permissions at all."""
        user = {"role": "resident"}
        for perm in Permission:
            assert not has_permission(user, perm), f"resident should not have {perm}"

    def test_unknown_role_defaults_to_no_permissions(self):
        """Unknown role should default to no permissions (like resident)."""
        user = {"role": "unknown_role"}
        assert not has_permission(user, Permission.VIEW_ALL_APPLICATIONS)

    def test_missing_role_defaults_to_resident(self):
        """User without role should default to resident (no permissions)."""
        user = {}
        assert not has_permission(user, Permission.VIEW_ALL_APPLICATIONS)

    def test_user_with_none_role(self):
        """User with None role should default to resident."""
        user = {"role": None}
        assert not has_permission(user, Permission.VIEW_ALL_APPLICATIONS)


class TestCanAccessApplication:
    """Test can_access_application function."""

    def test_super_admin_can_access_any_application(self):
        """Super admin can access any application regardless of assignment."""
        user = {"role": "super_admin", "user_id": 1}
        app = {"assigned_to": 999}
        assert can_access_application(user, app)

    def test_admin_can_access_any_application(self):
        """Admin can access any application."""
        user = {"role": "admin", "user_id": 2}
        app = {"assigned_to": 999}
        assert can_access_application(user, app)

    def test_manager_can_access_any_application(self):
        """Manager can access any application."""
        user = {"role": "manager", "user_id": 3}
        app = {"assigned_to": 999}
        assert can_access_application(user, app)

    def test_staff_can_access_assigned_application(self):
        """Staff can access applications assigned to them."""
        user = {"role": "staff", "user_id": 5}
        app = {"assigned_to": 5}
        assert can_access_application(user, app)

    def test_staff_cannot_access_unassigned_application(self):
        """Staff cannot access applications not assigned to them."""
        user = {"role": "staff", "user_id": 5}
        app = {"assigned_to": 999}
        assert not can_access_application(user, app)

    def test_staff_cannot_access_own_not_assigned(self):
        """Staff cannot access even if user_id matches but not assigned_to."""
        user = {"role": "staff", "user_id": 5}
        app = {"assigned_to": None}
        assert not can_access_application(user, app)

    def test_resident_cannot_access_applications(self):
        """Resident cannot access any application."""
        user = {"role": "resident", "user_id": 10}
        app = {"assigned_to": 10}
        assert not can_access_application(user, app)

    def test_unknown_role_cannot_access_applications(self):
        """Unknown role cannot access any application."""
        user = {"role": "unknown"}
        app = {}
        assert not can_access_application(user, app)


class TestPermissionEnum:
    """Test Permission enum values."""

    def test_all_permissions_are_strings(self):
        """All permissions should be strings (for database storage)."""
        for perm in Permission:
            assert isinstance(perm.value, str)

    def test_permission_values_match_spec(self):
        """Permission values should match the spec exactly."""
        assert Permission.VIEW_ALL_APPLICATIONS.value == "view_all_applications"
        assert Permission.VIEW_DEPARTMENT_APPLICATIONS.value == "view_department_applications"
        assert Permission.VIEW_ASSIGNED_APPLICATIONS.value == "view_assigned_applications"
        assert Permission.PROCESS_APPLICATION.value == "process_application"
        assert Permission.APPROVE_APPLICATION.value == "approve_application"
        assert Permission.BATCH_APPROVE.value == "batch_approve"

    def test_permission_count(self):
        """Should have exactly the expected number of permissions."""
        # Applications: 6, Tickets: 4, Users: 2, Reports: 2, Settings: 3, System: 1
        expected_count = 6 + 4 + 2 + 2 + 3 + 1
        assert len(Permission) == expected_count


class TestRolePermissionsMapping:
    """Test ROLE_PERMISSIONS mapping."""

    def test_super_admin_has_all_permissions(self):
        """Super admin should have all permissions."""
        from src.models.rbac import ROLE_PERMISSIONS
        assert len(ROLE_PERMISSIONS["super_admin"]) == len(Permission)

    def test_admin_permission_count(self):
        """Admin should have exactly specified number of permissions."""
        from src.models.rbac import ROLE_PERMISSIONS
        # VIEW_ALL, PROCESS, APPROVE, BATCH, VIEW_ALL_TICKETS, ASSIGN_TICKET,
        # REPLY_TICKET, VIEW_REPORTS, EXPORT_REPORTS, MANAGE_FAQ = 10
        assert len(ROLE_PERMISSIONS["admin"]) == 10

    def test_manager_permission_count(self):
        """Manager should have exactly specified number of permissions."""
        from src.models.rbac import ROLE_PERMISSIONS
        # VIEW_DEPT, PROCESS, APPROVE, BATCH, VIEW_DEPT_TICKETS, ASSIGN_TICKET,
        # REPLY_TICKET, VIEW_REPORTS, EXPORT_REPORTS = 9
        assert len(ROLE_PERMISSIONS["manager"]) == 9

    def test_staff_permission_count(self):
        """Staff should have exactly specified number of permissions."""
        from src.models.rbac import ROLE_PERMISSIONS
        # VIEW_ASSIGNED, PROCESS, VIEW_REPORTS = 3
        assert len(ROLE_PERMISSIONS["staff"]) == 3

    def test_resident_has_no_permissions(self):
        """Resident should have no permissions."""
        from src.models.rbac import ROLE_PERMISSIONS
        assert ROLE_PERMISSIONS["resident"] == []
