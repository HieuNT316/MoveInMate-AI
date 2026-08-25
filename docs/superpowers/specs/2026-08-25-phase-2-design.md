# Phase 2 Design Specification

**Date:** 2026-08-25
**Status:** Draft — pending team review
**Scope:** MoveInMate Phase 2 (25-31/08/2026)
**Team:** Hiếu (BE), Hải (AI), Thu (FE)

---

## 1. Overview

### 1.1 Phase 2 Goals

Phase 2 mở rộng MoveInMate với các subsystems mới phục vụ Demo Day 01/09/2026:

| # | Feature | Owner | Priority |
|---|---|---|---|
| 1 | Push Notifications (Web Push) | Hiếu | P0 |
| 2 | RBAC (Roles + Permissions) | Hiếu | P0 |
| 3 | FAQ CRUD + LangGraph integration | Hải | P0 |
| 4 | Ticket System (US-11) | Hiếu | P1 |
| 5 | Batch Approval + Auto-assignment | Hiếu | P1 |
| 6 | Dashboard Reports (Standard+) | Thu | P1 |
| 7 | In-app Reminders (US-14) | Thu | P2 |
| 8 | System Settings UI | Thu | P2 |
| 9 | Gamification | Thu | P2 |
| 10 | Cost Tracking | Hiếu | P2 |

### 1.2 Effort Summary

| Owner | Features | Est. Hours |
|---|---|---|
| Hiếu (BE) | Push, RBAC, Tickets, Batch, Cost Tracking | ~35h |
| Hải (AI) | FAQ + LangGraph, US-11 ticket logic | ~15h |
| Thu (FE) | Reports, Settings UI, Reminders, Gamification | ~30h |
| **Total** | | **~80h** |

**Resource:** 3 people × 7 days × ~4h/day = ~84h available
**Buffer:** ~4h cho unexpected issues

---

## 2. Push Notifications

### 2.1 Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Backend    │────▶│  Push Service │────▶│  Browser/Device │
│  (FastAPI)  │     │  (web-push)  │     │  (Service Worker)│
└─────────────┘     └──────────────┘     └─────────────────┘
       │
       ▼
┌─────────────┐
│ Subscriptions│
│    Table    │
└─────────────┘
```

### 2.2 Database Schema

```sql
-- PUSH_SUBSCRIPTIONS
CREATE TABLE push_subscriptions (
    subscription_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(user_id),
    endpoint VARCHAR(500) NOT NULL,
    p256dh VARCHAR(256) NOT NULL,
    auth VARCHAR(128) NOT NULL,
    user_agent VARCHAR(256),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(endpoint)
);

CREATE INDEX idx_push_subscriptions_user ON push_subscriptions(user_id);
```

### 2.3 VAPID Configuration

```bash
# Generate VAPID keys (run once)
web-push generate-vapid-keys

