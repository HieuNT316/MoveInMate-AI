"""Auto-assignment service — gán hồ sơ cho nhân viên ít việc nhất.

Module này chỉ chạy khi BQL duyệt hồ sơ (store.update_application_status).
Không import từ module này vào routes để tránh lazy import circular.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_least_worked_staff(db: Session, department_id: int) -> int | None:
    """Tra staff có ít hồ sơ đang xử lý nhất trong bộ phận.

    Chỉ đếm hồ sơ CHƯA đóng: delivered/rejected không tính là đang mở.
    """
    stmt = text("""
        SELECT u.user_id
        FROM users u
        JOIN staff_assignments sa ON u.user_id = sa.user_id
        LEFT JOIN applications a ON a.assigned_to = u.user_id
            AND a.status NOT IN ('delivered', 'rejected')
        WHERE sa.department_id = :dept_id
            AND u.role IN ('admin', 'staff')
        GROUP BY u.user_id
        ORDER BY COUNT(a.application_id) ASC
        LIMIT 1
    """)
    result = db.execute(stmt, {"dept_id": department_id})
    row = result.fetchone()
    return row.user_id if row else None


def get_department_id_by_name(db: Session, department_name: str) -> int | None:
    """Tra department_id từ tên bộ phận."""
    stmt = text("""
        SELECT department_id
        FROM departments
        WHERE name = :name
        LIMIT 1
    """)
    result = db.execute(stmt, {"name": department_name})
    row = result.fetchone()
    return row.department_id if row else None


def auto_assign_on_approval(db: Session, application_id: int) -> int | None:
    """Gán hồ sơ cho nhân viên ít việc nhất sau khi BQL duyệt.

    Tra bộ phận từ checklist_item (qua handling_department), rồi tìm
    staff có ít hồ sơ active nhất trong bộ phận đó.
    """
    # Tra checklist_item để lấy handling_department
    stmt = text("""
        SELECT ci.handling_department
        FROM applications a
        JOIN checklist_items ci ON a.checklist_item_id = ci.checklist_item_id
        WHERE a.application_id = :app_id
    """)
    result = db.execute(stmt, {"app_id": application_id})
    row = result.fetchone()

    if not row or not row.handling_department:
        logger.info("Application %d: no handling_department, skipping auto-assign", application_id)
        return None

    department_name = row.handling_department
    dept = get_department_id_by_name(db, department_name)
    if not dept:
        logger.warning("Application %d: department '%s' not found in departments table",
                      application_id, department_name)
        return None

    staff_id = get_least_worked_staff(db, dept)
    if staff_id:
        update_stmt = text("""
            UPDATE applications
            SET assigned_to = :staff_id
            WHERE application_id = :app_id
        """)
        db.execute(update_stmt, {"staff_id": staff_id, "app_id": application_id})
        db.commit()  # commit the assignment; caller's transaction already committed the status
        logger.info("Application %d auto-assigned to staff %d (dept %d)",
                    application_id, staff_id, dept)
    else:
        logger.info("Application %d: no staff available in department '%s'",
                    application_id, department_name)

    return staff_id
