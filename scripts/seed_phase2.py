"""Seed Phase 2 data: roles, permissions, departments.

Chạy: python -m scripts.seed_phase2
"""

from __future__ import annotations

from src.config import get_settings, safe_database_url
from src.database import SessionLocal
from src.models.rbac import ROLE_PERMISSIONS
from sqlalchemy import text


DEPARTMENTS = [
    ("Reception", "Tiếp nhận và phân loại hồ sơ"),
    ("Documents", "Kiểm tra và xử lý giấy tờ"),
    ("Cards", "Cấp phát thẻ cư dân, thẻ xe"),
    ("Utilities", "Tiện ích và dịch vụ"),
]


def seed_roles(db: SessionLocal) -> list[str]:
    """Seed roles from ROLE_PERMISSIONS keys (except resident)."""
    seeded: list[str] = []
    for role_name in ROLE_PERMISSIONS:
        if role_name == "resident":
            continue  # resident is a user role, not a staff role
        db.execute(
            text("""
                INSERT INTO roles (role_name, description)
                VALUES (:role_name, :desc)
                ON CONFLICT (role_name) DO NOTHING
            """),
            {
                "role_name": role_name,
                "desc": _role_description(role_name),
            },
        )
        seeded.append(role_name)
    db.commit()
    return seeded


def _role_description(role_name: str) -> str:
    """Human-readable description for each role."""
    descriptions = {
        "super_admin": "Toàn quyền hệ thống",
        "admin": "Truy cập BQL đầy đủ",
        "manager": "Quản lý bộ phận và phê duyệt",
        "staff": "Xử lý hồ sơ được giao",
    }
    return descriptions.get(role_name, role_name)


def seed_permissions(db: SessionLocal) -> int:
    """Seed permissions from Permission enum values."""
    from src.models.rbac import Permission

    perm_names = [p.value for p in Permission]
    for perm_name in perm_names:
        db.execute(
            text("""
                INSERT INTO permissions (permission_name, description)
                VALUES (:perm_name, :desc)
                ON CONFLICT (permission_name) DO NOTHING
            """),
            {"perm_name": perm_name, "desc": _perm_description(perm_name)},
        )
    db.commit()
    return len(perm_names)


def _perm_description(perm_name: str) -> str:
    """Human-readable description for each permission."""
    descriptions = {
        "view_all_applications": "Xem tất cả hồ sơ",
        "view_department_applications": "Xem hồ sơ bộ phận",
        "view_assigned_applications": "Xem hồ sơ được giao",
        "process_application": "Xử lý hồ sơ",
        "approve_application": "Phê duyệt hồ sơ",
        "batch_approve": "Phê duyệt hàng loạt",
        "view_all_tickets": "Xem tất cả ticket",
        "view_department_tickets": "Xem ticket bộ phận",
        "assign_ticket": "Giao ticket",
        "reply_ticket": "Trả lời ticket",
        "manage_users": "Quản lý người dùng",
        "view_users": "Xem người dùng",
        "view_reports": "Xem báo cáo",
        "export_reports": "Xuất báo cáo",
        "manage_settings": "Quản lý cài đặt",
        "manage_departments": "Quản lý bộ phận",
        "manage_faq": "Quản lý FAQ",
        "audit_log": "Xem nhật ký kiểm toán",
    }
    return descriptions.get(perm_name, perm_name)


def seed_role_permissions(db: SessionLocal) -> None:
    """Seed role_permissions from ROLE_PERMISSIONS mapping."""
    for role_name, permissions in ROLE_PERMISSIONS.items():
        for perm in permissions:
            db.execute(
                text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT r.role_id, p.permission_id
                    FROM roles r, permissions p
                    WHERE r.role_name = :role_name
                      AND p.permission_name = :perm_name
                    ON CONFLICT DO NOTHING
                """),
                {"role_name": role_name, "perm_name": perm.value},
            )
    db.commit()


def seed_departments(db: SessionLocal) -> list[str]:
    """Seed departments."""
    seeded: list[str] = []
    for dept_name, description in DEPARTMENTS:
        # departments has no unique constraint on name, use WHERE NOT EXISTS
        db.execute(
            text("""
                INSERT INTO departments (name, description)
                SELECT :name, :desc
                WHERE NOT EXISTS (
                    SELECT 1 FROM departments WHERE name = :name
                )
            """),
            {"name": dept_name, "desc": description},
        )
        seeded.append(dept_name)
    db.commit()
    return seeded


def main() -> None:
    if get_settings().app_env == "production":
        raise SystemExit("Từ chối seed khi APP_ENV=production.")

    db = SessionLocal()
    try:
        print("Seeding roles...")
        roles = seed_roles(db)
        print(f"  OK  {len(roles)} roles: {', '.join(roles)}")

        print("Seeding permissions...")
        perm_count = seed_permissions(db)
        print(f"  OK  {perm_count} permissions")

        print("Seeding role_permissions...")
        seed_role_permissions(db)
        print("  OK  role_permissions mapped")

        print("Seeding departments...")
        depts = seed_departments(db)
        print(f"  OK  {len(depts)} departments: {', '.join(depts)}")

        print(f"\nDone! DB: {safe_database_url()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