# Environment variables
VAPID_PUBLIC_KEY=<from output>
VAPID_PRIVATE_KEY=<from output>
VAPID_SUBJECT=mailto:admin@moveinmate.vn
```

**Security:** `VAPID_PRIVATE_KEY` NEVER committed to git. Store in Railway environment variables.

### 2.4 API Endpoints

#### POST /api/v1/push/subscriptions
**Auth:** Bearer token (resident or BQL)
**Request:**
```json
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/...",
  "keys": {
    "p256dh": "B...",
    "auth": "..."
  },
  "user_agent": "Mozilla/5.0 ..."
}
```
**Response:** 201 Created

**Logic:**
- Extract `user_id` from token
- Upsert by `endpoint` (user can register multiple devices)
- Log subscription_id only (never log full subscription object)

#### DELETE /api/v1/push/subscriptions
**Auth:** Bearer token
**Request:**
```json
{
  "endpoint": "https://..."
}
```
**Response:** 204 No Content

**Logic:** Delete subscription belonging to authenticated user only.

### 2.5 Push Triggers

#### For Residents

| Event | Title | Body | URL |
|---|---|---|---|
| Hồ sơ được tiếp nhận | "Hồ sơ đã được gửi" | "Hồ sơ đăng ký [tên thủ tục] đang chờ BQL xử lý." | `/documents` |
| Đang xử lý | "Hồ sơ đang được xử lý" | "Hồ sơ của bạn đang được BQL xem xét." | `/documents` |
| Cần bổ sung | "Hồ sơ cần bổ sung giấy tờ" | "Vui lòng bổ sung: [danh sách giấy tờ]." | `/documents/{id}` |
| Được duyệt | "Hồ sơ đã được duyệt!" | "Chúc mừng! Hồ sơ [tên thủ tục] đã được duyệt." | `/documents` |
| Bị từ chối | "Hồ sơ bị từ chối" | "Hồ sơ [tên thủ tục] không được duyệt. Lý do: [bql_note]." | `/documents/{id}` |
| Có phản hồi mới | "BQL đã phản hồi" | "[Trích nội dung phản hồi, max 100 chars]..." | `/documents/{id}` |
| Thủ tục sắp quá hạn | "Nhắc nhở: thủ tục sắp hết hạn" | "Thủ tục [tên] cần hoàn thành trong [X] ngày." | `/checklist` |
| Thủ tục quá hạn | "Thủ tục đã quá hạn" | "Thủ tục [tên] đã quá hạn [X] ngày." | `/checklist` |

#### For BQL

| Event | Title | Body | URL |
|---|---|---|---|
| Hồ sơ mới | "Có hồ sơ mới cần xử lý" | "Cư dân [tên] vừa nộp hồ sơ [tên thủ tục]." | `/admin/applications` |
| Cần bổ sung | "Cư dân đã bổ sung giấy tờ" | "[Tên cư dân] đã bổ sung cho hồ sơ [tên thủ tục]." | `/admin/applications/{id}` |
| Ticket mới | "Có ticket mới" | "Cư dân [tên] hỏi: [trích câu hỏi, max 100 chars]..." | `/admin/tickets` |

### 2.6 Push Error Handling

- **404 / 410 Gone:** Subscription expired → delete from DB automatically
- **429:** Rate limited → retry after Retry-After header
- **Other errors:** Log error, keep subscription (will be cleaned by background job)

### 2.7 Frontend Integration

```typescript
// Service worker (sw.js)
self.addEventListener('push', (event) => {
  const { title, body, url } = event.data.json();
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: '/icon-192.png',
      badge: '/badge-72.png',
      data: { url }
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url)
  );
});
```

**Env variable:** `NEXT_PUBLIC_VAPID_PUBLIC_KEY` exposed to frontend only.

---

## 3. RBAC (Role-Based Access Control)

### 3.1 Roles

| Role | Description | Parent |
|---|---|---|
| `super_admin` | Toàn quyền hệ thống | — |
| `manager` | Quản lý bộ phận, phân công, duyệt hồ sơ, xem báo cáo | — |
| `staff` | Xử lý hồ sơ được giao | manager |
| `admin` | Legacy BQL (giữ nguyên quyền Phase 1) | — |

**Note:** Role hierarchy determines inheritance. `manager` inherits from `staff` implicitly.

### 3.2 Permissions

```typescript
enum Permission {
  // Applications
  VIEW_ALL_APPLICATIONS = 'view_all_applications',
  VIEW_DEPARTMENT_APPLICATIONS = 'view_department_applications',
  VIEW_ASSIGNED_APPLICATIONS = 'view_assigned_applications',
  PROCESS_APPLICATION = 'process_application',
  APPROVE_APPLICATION = 'approve_application',
  BATCH_APPROVE = 'batch_approve',

  // Tickets
  VIEW_ALL_TICKETS = 'view_all_tickets',
  VIEW_DEPARTMENT_TICKETS = 'view_department_tickets',
  ASSIGN_TICKET = 'assign_ticket',
  REPLY_TICKET = 'reply_ticket',

  // Users
  MANAGE_USERS = 'manage_users',
  VIEW_USERS = 'view_users',

  // Reports
  VIEW_REPORTS = 'view_reports',
  EXPORT_REPORTS = 'export_reports',

  // Settings
  MANAGE_SETTINGS = 'manage_settings',
  MANAGE_DEPARTMENTS = 'manage_departments',
  MANAGE_FAQ = 'manage_faq',

  // System
  AUDIT_LOG = 'audit_log',
}

