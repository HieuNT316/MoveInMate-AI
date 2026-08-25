"""Test batch approval and auto-assignment (Task 6, Phase 2).

Tests the following features:
- Batch approve/reject applications
- Optimistic locking (version check)
- Auto-assignment on approval (assigns to staff with least active applications)
- Error handling (not found, version conflict)
"""
from __future__ import annotations

import pytest

from src.models.db import Application, Department, StaffAssignment, User
from src.services import assignment, store

ADMIN = {"X-User-Id": "1"}
OWNER = {"X-User-Id": "2"}
CAR_CARD_ITEM = 6      # "Đăng ký thẻ xe"  — owner có xe
RESIDENT_CARD_ITEM = 1  # "Làm thẻ cư dân (chủ hộ)" — owner có trong checklist


def _close_app(db_session, user_id, checklist_item_id):
    """Đóng hồ sơ đang mở của user+item để test có thể nộp lại."""
    from sqlalchemy import update
    db_session.execute(
        update(Application).where(
            Application.user_id == user_id,
            Application.checklist_item_id == checklist_item_id,
            Application.status.not_in(("delivered", "rejected")),
        ).values(status="rejected")
    )
    db_session.commit()


async def _submit(client, item_id, headers=OWNER):
    return (
        await client.post(
            "/api/v1/applications",
            json={"checklist_item_id": item_id},
            headers=headers,
        )
    ).json()


