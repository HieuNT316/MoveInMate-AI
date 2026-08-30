"""Truy vấn tổng hợp cho Report API.

Đọc `src/services/reporting.py` trước — file đó giữ phép đếm ngày làm việc và
hai nguyên tắc mà file này bám theo.

**Vì sao mốc thời gian đến từ `audit_log`:** `applications` chỉ có `created_at`
và `updated_at`. `updated_at` bị ghi đè mỗi lần sửa BẤT KỲ trường nào (thêm ghi
chú, gán người xử lý) nên không dùng làm mốc duyệt được. Đường ghi trạng thái
(`store.update_application_status`) đã ghi `application.status_changed` kèm
`new_value.status` — đó là nơi duy nhất biết hồ sơ vào trạng thái nào lúc nào.

**Vì sao không cache:** dịch vụ chạy MỘT instance (docs/DEPLOY.md mục 213) và
quy mô thật là 40 cư dân × 13 thủ tục. Cache invalidation ở đây phức tạp hơn
chính truy vấn nó tăng tốc. Nếu về sau chậm thật thì index
`audit_log(action, created_at)` đã sẵn sàng, dùng nó trước.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.models.db import (
    APPLICATION_STATUSES,
    CLOSED_STATUSES,
    Application,
    AuditLog,
    Department,
    StaffAssignment,
    User,
)
from src.services import settings_store
from src.services.reporting import business_days_between

STATUS_CHANGED = "application.status_changed"

# Hồ sơ coi là "đã xử lý xong" khi đạt một trong các trạng thái này. `rejected`
# nằm trong danh sách: BQL vẫn tốn công xem xét rồi mới từ chối, loại nó ra sẽ
# làm đẹp số liệu một cách giả tạo.
COMPLETED_STATUSES = ("approved", "delivered", "rejected")


def resolve_period(
    db: Session, date_from: str | None, date_to: str | None
) -> tuple[datetime, datetime]:
    """Chuẩn hoá kỳ báo cáo, lấy mặc định từ cấu hình hệ thống.

    Ném `ValueError` với chuỗi ngày sai định dạng — im lặng rơi về mặc định sẽ
    khiến BQL đọc một kỳ khác hẳn kỳ họ chọn mà không biết.
    """
    # Chuỗi rỗng = ô ngày bị xoá trống, hiểu là "không chọn" chứ không phải giá
    # trị sai. Trả 422 vào mặt người vừa xoá ô lọc là vô lý; còn chuỗi CÓ nội
    # dung mà sai định dạng thì phải nổ, xem `_parse_date`.
    date_from = (date_from or "").strip() or None
    date_to = (date_to or "").strip() or None

    end = _parse_date(date_to, "date_to") if date_to else datetime.now(UTC)
    if date_from:
        start = _parse_date(date_from, "date_from")
    else:
        days = settings_store.get_settings(db)["reports"]["defaultPeriodDays"]
        start = end - timedelta(days=days)

    if start > end:
        raise ValueError("date_from phải trước date_to")
    return start, end


def _parse_date(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} không phải ngày ISO hợp lệ: {value!r}") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _first_reached(db: Session, statuses: tuple[str, ...]) -> dict[int, datetime]:
    """Lần ĐẦU mỗi hồ sơ đạt một trong các trạng thái đã cho.

    Lần đầu chứ không phải lần cuối: hồ sơ đi approved → needs_info → approved
    thì quãng giữa là thời gian chờ CƯ DÂN bổ sung giấy tờ. Tính nó vào thời
    gian xử lý của BQL là đổ lỗi sai chỗ.
    """
    rows = db.execute(
        select(AuditLog.resource_id, AuditLog.new_value, AuditLog.created_at)
        .where(AuditLog.action == STATUS_CHANGED)
        .where(AuditLog.resource_type == "application")
        .order_by(AuditLog.created_at)
    ).all()

    # Lọc theo `new_value.status` trong Python: `new_value` là JSON và toán tử
    # trích khoá khác nhau giữa SQLite (test) với Postgres. Số dòng ở quy mô này
    # nhỏ, không đáng đánh đổi lấy một câu SQL chỉ chạy được trên một hệ.
    reached: dict[int, datetime] = {}
    for resource_id, new_value, created_at in rows:
        if resource_id is None or not isinstance(new_value, dict):
            continue
        if new_value.get("status") not in statuses:
            continue
        reached.setdefault(resource_id, created_at)
    return reached


def _load_applications(
    db: Session, start: datetime, end: datetime
) -> list[Application]:
    """Hồ sơ NỘP trong kỳ, kèm sẵn cư dân và thủ tục."""
    return list(
        db.scalars(
            select(Application)
            .options(selectinload(Application.user), selectinload(Application.item))
            .where(Application.created_at >= start)
            .where(Application.created_at <= end)
            .order_by(Application.application_id)
        )
    )


def _load_open_applications(db: Session) -> list[Application]:
    """Mọi hồ sơ CHƯA đóng, bất kể nộp lúc nào.

    Dùng cho danh sách quá hạn — xem giải thích ở `applications_report`.
    """
    return list(
        db.scalars(
            select(Application)
            .options(selectinload(Application.user), selectinload(Application.item))
            .where(Application.status.notin_(CLOSED_STATUSES))
            .order_by(Application.application_id)
        )
    )


def _processing_days(app: Application, reached: dict[int, datetime]) -> int | None:
    """Số ngày làm việc từ lúc nộp tới lần đầu đóng hồ sơ. None nếu chưa đóng
    hoặc thiếu dòng audit."""
    closed_at = reached.get(app.application_id)
    if closed_at is None:
        return None
    return business_days_between(app.created_at, closed_at)


def _overdue_days(app: Application, now: datetime) -> int | None:
    """Số ngày làm việc VƯỢT quá SLA của một hồ sơ đang mở. None nếu không
    quá hạn hoặc thủ tục không có SLA."""
    sla = app.item.sla_business_days
    if sla is None or app.status in CLOSED_STATUSES:
        return None
    elapsed = business_days_between(app.created_at, now)
    return elapsed if elapsed is not None and elapsed > sla else None


def _avg(values: list[int]) -> float | None:
    """Trung bình làm tròn 1 chữ số. Mẫu rỗng → None, KHÔNG phải 0."""
    if not values:
        return None
    return round(sum(values) / len(values), 1)


def _rate(numerator: int, denominator: int) -> float | None:
    """Tỉ lệ 0..1. Mẫu rỗng → None: `0` đọc thành 'không cái nào đạt'."""
    if denominator <= 0:
        return None
    return round(numerator / denominator, 3)


def applications_report(
    db: Session,
    start: datetime,
    end: datetime,
    overdue_limit: int = 50,
) -> dict[str, Any]:
    """Báo cáo vận hành: khối lượng, thời gian xử lý, tỉ lệ đúng hạn, hồ sơ trễ."""
    apps = _load_applications(db, start, end)
    reached = _first_reached(db, COMPLETED_STATUSES)
    now = datetime.now(UTC)

    by_status = Counter(app.status for app in apps)

    processing_days: list[int] = []
    on_time = 0
    measurable = 0
    excluded_no_audit = 0
    excluded_no_sla = 0

    for app in apps:
        if app.status not in COMPLETED_STATUSES:
            continue
        days = _processing_days(app, reached)
        if days is None:
            # Hồ sơ đóng trước khi audit_log tồn tại, hoặc đổi trạng thái qua
            # đường không ghi audit. Báo qua `coverage` thay vì lặng lẽ bỏ.
            excluded_no_audit += 1
            continue
        processing_days.append(days)

        if app.item.sla_business_days is None:
            excluded_no_sla += 1
            continue
        measurable += 1
        if days <= app.item.sla_business_days:
            on_time += 1

    # Danh sách quá hạn KHÔNG lọc theo kỳ, khác với mọi số liệu ở trên.
    #
    # "Quá hạn" là tình trạng HIỆN TẠI, không phải sự kiện xảy ra trong kỳ. Hồ
    # sơ nộp từ ba tháng trước mà vẫn treo là thứ BQL cần thấy nhất — lọc theo
    # kỳ 30 ngày sẽ giấu đúng nó đi, và càng tồn đọng lâu càng chắc chắn bị giấu.
    overdue = [
        {
            "applicationId": app.application_id,
            "residentName": app.user.full_name,
            "apartment": app.user.apartment,
            "procedureName": app.item.task_name,
            "handlingDepartment": app.item.handling_department,
            "createdAt": app.created_at,
            "businessDaysElapsed": business_days_between(app.created_at, now),
            "slaBusinessDays": app.item.sla_business_days,
            "assignedTo": app.assigned_user.full_name if app.assigned_user else None,
        }
        for app in _load_open_applications(db)
        if _overdue_days(app, now) is not None
    ]
    overdue.sort(key=lambda row: row["businessDaysElapsed"], reverse=True)

    return {
        "period": {"dateFrom": start.date().isoformat(), "dateTo": end.date().isoformat()},
        "summary": {
            "total": len(apps),
            "byStatus": {s: by_status.get(s, 0) for s in APPLICATION_STATUSES},
            "avgProcessingDays": _avg(processing_days),
            "onTimeRate": _rate(on_time, measurable),
        },
        "coverage": {
            "closedInPeriod": sum(1 for a in apps if a.status in COMPLETED_STATUSES),
            "measurable": measurable,
            "excludedNoAudit": excluded_no_audit,
            "excludedNoSla": excluded_no_sla,
        },
        "trends": _trends(apps, reached),
        "overdue": overdue[:overdue_limit],
        "overdueTotal": len(overdue),
    }


def _trends(apps: list[Application], reached: dict[int, datetime]) -> list[dict[str, Any]]:
    """Số hồ sơ nộp và đóng theo từng ngày CÓ dữ liệu.

    Không trả dòng rỗng cho ngày không có hồ sơ nào: kỳ 365 ngày sẽ sinh 365
    dòng mà 300 trong đó là số 0. Biểu đồ phía giao diện tự điền khoảng trống.
    """
    created: Counter[date] = Counter(app.created_at.date() for app in apps)
    closed: Counter[date] = Counter(
        reached[app.application_id].date() for app in apps if app.application_id in reached
    )

    return [
        {
            "date": day.isoformat(),
            "created": created.get(day, 0),
            "closed": closed.get(day, 0),
        }
        for day in sorted(set(created) | set(closed))
    ]


def departments_report(
    db: Session,
    start: datetime,
    end: datetime,
    department: str | None = None,
) -> dict[str, Any]:
    """Báo cáo theo bộ phận xử lý.

    Bộ phận suy ra từ `checklist_items.handling_department` (một CHUỖI), không
    từ bảng `departments`: `applications` cố ý không có khoá ngoại tới bảng đó
    (`src/models/db.py`, docstring của `Application`).

    KHÔNG trả `departmentId`. Bảng `departments` đang chứa tên tiếng Anh
    (`Reception`, `Documents`, `Cards`, `Utilities` — `scripts/seed_phase2.py`)
    trong khi `handling_department` dùng tiếng Việt (`Lễ tân & CSKH`, `An ninh`,
    …), nên không cặp nào khớp và trường đó luôn là None. Một trường luôn rỗng,
    để dành cho trang quản lý bộ phận CHƯA tồn tại, chỉ khiến người đọc API mất
    thời gian tự hỏi vì sao. Khi nào có trang đó thì nối lại — kèm việc thống
    nhất tên giữa hai nguồn (bảng `departments` không có UNIQUE trên `name`,
    seed lại sẽ nhân đôi dòng chứ không cập nhật).
    """
    apps = _load_applications(db, start, end)
    reached = _first_reached(db, COMPLETED_STATUSES)
    now = datetime.now(UTC)

    grouped: dict[str, list[Application]] = defaultdict(list)
    for app in apps:
        name = app.item.handling_department
        if name is None:
            # Thủ tục ngoài phạm vi BQL — không có bộ phận nào để quy trách nhiệm.
            continue
        if department and name != department:
            continue
        grouped[name].append(app)

    departments = []
    for name, items in sorted(grouped.items()):
        days = [d for d in (_processing_days(a, reached) for a in items) if d is not None]
        departments.append(
            {
                "handlingDepartment": name,
                "total": len(items),
                "open": sum(1 for a in items if a.status not in CLOSED_STATUSES),
                "unassigned": sum(
                    1 for a in items if a.assigned_to is None and a.status not in CLOSED_STATUSES
                ),
                "overdue": sum(1 for a in items if _overdue_days(a, now) is not None),
                "avgProcessingDays": _avg(days),
                "measurable": len(days),
                "bottlenecks": _bottlenecks(items, reached),
            }
        )

    return {
        "period": {"dateFrom": start.date().isoformat(), "dateTo": end.date().isoformat()},
        "departments": departments,
    }


def _bottlenecks(apps: list[Application], reached: dict[int, datetime]) -> list[dict[str, Any]]:
    """Thủ tục chậm nhất trong một bộ phận, chậm trước."""
    by_procedure: dict[str, list[Application]] = defaultdict(list)
    for app in apps:
        by_procedure[app.item.task_name].append(app)

    rows = [
        {
            "procedureName": name,
            "avgProcessingDays": _avg(
                [d for d in (_processing_days(a, reached) for a in items) if d is not None]
            ),
            "openCount": sum(1 for a in items if a.status not in CLOSED_STATUSES),
        }
        for name, items in by_procedure.items()
    ]
    # Thủ tục chưa đo được (None) xếp cuối — không có số thì không kết luận được
    # là nhanh hay chậm.
    rows.sort(key=lambda r: (r["avgProcessingDays"] is None, -(r["avgProcessingDays"] or 0)))
    return rows


def staff_report(
    db: Session,
    start: datetime,
    end: datetime,
    staff_id: int | None = None,
) -> dict[str, Any]:
    """Báo cáo theo nhân viên được GÁN hồ sơ.

    `basis` trong kết quả nói rõ giới hạn này: số liệu tính theo
    `applications.assigned_to`, KHÔNG phải "ai bấm nút". `audit_log.user_id`
    hiện chỉ được điền ở một đường ghi (`PATCH /admin/applications/{id}`) nên
    chưa đủ tin cậy để quy công việc cho người thao tác.
    """
    apps = _load_applications(db, start, end)
    reached = _first_reached(db, COMPLETED_STATUSES)
    now = datetime.now(UTC)

    staff_rows = db.scalars(select(User).where(User.role == "admin")).all()
    if staff_id is not None:
        staff_rows = [u for u in staff_rows if u.user_id == staff_id]

    dept_by_user = {
        user_id: name
        for user_id, name in db.execute(
            select(StaffAssignment.user_id, Department.name).join(
                Department, Department.department_id == StaffAssignment.department_id
            )
        ).all()
    }

    by_staff: dict[int, list[Application]] = defaultdict(list)
    for app in apps:
        if app.assigned_to is not None:
            by_staff[app.assigned_to].append(app)

    staff = []
    for user in staff_rows:
        items = by_staff.get(user.user_id, [])
        closed = [a for a in items if a.status in COMPLETED_STATUSES]
        days = [d for d in (_processing_days(a, reached) for a in closed) if d is not None]
        outcomes = Counter(a.status for a in items)

        staff.append(
            {
                "staffId": user.user_id,
                "staffName": user.full_name,
                "department": dept_by_user.get(user.user_id),
                "assigned": len(items),
                "open": sum(1 for a in items if a.status not in CLOSED_STATUSES),
                "closed": len(closed),
                "overdue": sum(1 for a in items if _overdue_days(a, now) is not None),
                "avgProcessingDays": _avg(days),
                "measurable": len(days),
                "outcomeRates": {
                    "approved": _rate(outcomes.get("approved", 0), len(closed)),
                    "rejected": _rate(outcomes.get("rejected", 0), len(closed)),
                    "needsInfo": _rate(outcomes.get("needs_info", 0), len(closed)),
                },
            }
        )

    # Hồ sơ chưa gán ai để RIÊNG. Gộp vào một "nhân viên ảo" sẽ kéo lệch mọi
    # trung bình của người thật.
    unassigned = [a for a in apps if a.assigned_to is None]
    return {
        "period": {"dateFrom": start.date().isoformat(), "dateTo": end.date().isoformat()},
        "basis": "assigned_to",
        "staff": staff,
        "unassigned": {
            "open": sum(1 for a in unassigned if a.status not in CLOSED_STATUSES),
            "overdue": sum(1 for a in unassigned if _overdue_days(a, now) is not None),
        },
    }