const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  super_admin: Object.values(Permission), // All permissions
  admin: [
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
  ],
  manager: [
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
  staff: [
    Permission.VIEW_ASSIGNED_APPLICATIONS,
    Permission.PROCESS_APPLICATION,
    Permission.VIEW_REPORTS, // Only own stats
  ],
};
```

### 3.3 Database Schema

```sql
-- ROLES (pre-seeded)
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- PERMISSIONS (pre-seeded)
CREATE TABLE permissions (
    permission_id SERIAL PRIMARY KEY,
    permission_name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255)
);

-- ROLE_PERMISSIONS (junction)
CREATE TABLE role_permissions (
    role_id INT REFERENCES roles(role_id),
    permission_id INT REFERENCES permissions(permission_id),
    PRIMARY KEY (role_id, permission_id)
);

-- DEPARTMENTS
CREATE TABLE departments (
    department_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    lead_user_id INT REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- STAFF_ASSIGNMENTS (which staff belongs to which department)
CREATE TABLE staff_assignments (
    assignment_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    department_id INT REFERENCES departments(department_id),
    assigned_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, department_id)
);

-- Update users table
ALTER TABLE users ADD COLUMN role VARCHAR(50) REFERENCES roles(role_name);
ALTER TABLE users ADD COLUMN department_id INT REFERENCES departments(department_id);
```

### 3.4 Backend Enforcement

```python
# src/middleware/rbac.py
from functools import wraps
from fastapi import HTTPException, status

def require_permission(permission: Permission):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user')
            if not user:
                raise HTTPException(status_code=401)

            if not has_permission(user.role, permission):
                raise HTTPException(status_code=403)

            # Check department access if applicable
            if requires_department_check(permission):
                resource_dept = kwargs.get('department_id')
                if not user_can_access_department(user, resource_dept):
                    raise HTTPException(status_code=403)

            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

**Example usage:**
```python
@router.patch("/admin/applications/{id}")
@require_permission(Permission.APPROVE_APPLICATION)
async def approve_application(id: int, current_user: User):
    # Check ownership/assignment before processing
    application = await get_application(id)
    if not can_user_process(user, application):
        raise HTTPException(status_code=403)
    ...
```

### 3.5 Department-Based Access Control

**Rule:** `staff` can only view/process applications assigned to them OR belonging to their department (if department_lead).

```python
def can_user_access_application(user: User, application: Application) -> bool:
    if user.role == 'super_admin':
        return True

    if user.role in ('admin', 'manager'):
        return True  # Admin/manager can access all

    if user.role == 'staff':
        # Staff can only access assigned applications
        return application.assigned_to == user.user_id

    return False
```

### 3.6 Audit Log

```sql
CREATE TABLE audit_log (
    audit_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id INT,
    old_value JSONB,
    new_value JSONB,
    ip_address VARCHAR(45),
    user_agent VARCHAR(256),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Logged actions:**
- `application.status_changed`
- `application.assigned`
- `ticket.created`
- `ticket.assigned`
- `ticket.resolved`
- `user.role_changed`
- `settings.changed`

---

## 4. FAQ System (US-09)

### 4.1 Database Schema

```sql
-- Already exists in Phase 1, adding fields for admin management
ALTER TABLE faq ADD COLUMN category VARCHAR(100);
ALTER TABLE faq ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE faq ADD COLUMN view_count INT DEFAULT 0;
ALTER TABLE faq ADD COLUMN order_index INT DEFAULT 0;
```

### 4.2 API Endpoints

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| GET | /api/v1/admin/faq | MANAGE_FAQ | List all FAQs |
| POST | /api/v1/admin/faq | MANAGE_FAQ | Create FAQ |
| PATCH | /api/v1/admin/faq/{id} | MANAGE_FAQ | Update FAQ |
| DELETE | /api/v1/admin/faq/{id} | MANAGE_FAQ | Delete FAQ |
| POST | /api/v1/admin/faq/reorder | MANAGE_FAQ | Reorder FAQs |
| GET | /api/v1/faq | — | Public: list active FAQs |
| POST | /api/v1/faq/search | — | Public: search FAQs |

### 4.3 LangGraph Integration

```python
# src/ai/nodes/faq_node.py
async def faq_node(state: AgentState) -> AgentState:
    """Check FAQ before RAG"""
    query = state.get('query')

    # Simple keyword match
    faqs = await get_active_faqs()
    for faq in faqs:
        if keyword_match(query, faq.question):
            return {
                'answer': faq.answer,
                'answer_source': 'faq',
                'confidence': 0.95,
                'sources': []
            }

    # No FAQ match → continue to RAG
    return {'next_node': 'rag'}