# --- Batch Approval -------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_approve_all_success(client, db_session):
    """Duyệt nhiều hồ sơ cùng lúc — tất cả thành công."""
    # Đóng hồ sơ cũ trước để tránh UNIQUE constraint
    _close_app(db_session, 2, CAR_CARD_ITEM)
    _close_app(db_session, 2, RESIDENT_CARD_ITEM)

    app1 = await _submit(client, CAR_CARD_ITEM)
    app2 = await _submit(client, RESIDENT_CARD_ITEM)

    r = await client.post(
        "/api/v1/admin/applications/batch",
        json={
            "application_ids": [app1["application_id"], app2["application_id"]],
            "action": "approve",
        },
        headers=ADMIN,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["processed"] == 2
    assert data["failed"] == []


@pytest.mark.asyncio
async def test_batch_reject_all_success(client, db_session):
    """Từ chối nhiều hồ sơ cùng lúc."""
    _close_app(db_session, 2, CAR_CARD_ITEM)
    _close_app(db_session, 2, RESIDENT_CARD_ITEM)

    app1 = await _submit(client, CAR_CARD_ITEM)
    app2 = await _submit(client, RESIDENT_CARD_ITEM)

    r = await client.post(
        "/api/v1/admin/applications/batch",
        json={
            "application_ids": [app1["application_id"], app2["application_id"]],
            "action": "reject",
            "bql_note": "Không đủ điều kiện",
        },
        headers=ADMIN,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["processed"] == 2

    # Verify status changed
    apps = (await client.get("/api/v1/admin/applications", headers=ADMIN)).json()
    app1_data = next(a for a in apps if a["application_id"] == app1["application_id"])
    assert app1_data["status"] == "rejected"


@pytest.mark.asyncio
async def test_batch_partial_failure(client, db_session):
    """Một số hồ sơ không tìm thấy — vẫn xử lý được các hồ sơ còn lại."""
    _close_app(db_session, 2, CAR_CARD_ITEM)

    app1 = await _submit(client, CAR_CARD_ITEM)

    r = await client.post(
        "/api/v1/admin/applications/batch",
        json={
            "application_ids": [app1["application_id"], 99999],
            "action": "approve",
        },
        headers=ADMIN,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["processed"] == 1
    assert len(data["failed"]) == 1
    assert data["failed"][0]["application_id"] == 99999


@pytest.mark.asyncio
async def test_batch_approve_nonexistent_all_failed(client):
    """Toàn bộ không tồn tại — processed=0, failed có đủ."""
    r = await client.post(
        "/api/v1/admin/applications/batch",
        json={"application_ids": [99998, 99999], "action": "approve"},
        headers=ADMIN,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["processed"] == 0
    assert len(data["failed"]) == 2


@pytest.mark.asyncio
async def test_batch_approve_empty_list(client):
    """Danh sách rỗng bị Pydantic chặn."""
    r = await client.post(
        "/api/v1/admin/applications/batch",
        json={"application_ids": [], "action": "approve"},
        headers=ADMIN,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_batch_resident_forbidden(client):
    """Cư dân không có quyền batch approve."""
    r = await client.post(
        "/api/v1/admin/applications/batch",
        json={"application_ids": [1], "action": "approve"},
        headers=OWNER,
    )
    assert r.status_code == 403


# --- Optimistic Locking -------------------------------------------------


@pytest.mark.asyncio
async def test_update_status_increments_version(db_session):
    """Cập nhật trạng thái phải tăng version."""
    from sqlalchemy import select

    app = Application(
        user_id=5,  # user 5 chưa có ứng dụng
        checklist_item_id=RESIDENT_CARD_ITEM,
        status="received",
        kind="bql_processing",
        version=1,
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)
    app_id = app.application_id
    initial_version = app.version

    result = store.update_application_status(
        db_session, app_id, "approved", None, None
    )

    assert result is not None
    # version đã tăng
    db_session.expire_all()
    updated_app = db_session.scalar(select(Application).where(Application.application_id == app_id))
    assert updated_app.version == initial_version + 1


@pytest.mark.asyncio
async def test_optimistic_lock_detects_stale_version(db_session):
    """Version cũ bị reject — đúng optimistic locking."""
    app = Application(
        user_id=4,
        checklist_item_id=2,  # dùng item khác tránh UNIQUE
        status="received",
        kind="bql_processing",
        version=5,
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)
    app_id = app.application_id

    # Cố cập nhật với version cũ
    with pytest.raises(store.VersionConflictError):
        store.update_application_status(
            db_session, app_id, "approved", None, None, expected_version=3
        )


@pytest.mark.asyncio
async def test_optimistic_lock_succeeds_with_correct_version(db_session):
    """Version đúng thì cập nhật thành công."""
    app = Application(
        user_id=5,
        checklist_item_id=2,
        status="received",
        kind="bql_processing",
        version=3,
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)
    app_id = app.application_id

    result = store.update_application_status(
        db_session, app_id, "approved", None, None, expected_version=3
    )
    assert result is not None
    assert result["status"] == "approved"

    # Version đã tăng
    db_session.expire_all()
    updated = db_session.get(Application, app_id)
    assert updated.version == 4


# --- Auto-Assignment -----------------------------------------------------


@pytest.mark.asyncio
async def test_auto_assign_gets_staff_with_least_work(db_session):
    """Staff có ít hồ sơ active nhất được chọn."""
    # Tạo department
    dept = Department(department_id=10, name="An ninh 2")
    db_session.add(dept)

    # Tạo staff: user 50 (0 hồ sơ), user 51 (2 hồ sơ)
    staff1 = User(user_id=50, full_name="Staff A", email="sa@test", apartment="-", building="-", role="staff")
    staff2 = User(user_id=51, full_name="Staff B", email="sb@test", apartment="-", building="-", role="staff")
    db_session.add(staff1)
    db_session.add(staff2)
    db_session.flush()

    db_session.add(StaffAssignment(user_id=50, department_id=10))
    db_session.add(StaffAssignment(user_id=51, department_id=10))

    # Staff 51 đã có 2 hồ sơ active — dùng item 3 (chủ hộ) và 4
    db_session.add(Application(
        user_id=2,
        checklist_item_id=3,
        status="processing",
        kind="bql_processing",
        assigned_to=51,
    ))
    db_session.add(Application(
        user_id=3,
        checklist_item_id=3,
        status="processing",
        kind="bql_processing",
        assigned_to=51,
    ))
    db_session.commit()

    # Gọi auto_assign
    chosen = assignment.get_least_worked_staff(db_session, 10)
    assert chosen == 50  # Staff A có ít việc nhất


@pytest.mark.asyncio
async def test_auto_assign_returns_none_when_no_staff(db_session):
    """Không có staff trong bộ phận -> trả None."""
    dept = Department(department_id=11, name="Tiếp tân 2")
    db_session.add(dept)
    db_session.commit()

    chosen = assignment.get_least_worked_staff(db_session, 11)
    assert chosen is None


@pytest.mark.asyncio
async def test_auto_assign_on_approval(db_session):
    """Duyệt hồ sơ -> auto_assign gán cho staff ít việc nhất."""
    # Setup: department + staff
    dept = Department(department_id=12, name="An ninh 3")
    db_session.add(dept)
    staff = User(user_id=60, full_name="Staff X", email="sx@test", apartment="-", building="-", role="staff")
    db_session.add(staff)
    db_session.flush()
    db_session.add(StaffAssignment(user_id=60, department_id=12))

    # Checklist item phải có handling_department khớp
    from src.models.db import ChecklistItem
    item = db_session.get(ChecklistItem, CAR_CARD_ITEM)
    item.handling_department = "An ninh 3"

    # Hồ sơ
    app = Application(
        user_id=5,
        checklist_item_id=CAR_CARD_ITEM,
        status="received",
        kind="bql_processing",
    )
    db_session.add(app)
    db_session.commit()
    app_id = app.application_id

    # Gọi auto_assign_on_approval
    staff_id = assignment.auto_assign_on_approval(db_session, app_id)
    assert staff_id == 60

    # Verify assigned_to đã được ghi (expire để đọc lại từ DB)
    db_session.expire_all()
    updated = db_session.get(Application, app_id)
    assert updated.assigned_to == 60


@pytest.mark.asyncio
async def test_auto_assign_skips_when_no_department(db_session):
    """Hồ sơ không có handling_department -> skip auto_assign."""
    from src.models.db import ChecklistItem

    item = db_session.get(ChecklistItem, CAR_CARD_ITEM)
    item.handling_department = None

    app = Application(
        user_id=5,
        checklist_item_id=CAR_CARD_ITEM,
        status="received",
        kind="bql_processing",
    )
    db_session.add(app)
    db_session.commit()
    app_id = app.application_id

    staff_id = assignment.auto_assign_on_approval(db_session, app_id)
    assert staff_id is None


@pytest.mark.asyncio
async def test_batch_approve_triggers_auto_assign(client, db_session):
    """Batch approve -> gọi auto_assign_on_approval cho mỗi hồ sơ được duyệt."""
    # Setup department + staff
    dept = Department(department_id=13, name="An ninh 4")
    db_session.add(dept)
    staff = User(user_id=70, full_name="Staff Y", email="sy@test", apartment="-", building="-", role="staff")
    db_session.add(staff)
    db_session.flush()
    db_session.add(StaffAssignment(user_id=70, department_id=13))

    # Set handling_department for the checklist item
    from src.models.db import ChecklistItem
    item = db_session.get(ChecklistItem, CAR_CARD_ITEM)
    item.handling_department = "An ninh 4"
    db_session.commit()

    # Đóng hồ sơ cũ
    _close_app(db_session, 2, CAR_CARD_ITEM)

    # Submit applications
    app1 = await _submit(client, CAR_CARD_ITEM)

    # Batch approve
    r = await client.post(
        "/api/v1/admin/applications/batch",
        json={
            "application_ids": [app1["application_id"]],
            "action": "approve",
        },
        headers=ADMIN,
    )
    assert r.status_code == 200
    assert r.json()["processed"] == 1

    # Verify assigned_to đã được set
    db_session.expire_all()
    updated = db_session.get(Application, app1["application_id"])
    assert updated.assigned_to == 70


# --- Edge Cases ----------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_reject_does_not_auto_assign(client, db_session):
    """Reject không gọi auto_assign."""
    dept = Department(department_id=14, name="An ninh 5")
    db_session.add(dept)
    staff = User(user_id=80, full_name="Staff Z", email="sz@test", apartment="-", building="-", role="staff")
    db_session.add(staff)
    db_session.flush()
    db_session.add(StaffAssignment(user_id=80, department_id=14))

    from src.models.db import ChecklistItem
    item = db_session.get(ChecklistItem, CAR_CARD_ITEM)
    item.handling_department = "An ninh 5"
    db_session.commit()

    _close_app(db_session, 2, CAR_CARD_ITEM)
    app = await _submit(client, CAR_CARD_ITEM)

    r = await client.post(
        "/api/v1/admin/applications/batch",
        json={"application_ids": [app["application_id"]], "action": "reject"},
        headers=ADMIN,
    )
    assert r.status_code == 200

    db_session.expire_all()
    updated = db_session.get(Application, app["application_id"])
    assert updated.assigned_to is None


@pytest.mark.asyncio
async def test_batch_invalid_action_rejected(client):
    """Action không hợp lệ bị Pydantic chặn."""
    r = await client.post(
        "/api/v1/admin/applications/batch",
        json={"application_ids": [1], "action": "maybe"},
        headers=ADMIN,
    )
    assert r.status_code == 422