```

**Flow:** User query → FAQ node → Match? → Return FAQ answer → No match → RAG node

### 4.4 FAQ Admin UI

- List FAQs with category, view count, active status
- Create/Edit form: question, answer, category, order
- Toggle active/inactive
- Drag-and-drop reorder

---

## 5. Ticket System (US-11)

### 5.1 When Tickets Are Created

```python
# In RAG node, when confidence is low
async def rag_node(state: AgentState) -> AgentState:
    retrieved = await rag_retrieve(state['query'])

    if retrieved['count'] == 0:
        # No documents found → suggest ticket
        return {
            'answer': TICKET_SUGGESTION_MESSAGE,
            'answer_source': 'no_context',
            'confidence': 0.0,
            'ticket_suggested': True
        }

    if retrieved['max_distance'] > RAG_MAX_DISTANCE:
        # Low confidence → suggest ticket
        return {
            'ticket_suggested': True,
            'answer': LOW_CONFIDENCE_MESSAGE
        }

    # ... normal RAG flow
```

### 5.2 Database Schema

```sql
CREATE TABLE tickets (
    ticket_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    subject VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'open', -- open, in_progress, resolved, closed
    priority VARCHAR(20) DEFAULT 'normal', -- low, normal, high, urgent
    assigned_to INT REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

CREATE TABLE ticket_messages (
    message_id SERIAL PRIMARY KEY,
    ticket_id INT REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    sender_id INT REFERENCES users(user_id),
    sender_type VARCHAR(20) NOT NULL, -- 'resident', 'staff'
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tickets_user ON tickets(user_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_assigned ON tickets(assigned_to);
CREATE INDEX idx_messages_ticket ON ticket_messages(ticket_id);
```

### 5.3 API Endpoints

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| POST | /api/v1/tickets | Authenticated | Resident creates ticket |
| GET | /api/v1/tickets | Authenticated | Resident views own tickets |
| GET | /api/v1/tickets/{id} | Authenticated | View ticket + messages |
| POST | /api/v1/tickets/{id}/messages | Authenticated | Add message to ticket |
| PATCH | /api/v1/tickets/{id} | Authenticated | Update ticket status |

**Admin endpoints:**

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| GET | /api/v1/admin/tickets | VIEW_ALL_TICKETS | List all tickets |
| PATCH | /api/v1/admin/tickets/{id}/assign | ASSIGN_TICKET | Assign ticket |
| PATCH | /api/v1/admin/tickets/{id}/status | ASSIGN_TICKET | Change status |

### 5.4 Ticket Notifications

- When resident creates ticket → Push to BQL (filtered by department)
- When staff replies → Push to resident
- When ticket resolved → Push to resident

---

## 6. Batch Approval + Auto-Assignment

### 6.1 Batch Approval API

```python
@router.post("/api/v1/admin/applications/batch")
@require_permission(Permission.BATCH_APPROVE)
async def batch_approve_applications(
    application_ids: List[int],
    action: Literal['approve', 'reject'],
    note: Optional[str] = None,
    current_user: User = Depends(get_current_admin)
):
    # Validate all applications exist and are actionable
    applications = await get_applications(application_ids)

    # Check user has permission for all
    for app in applications:
        if not can_user_process(current_user, app):
            raise HTTPException(403)

    # Update all
    for app in applications:
        await update_application_status(
            app.id,
            status='approved' if action == 'approve' else 'rejected',
            bql_note=note,
            reviewed_by=current_user.user_id
        )

        # Trigger notifications
        await send_application_notification(app)

    # Return results
    return {
        'processed': len(applications),
        'failed': []
    }
```

### 6.2 Auto-Assignment Logic

```python
async def auto_assign_application(application: Application) -> Optional[int]:
    """Assign to staff with least workload in target department"""
    checklist_item = await get_checklist_item(application.checklist_item_id)
    department = get_department_for_item(checklist_item)

    if not department:
        return None

    # Get staff with least active applications
    query = """
        SELECT u.user_id, COUNT(a.application_id) as active_count
        FROM users u
        JOIN staff_assignments sa ON u.user_id = sa.user_id
        LEFT JOIN applications a ON a.assigned_to = u.user_id
            AND a.status NOT IN ('delivered', 'rejected')
        WHERE sa.department_id = :dept_id
            AND u.role = 'staff'
        GROUP BY u.user_id
        ORDER BY active_count ASC
        LIMIT 1
    """
    result = await db.execute(query, {'dept_id': department.id})
    row = result.fetchone()

    return row.user_id if row else None
```

### 6.3 Concurrency Control

```python
@router.patch("/api/v1/admin/applications/{id}")
@require_permission(Permission.APPROVE_APPLICATION)
async def update_application(
    id: int,
    status_update: StatusUpdate,
    version: int,  # Optimistic locking
    current_user: User = Depends(get_current_admin)
):
    application = await get_application(id)

    # Check version matches
    if application.version != version:
        raise HTTPException(
            status_code=409,
            detail="Application was modified by another user"
        )

    # Update with version increment
    await db.execute("""
        UPDATE applications
        SET status = :status,
            bql_note = :note,
            updated_at = NOW(),
            version = version + 1
        WHERE application_id = :id AND version = :version
    """, {...})

    # If no rows updated, version mismatch → 409
```

---

## 7. Dashboard Reports (US-12)

### 7.1 Report Types

#### 7.1.1 Operational Report

```typescript
interface OperationalReport {
  summary: {
    newApplications: number;        // Trong kỳ
    processing: number;              // Đang xử lý
    needsInfo: number;               // Cần bổ sung
    approved: number;               // Đã duyệt
    rejected: number;                // Từ chối
    avgProcessingDays: number;       // TB ngày xử lý
    onTimeRate: number;              // % đúng hạn
  };

  trends: {
    date: string;
    new: number;
    processed: number;
    pending: number;
  }[];

  overdue: {
    applicationId: number;
    residentName: string;
    procedureName: string;
    daysOverdue: number;
    assignedTo: string;
  }[];

  commonMissingDocs: {
    documentType: string;
    count: number;
  }[];

  commonRejectionReasons: {
    reason: string;
    count: number;
  }[];
}
```

#### 7.1.2 Staff Report

```typescript
interface StaffReport {
  staffId: number;
  staffName: string;

  metrics: {
    assigned: number;
    processed: number;
    pending: number;
    avgProcessingDays: number;
    approvalRate: number;           // % duyệt lần đầu
    requestInfoRate: number;        // % yêu cầu bổ sung
    rejectionRate: number;
    overdueCount: number;
  };

  workload: {
    date: string;
    assigned: number;
    processed: number;
  }[];

  activityLog: {
    date: string;
    action: string;
    applicationId: number;
  }[];
}
```

#### 7.1.3 Department Report

```typescript
interface DepartmentReport {
  departmentId: number;
  departmentName: string;

  metrics: {
    totalApplications: number;
    avgProcessingDays: number;
    overdueRate: number;
    unassignedCount: number;
    crossDeptTransfers: number;
  };

  bottlenecks: {
    procedureName: string;
    avgDays: number;
    pendingCount: number;
  }[];

  staffBreakdown: {
    staffId: number;
    staffName: string;
    pending: number;
    avgDays: number;
  }[];
}
```

### 7.2 Filters

```typescript
interface ReportFilters {
  dateRange: {
    from: string;  // ISO date
    to: string;
  };
  building?: string;
  procedureType?: number[];      // Checklist item IDs
  department?: number[];
  staff?: number[];
  status?: ApplicationStatus[];
  overdue?: boolean;
  ownerType?: 'owner' | 'renter';
}
```

### 7.3 Export Features

#### Excel Export
- All report tables exportable to `.xlsx`
- Formatted with headers, auto-column width
- Includes date range and filters in metadata

#### PDF Export
- Summary page with key metrics
- Tables formatted for print
- Branded header with date

### 7.4 Data Export Security

**Rule:** Export respects user's permission scope.

- `staff` can only export their own data
- `manager` can export department data
- `admin`/`super_admin` can export all data

**PII Masking:**
- CCCD: `123456789` → `123***789`
- File paths: Replaced with `[REDACTED]`
- Full export requires elevated permission

---

## 8. In-App Reminders (US-14)

### 8.1 Notification Types

```typescript
enum NotificationType {
  APPLICATION_STATUS = 'application_status',
  APPLICATION_NEEDS_INFO = 'application_needs_info',
  APPLICATION_APPROVED = 'application_approved',
  APPLICATION_REJECTED = 'application_rejected',
  TICKET_REPLY = 'ticket_reply',
  CHECKLIST_REMINDER = 'checklist_reminder',
  CHECKLIST_OVERDUE = 'checklist_overdue',
}
```

### 8.2 Database Schema

```sql
CREATE TABLE notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    data JSONB,  -- { applicationId, ticketId, checklistItemId, etc. }
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id, is_read, created_at DESC);
```

### 8.3 Reminder Logic

```python
# Background job (runs every hour)
async def check_overdue_items():
    """Send reminders for overdue checklist items"""
    users = await get_users_with_overdue_items()

    for user in users:
        overdue = await get_overdue_items(user.user_id)

        await create_notification(
            user_id=user.user_id,
            type=NotificationType.CHECKLIST_OVERDUE,
            title="Thủ tục đã quá hạn",
            body=f"Bạn có {len(overdue)} thủ tục đã quá hạn.",
            data={'overdueItems': overdue}
        )

        # Push if subscribed
        if await has_push_subscription(user.user_id):
            await send_push(user.user_id, {...})

# Runs daily at 9 AM
async def daily_reminder():
    """Remind about items due in 3 days"""
    users = await get_users_with_upcoming_deadlines(days=3)

    for user in users:
        await create_notification(
            user_id=user.user_id,
            type=NotificationType.CHECKLIST_REMINDER,
            title="Nhắc nhở: thủ tục sắp hết hạn",
            body=f"Bạn có {len(upcoming)} thủ tục cần hoàn thành trong 3 ngày tới.",
            data={'upcomingItems': upcoming}
        )
```

---

## 9. System Settings

### 9.1 Settings Categories

```typescript
interface SystemSettings {
  // Staff Management
  staffManagement: {
    canCreateStaff: boolean;
    canLockStaff: boolean;
    canAssignRoles: boolean;
    maxStaffPerDepartment: number;
  };

  // SLA Configuration
  sla: {
    defaultProcessingDays: number;
    warningDaysBefore: number;
    escalationDays: number;
    autoEscalateToManager: boolean;
  };

  // Document Settings
  documents: {
    allowedTypes: string[];  // ['pdf', 'jpg', 'png']
    maxFileSizeMB: number;
    retentionDays: number;
    autoDeleteAfterRetention: boolean;
  };

  // Security
  security: {
    sessionTimeoutMinutes: number;
    requirePasswordChange: boolean;
    twoFactorRequired: boolean;
  };

  // Notifications
  notifications: {
    emailEnabled: boolean;
    pushEnabled: boolean;
    quietHoursStart: string;  // "22:00"
    quietHoursEnd: string;    // "08:00"
  };
}
```

### 9.2 Settings API

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| GET | /api/v1/admin/settings | MANAGE_SETTINGS | Get all settings |
| PATCH | /api/v1/admin/settings | MANAGE_SETTINGS | Update settings |
| GET | /api/v1/admin/settings/audit | AUDIT_LOG | Get settings change history |

### 9.3 Settings UI

Admin settings page with sections:
- **Nhân viên**: List staff, create/lock accounts, assign roles/departments
- **Bộ phận**: CRUD departments, assign lead, configure procedures
- **Quy trình**: Enable/disable procedures, configure required documents
- **Thông báo**: Configure notification channels, templates
- **Bảo mật**: Session timeout, password policy, 2FA
- **SLA**: Processing time defaults, escalation rules

---

## 10. Document Viewer (Point 6)

### 10.1 API Endpoint

```python
@router.get("/api/v1/documents/{document_id}/content")
@require_permission(Permission.VIEW_DOCUMENTS)
async def get_document_content(
    document_id: int,
    current_user: User = Depends(get_current_user)
):
    # Get document metadata
    doc = await get_document(document_id)

    # Check access permissions
    if doc.source_type == 'bql_internal':
        # Only BQL can view internal documents
        if not is_bql_user(current_user):
            raise HTTPException(403)

    # Generate signed URL (expires in 15 minutes)
    signed_url = generate_signed_url(
        bucket='documents',
        path=doc.file_path,
        expires_in=900
    )

    return {
        'document_id': doc.id,
        'title': doc.title,
        'content_type': doc.content_type,
        'signed_url': signed_url,
        'expires_at': datetime.now() + timedelta(minutes=15)
    }
```

---

## 11. Password Reset (Point 5)

### 11.1 Configuration Checklist

- [ ] Add Vercel production domain to Supabase Redirect URLs
- [ ] Add `/reset-password` to allowed redirect URLs
- [ ] Customize email template with branding
- [ ] Set link expiration (default: 1 hour)
- [ ] Test full flow: request → email → reset → success
- [ ] Verify email lands in inbox (check spam)

### 11.2 No Code Required

Frontend already uses:
```typescript
supabase.auth.resetPasswordForEmail(email, {
  redirectTo: `${origin}/reset-password`
});
```

Backend uses Supabase Auth's built-in flow.

---

## 12. Gamification (Priority 2)

### 12.1 Badges

```typescript
const BADGES = [
  { id: 'first_step', name: 'Bước đầu tiên', icon: '🎯', condition: 'Complete 1 checklist item' },
  { id: 'half_way', name: 'Tiến một nửa', icon: '📊', condition: '50% checklist complete' },
  { id: 'resident_card', name: 'Thẻ cư dân', icon: '🏠', condition: 'Resident card approved' },
  { id: 'vehicle_card', name: 'Thẻ xe', icon: '🚗', condition: 'Vehicle card approved' },
  { id: 'all_done', name: 'Hoàn tất', icon: '🎉', condition: '100% checklist complete' },
  { id: 'fast_track', name: 'Nhanh như chớp', icon: '⚡', condition: 'Complete within 7 days' },
];
```

### 12.2 Progress Display

- Badge earned → celebration animation + badge icon
- Progress bar on dashboard showing % complete
- "Next milestone" preview

### 12.3 Database Schema

```sql
CREATE TABLE user_badges (
    badge_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    badge_key VARCHAR(50) NOT NULL,
    earned_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, badge_key)
);
```

---

## 13. Cost Tracking

### 13.1 Database Schema

```sql
CREATE TABLE usage_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    provider VARCHAR(20) NOT NULL,  -- 'openai', 'google', 'openrouter'
    model VARCHAR(100) NOT NULL,
    operation VARCHAR(50) NOT NULL,  -- 'chat', 'embedding'
    input_tokens INT,
    output_tokens INT,
    cost_usd DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 13.2 Logging Logic

```python
# In chat endpoint
start = time.time()
response = await chat_with_openai(messages)
duration = time.time() - start

await db.insert('usage_logs', {
    'user_id': current_user.user_id,
    'provider': 'openai',
    'model': 'gpt-4o-mini',
    'operation': 'chat',
    'input_tokens': response.usage.prompt_tokens,
    'output_tokens': response.usage.completion_tokens,
    'cost_usd': calculate_cost(response.usage)
})
```

### 13.3 Dashboard

- Total cost by day/week/month
- Cost breakdown by operation (chat vs embedding)
- Cost per user
- Monthly budget alerts

---

## 14. API Summary

### New Endpoints

| Method | Endpoint | Permission | Feature |
|---|---|---|---|
| POST | /api/v1/push/subscriptions | Auth | Push: subscribe |
| DELETE | /api/v1/push/subscriptions | Auth | Push: unsubscribe |
| GET | /api/v1/admin/faq | MANAGE_FAQ | FAQ: list |
| POST | /api/v1/admin/faq | MANAGE_FAQ | FAQ: create |
| PATCH | /api/v1/admin/faq/{id} | MANAGE_FAQ | FAQ: update |
| DELETE | /api/v1/admin/faq/{id} | MANAGE_FAQ | FAQ: delete |
| POST | /api/v1/tickets | Auth | Tickets: create |
| GET | /api/v1/tickets | Auth | Tickets: list own |
| GET | /api/v1/tickets/{id} | Auth | Tickets: detail |
| POST | /api/v1/tickets/{id}/messages | Auth | Tickets: reply |
| GET | /api/v1/admin/tickets | VIEW_ALL_TICKETS | Tickets: admin list |
| PATCH | /api/v1/admin/tickets/{id}/assign | ASSIGN_TICKET | Tickets: assign |
| POST | /api/v1/admin/applications/batch | BATCH_APPROVE | Batch approve |
| GET | /api/v1/documents/{id}/content | VIEW_DOCUMENTS | Document viewer |
| GET | /api/v1/admin/applications/report | VIEW_REPORTS | Operational report |
| GET | /api/v1/admin/staff/report | VIEW_REPORTS | Staff report |
| GET | /api/v1/admin/departments/report | VIEW_REPORTS | Department report |
| GET | /api/v1/admin/settings | MANAGE_SETTINGS | Settings: get |
| PATCH | /api/v1/admin/settings | MANAGE_SETTINGS | Settings: update |
| GET | /api/v1/notifications | Auth | Notifications: list |
| PATCH | /api/v1/notifications/{id}/read | Auth | Notifications: mark read |

---

## 15. Implementation Order

### Week 1 (Days 1-3: 25-27/08)

| # | Task | Owner | Dependency |
|---|---|---|---|
| 1 | DB migrations (roles, permissions, departments, tickets) | Hiếu | — |
| 2 | RBAC middleware + permission decorators | Hiếu | 1 |
| 3 | Push subscriptions API + web-push config | Hiếu | 1 |
| 4 | Push trigger on application status change | Hiếu | 3 |
| 5 | FAQ CRUD API + admin UI | Hải | 1 |
| 6 | LangGraph FAQ node | Hải | 5 |

### Week 1 (Days 4-5: 28-29/08)

| # | Task | Owner | Dependency |
|---|---|---|---|
| 7 | Ticket system API | Hiếu | 1 |
| 8 | Ticket creation from RAG low confidence | Hải | 7 |
| 9 | Ticket admin UI + notifications | Thu | 7 |
| 10 | Batch approval API | Hiếu | 2 |
| 11 | Auto-assignment logic | Hiếu | 2 |
| 12 | Document viewer API | Hiếu | 1 |

### Week 2 (Days 6-7: 30-31/08)

| # | Task | Owner | Dependency |
|---|---|---|---|
| 13 | Dashboard reports (Operational, Staff, Department) | Thu | 1 |
| 14 | Report exports (Excel, PDF) | Thu | 13 |
| 15 | In-app notifications UI | Thu | 7, 8 |
| 16 | System settings UI | Thu | 2 |
| 17 | Gamification | Thu | 1 |
| 18 | Cost tracking + dashboard | Hiếu | 1 |
| 19 | Testing + bug fixes | All | — |
| 20 | Demo prep | All | — |

---

## 16. Out of Scope for Phase 2

- Multi-language support
- OCR document verification
- SMS/Zalo notifications
- Real-time chat (WebSocket)
- Mobile app push
- Advanced ticket categorization
- Complex workflow builder
- SSO integration

---

## 17. Appendix: VAPID Keys Generation

```bash
# Install web-push if not installed
npm install -g web-push

# Generate keys
web-push generate-vapid-keys

# Output:
# ========================================
# Public Key:
# BGqNW9...
# ========================================
# Private Key:
# UUxI4O...
# ========================================

# Set in Railway environment variables:
VAPID_PUBLIC_KEY=BGqNW9...
VAPID_PRIVATE_KEY=UUxI4O...
VAPID_SUBJECT=mailto:admin@moveinmate.vn
```

---

## 18. Appendix: Seed Data for Phase 2

```python
# scripts/seed_phase2.py
ROLES = [
    ('super_admin', 'Full system access'),
    ('manager', 'Department management + approval'),
    ('staff', 'Process assigned applications'),
    ('admin', 'Legacy BQL access'),
]

DEPARTMENTS = [
    ('Reception', 'Tiếp nhận và phân loại hồ sơ'),
    ('Documents', 'Kiểm tra và xử lý giấy tờ'),
    ('Cards', 'Cấp phát thẻ cư dân, thẻ xe'),
    ('Utilities', 'Tiện ích và dịch vụ'),
]

# Sample staff with roles
STAFF_ACCOUNTS = [
    ('Nguyen Van A', 'manager@moveinmate.vn', 'manager', 'Reception'),
    ('Tran Thi B', 'staff1@moveinmate.vn', 'staff', 'Documents'),
    ('Le Van C', 'staff2@moveinmate.vn', 'staff', 'Cards'),
]
```

---

**Document Status:** Draft v1.0 — Pending team review
**Next Step:** Team review → approve → start implementation
