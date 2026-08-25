# Frontend Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement frontend features for Phase 2: Dashboard Reports, Settings UI, Notifications UI, Gamification

**Architecture:** Next.js App Router, React hooks for data fetching, Tailwind CSS for styling

**Spec:** `docs/superpowers/specs/2026-08-25-phase-2-design.md`

---

## Global Constraints

- Follow existing component patterns in `web/app/components/`
- Use existing API client (`web/lib/api.ts` or similar)
- Keep responsive design (mobile-first approach)
- Use Vietnamese language for all UI text
- Theme-aware colors (existing color tokens)

---

## Task 1: Dashboard Reports (US-12)

**Files:**
- Create: `web/app/bql/reports/page.tsx`
- Create: `web/app/components/reports/OperationalReport.tsx`
- Create: `web/app/components/reports/StaffReport.tsx`
- Create: `web/app/components/reports/DepartmentReport.tsx`
- Create: `web/app/components/reports/ReportFilters.tsx`
- Create: `web/app/components/reports/ExportButtons.tsx`
- Test: `tests/reports.test.tsx`

### Steps

- [ ] **Step 1: Create report types and API hooks**

```typescript
// web/lib/reports.ts
export interface ReportFilters {
  dateRange: {
    from: string;
    to: string;
  };
  building?: string;
  procedureType?: number[];
  department?: number[];
  staff?: number[];
  status?: string[];
  overdue?: boolean;
  ownerType?: 'owner' | 'renter';
}

export interface OperationalReport {
  summary: {
    newApplications: number;
    processing: number;
    needsInfo: number;
    approved: number;
    rejected: number;
    avgProcessingDays: number;
    onTimeRate: number;
  };
  trends: Array<{
    date: string;
    new: number;
    processed: number;
    pending: number;
  }>;
  overdue: Array<{
    applicationId: number;
    residentName: string;
    procedureName: string;
    daysOverdue: number;
    assignedTo: string;
  }>;
  commonMissingDocs: Array<{
    documentType: string;
    count: number;
  }>;
  commonRejectionReasons: Array<{
    reason: string;
    count: number;
  }>;
}

export async function fetchOperationalReport(filters: ReportFilters): Promise<OperationalReport> {
  const params = new URLSearchParams();
  if (filters.dateRange?.from) params.set('from', filters.dateRange.from);
  if (filters.dateRange?.to) params.set('to', filters.dateRange.to);
  // ... other filters

  const response = await fetch(`/api/v1/admin/applications/report?${params}`);
  if (!response.ok) throw new Error('Failed to fetch report');
  return response.json();
}
```

- [ ] **Step 2: Create Operational Report component**

```typescript
// web/app/components/reports/OperationalReport.tsx
'use client';

import { useState } from 'react';
import { OperationalReport } from '@/lib/reports';

interface Props {
  report: OperationalReport;
}

export function OperationalReportView({ report }: Props) {
  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard
          label="Hồ sơ mới"
          value={report.summary.newApplications}
          icon="📋"
        />
        <SummaryCard
          label="Đang xử lý"
          value={report.summary.processing}
          icon="⏳"
        />
        <SummaryCard
          label="Đã duyệt"
          value={report.summary.approved}
          icon="✅"
        />
        <SummaryCard
          label="Từ chối"
          value={report.summary.rejected}
          icon="❌"
        />
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 gap-4">
        <MetricCard
          label="Thời gian xử lý TB"
          value={`${report.summary.avgProcessingDays.toFixed(1)} ngày`}
        />
        <MetricCard
          label="Tỷ lệ đúng hạn"
          value={`${(report.summary.onTimeRate * 100).toFixed(1)}%`}
          color={report.summary.onTimeRate >= 0.8 ? 'green' : 'yellow'}
        />
      </div>

      {/* Trends Chart Placeholder */}
      <Card title="Xu hướng">
        <div className="h-64 flex items-center justify-center text-gray-400">
          [Biểu đồ xu hướng]
        </div>
      </Card>

      {/* Overdue Table */}
      {report.overdue.length > 0 && (
        <Card title="Hồ sơ quá hạn">
          <table className="w-full">
            <thead>
              <tr className="text-left text-sm text-gray-500">
                <th>Cư dân</th>
                <th>Thủ tục</th>
                <th>Quá hạn</th>
                <th>Người xử lý</th>
              </tr>
            </thead>
            <tbody>
              {report.overdue.map((item) => (
                <tr key={item.applicationId} className="border-t">
                  <td>{item.residentName}</td>
                  <td>{item.procedureName}</td>
                  <td className="text-red-600">{item.daysOverdue} ngày</td>
                  <td>{item.assignedTo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

// Helper components
function SummaryCard({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="bg-white rounded-lg p-4 shadow-sm border">
      <div className="flex items-center gap-2">
        <span className="text-2xl">{icon}</span>
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-sm text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, color = 'gray' }: { label: string; value: string; color?: string }) {
  const colors = {
    green: 'bg-green-50 border-green-200 text-green-800',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    red: 'bg-red-50 border-red-200 text-red-800',
    gray: 'bg-gray-50 border-gray-200 text-gray-800',
  };
  return (
    <div className={`rounded-lg p-4 border ${colors[color]}`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-sm">{label}</p>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border">
      <h3 className="font-semibold p-4 border-b">{title}</h3>
      <div className="p-4">{children}</div>
    </div>
  );
}
```

- [ ] **Step 3: Create Report Filters component**

```typescript
// web/app/components/reports/ReportFilters.tsx
'use client';

import { useState } from 'react';
import { ReportFilters } from '@/lib/reports';

interface Props {
  onApply: (filters: ReportFilters) => void;
  departments: Array<{ id: number; name: string }>;
  staff: Array<{ id: number; name: string }>;
}

export function ReportFilters({ onApply, departments, staff }: Props) {
  const [filters, setFilters] = useState<ReportFilters>({
    dateRange: {
      from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      to: new Date().toISOString().split('T')[0],
    },
  });

  const handleApply = () => {
    onApply(filters);
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border p-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Date Range */}
        <div>
          <label className="block text-sm font-medium mb-1">Từ ngày</label>
          <input
            type="date"
            className="w-full border rounded px-3 py-2"
            value={filters.dateRange?.from || ''}
            onChange={(e) => setFilters({
              ...filters,
              dateRange: { ...filters.dateRange!, from: e.target.value }
            })}
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Đến ngày</label>
          <input
            type="date"
            className="w-full border rounded px-3 py-2"
            value={filters.dateRange?.to || ''}
            onChange={(e) => setFilters({
              ...filters,
              dateRange: { ...filters.dateRange!, to: e.target.value }
            })}
          />
        </div>

        {/* Department */}
        <div>
          <label className="block text-sm font-medium mb-1">Bộ phận</label>
          <select
            className="w-full border rounded px-3 py-2"
            onChange={(e) => setFilters({
              ...filters,
              department: e.target.value ? [parseInt(e.target.value)] : undefined
            })}
          >
            <option value="">Tất cả</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>

        {/* Staff */}
        <div>
          <label className="block text-sm font-medium mb-1">Nhân viên</label>
          <select
            className="w-full border rounded px-3 py-2"
            onChange={(e) => setFilters({
              ...filters,
              staff: e.target.value ? [parseInt(e.target.value)] : undefined
            })}
          >
            <option value="">Tất cả</option>
            {staff.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        {/* Status */}
        <div>
          <label className="block text-sm font-medium mb-1">Trạng thái</label>
          <select
            className="w-full border rounded px-3 py-2"
            onChange={(e) => setFilters({
              ...filters,
              status: e.target.value ? [e.target.value] : undefined
            })}
          >
            <option value="">Tất cả</option>
            <option value="received">Đã tiếp nhận</option>
            <option value="processing">Đang xử lý</option>
            <option value="needs_info">Cần bổ sung</option>
            <option value="approved">Đã duyệt</option>
            <option value="rejected">Từ chối</option>
          </select>
        </div>

        {/* Overdue Toggle */}
        <div className="flex items-end">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.overdue || false}
              onChange={(e) => setFilters({ ...filters, overdue: e.target.checked })}
            />
            <span className="text-sm">Chỉ quá hạn</span>
          </label>
        </div>
      </div>

      <div className="mt-4 flex justify-end gap-2">
        <button
          className="px-4 py-2 border rounded hover:bg-gray-50"
          onClick={() => setFilters({ dateRange: { from: '', to: '' } })}
        >
          Đặt lại
        </button>
        <button
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          onClick={handleApply}
        >
          Áp dụng
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create Export Buttons component**

```typescript
// web/app/components/reports/ExportButtons.tsx
'use client';

import { ReportFilters } from '@/lib/reports';

interface Props {
  filters: ReportFilters;
  reportType: 'operational' | 'staff' | 'department';
}

export function ExportButtons({ filters, reportType }: Props) {
  const buildUrl = (format: 'excel' | 'pdf') => {
    const params = new URLSearchParams({ format, type: reportType });
    if (filters.dateRange?.from) params.set('from', filters.dateRange.from);
    if (filters.dateRange?.to) params.set('to', filters.dateRange.to);
    // ... other filters
    return `/api/v1/admin/reports/export?${params}`;
  };

  return (
    <div className="flex gap-2">
      <a
        href={buildUrl('excel')}
        className="px-4 py-2 border rounded hover:bg-gray-50 flex items-center gap-2"
      >
        <span>📊</span> Xuất Excel
      </a>
      <a
        href={buildUrl('pdf')}
        className="px-4 py-2 border rounded hover:bg-gray-50 flex items-center gap-2"
      >
        <span>📄</span> Xuất PDF
      </a>
    </div>
  );
}
```

- [ ] **Step 5: Create Reports page**

```typescript
// web/app/bql/reports/page.tsx
'use client';

import { useState } from 'react';
import { OperationalReport, fetchOperationalReport } from '@/lib/reports';
import { OperationalReportView } from '@/components/reports/OperationalReport';
import { ReportFilters } from '@/components/reports/ReportFilters';
import { ExportButtons } from '@/components/reports/ExportButtons';

type Tab = 'operational' | 'staff' | 'department';

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('operational');
  const [report, setReport] = useState<OperationalReport | null>(null);
  const [filters, setFilters] = useState<ReportFilters | null>(null);
  const [loading, setLoading] = useState(false);

  const handleApplyFilters = async (newFilters: ReportFilters) => {
    setLoading(true);
    setFilters(newFilters);
    try {
      const data = await fetchOperationalReport(newFilters);
      setReport(data);
    } catch (error) {
      console.error('Failed to fetch report:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Báo cáo</h1>
        {filters && <ExportButtons filters={filters} reportType={activeTab} />}
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-4">
          {[
            { id: 'operational', label: 'Vận hành' },
            { id: 'staff', label: 'Nhân viên' },
            { id: 'department', label: 'Bộ phận' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as Tab)}
              className={`py-3 px-1 border-b-2 ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Filters */}
      <ReportFilters
        onApply={handleApplyFilters}
        departments={[]}  // TODO: fetch from API
        staff={[]}  // TODO: fetch from API
      />

      {/* Report Content */}
      {loading && <div className="text-center py-8">Đang tải...</div>}
      {report && activeTab === 'operational' && (
        <OperationalReportView report={report} />
      )}
    </div>
  );
}
```

- [ ] **Step 6: Commit**

```bash
git add web/app/bql/reports/page.tsx web/app/components/reports/
git commit -m "feat: dashboard reports UI (operational, staff, department)"
```

---

## Task 2: System Settings UI

**Files:**
- Create: `web/app/bql/settings/page.tsx`
- Create: `web/app/components/settings/StaffManagement.tsx`
- Create: `web/app/components/settings/DepartmentManagement.tsx`
- Create: `web/app/components/settings/SlaConfig.tsx`
- Test: `tests/settings.test.tsx`

### Steps

- [ ] **Step 1: Create Settings page with tabs**

```typescript
// web/app/bql/settings/page.tsx
'use client';

import { useState } from 'react';
import { StaffManagement } from '@/components/settings/StaffManagement';
import { DepartmentManagement } from '@/components/settings/DepartmentManagement';
import { SlaConfig } from '@/components/settings/SlaConfig';

type SettingsTab = 'staff' | 'departments' | 'procedures' | 'notifications' | 'security' | 'sla';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('staff');

  const tabs = [
    { id: 'staff', label: 'Nhân viên', icon: '👥' },
    { id: 'departments', label: 'Bộ phận', icon: '🏢' },
    { id: 'procedures', label: 'Quy trình', icon: '📋' },
    { id: 'notifications', label: 'Thông báo', icon: '🔔' },
    { id: 'security', label: 'Bảo mật', icon: '🔒' },
    { id: 'sla', label: 'SLA', icon: '⏱️' },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Cài đặt hệ thống</h1>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-1 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as SettingsTab)}
              className={`flex items-center gap-2 py-3 px-4 border-b-2 whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === 'staff' && <StaffManagement />}
        {activeTab === 'departments' && <DepartmentManagement />}
        {activeTab === 'sla' && <SlaConfig />}
        {activeTab === 'procedures' && <ProceduresSettings />}
        {activeTab === 'notifications' && <NotificationSettings />}
        {activeTab === 'security' && <SecuritySettings />}
      </div>
    </div>
  );
}

// Placeholders for other tabs
function ProceduresSettings() {
  return <div className="text-gray-500">Cấu hình quy trình hồ sơ...</div>;
}

function NotificationSettings() {
  return <div className="text-gray-500">Cấu hình thông báo...</div>;
}

function SecuritySettings() {
  return <div className="text-gray-500">Cấu hình bảo mật...</div>;
}
```

- [ ] **Step 2: Create Staff Management component**

```typescript
// web/app/components/settings/StaffManagement.tsx
'use client';

import { useState } from 'react';

interface Staff {
  id: number;
  fullName: string;
  email: string;
  role: 'staff' | 'manager' | 'admin';
  department: string | null;
  accountStatus: 'active' | 'locked';
}

export function StaffManagement() {
  const [staff, setStaff] = useState<Staff[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  // TODO: fetch staff list

  const handleCreateStaff = async (data: Partial<Staff>) => {
    // TODO: API call
    console.log('Create staff:', data);
  };

  const handleToggleLock = async (staffId: number, locked: boolean) => {
    // TODO: API call
    console.log('Toggle lock:', staffId, locked);
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-gray-600">Quản lý tài khoản nhân viên và phân công công việc.</p>
        <button
          onClick={() => setShowCreateDialog(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-2"
        >
          <span>+</span> Thêm nhân viên
        </button>
      </div>

      {/* Staff Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Họ tên</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Email</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Vai trò</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Bộ phận</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Trạng thái</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Thao tác</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  Đang tải...
                </td>
              </tr>
            ) : staff.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  Chưa có nhân viên nào
                </td>
              </tr>
            ) : (
              staff.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{s.fullName}</td>
                  <td className="px-4 py-3 text-gray-500">{s.email}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-sm ${
                      s.role === 'admin' ? 'bg-purple-100 text-purple-800' :
                      s.role === 'manager' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {s.role === 'admin' ? 'Quản trị' :
                       s.role === 'manager' ? 'Quản lý' : 'Nhân viên'}
                    </span>
                  </td>
                  <td className="px-4 py-3">{s.department || '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-sm ${
                      s.accountStatus === 'active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {s.accountStatus === 'active' ? 'Hoạt động' : 'Đã khóa'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleToggleLock(s.id, s.accountStatus !== 'locked')}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      {s.accountStatus === 'locked' ? 'Mở khóa' : 'Khóa'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create Dialog */}
      {showCreateDialog && (
        <CreateStaffDialog
          onClose={() => setShowCreateDialog(false)}
          onCreate={handleCreateStaff}
        />
      )}
    </div>
  );
}

// Create Staff Dialog
function CreateStaffDialog({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (data: Partial<Staff>) => void;
}) {
  const [form, setForm] = useState({
    fullName: '',
    email: '',
    role: 'staff' as const,
    department: '',
  });

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-md p-6">
        <h2 className="text-lg font-semibold mb-4">Thêm nhân viên mới</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Họ tên</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2"
              value={form.fullName}
              onChange={(e) => setForm({ ...form, fullName: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              className="w-full border rounded px-3 py-2"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Vai trò</label>
            <select
              className="w-full border rounded px-3 py-2"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as any })}
            >
              <option value="staff">Nhân viên</option>
              <option value="manager">Quản lý</option>
              <option value="admin">Quản trị viên</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="px-4 py-2 border rounded hover:bg-gray-50">
            Hủy
          </button>
          <button
            onClick={() => onCreate(form)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Tạo tài khoản
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create Department Management component**

```typescript
// web/app/components/settings/DepartmentManagement.tsx
'use client';

import { useState } from 'react';

interface Department {
  id: number;
  name: string;
  description: string;
  leadUser: { id: number; name: string } | null;
  staffCount: number;
}

export function DepartmentManagement() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  // TODO: fetch departments

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-gray-600">Quản lý bộ phận xử lý hồ sơ.</p>
        <button
          onClick={() => setShowCreateDialog(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-2"
        >
          <span>+</span> Thêm bộ phận
        </button>
      </div>

      {/* Department Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {departments.map((dept) => (
          <div key={dept.id} className="bg-white rounded-lg shadow p-4">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-semibold text-lg">{dept.name}</h3>
                <p className="text-gray-500 text-sm">{dept.description}</p>
              </div>
              <button className="text-blue-600 hover:text-blue-700 text-sm">
                Chỉnh sửa
              </button>
            </div>
            <div className="mt-4 flex gap-4 text-sm">
              <div>
                <span className="text-gray-500">Trưởng bộ phận:</span>{' '}
                <span className="font-medium">{dept.leadUser?.name || 'Chưa có'}</span>
              </div>
              <div>
                <span className="text-gray-500">Nhân viên:</span>{' '}
                <span className="font-medium">{dept.staffCount}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create SLA Configuration component**

```typescript
// web/app/components/settings/SlaConfig.tsx
'use client';

import { useState } from 'react';

interface SlaConfig {
  defaultProcessingDays: number;
  warningDaysBefore: number;
  escalationDays: number;
  autoEscalateToManager: boolean;
}

export function SlaConfig() {
  const [config, setConfig] = useState<SlaConfig>({
    defaultProcessingDays: 7,
    warningDaysBefore: 3,
    escalationDays: 14,
    autoEscalateToManager: true,
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    // TODO: API call
    await new Promise((r) => setTimeout(r, 500));
    setSaving(false);
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <p className="text-gray-600">
        Cấu hình thời gian xử lý mặc định và quy tắc tự động nhắc nhở.
      </p>

      <div className="bg-white rounded-lg shadow space-y-4 p-6">
        <div>
          <label className="block text-sm font-medium mb-1">
            Thời gian xử lý mặc định (ngày)
          </label>
          <input
            type="number"
            min={1}
            className="w-full border rounded px-3 py-2"
            value={config.defaultProcessingDays}
            onChange={(e) => setConfig({
              ...config,
              defaultProcessingDays: parseInt(e.target.value) || 1
            })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">
            Nhắc trước khi hết hạn (ngày)
          </label>
          <input
            type="number"
            min={1}
            className="w-full border rounded px-3 py-2"
            value={config.warningDaysBefore}
            onChange={(e) => setConfig({
              ...config,
              warningDaysBefore: parseInt(e.target.value) || 1
            })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">
            Thời hạn chuyển cấp (ngày)
          </label>
          <input
            type="number"
            min={1}
            className="w-full border rounded px-3 py-2"
            value={config.escalationDays}
            onChange={(e) => setConfig({
              ...config,
              escalationDays: parseInt(e.target.value) || 1
            })}
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="autoEscalate"
            checked={config.autoEscalateToManager}
            onChange={(e) => setConfig({
              ...config,
              autoEscalateToManager: e.target.checked
            })}
          />
          <label htmlFor="autoEscalate" className="text-sm">
            Tự động chuyển cấp cho trưởng bộ phận khi quá hạn
          </label>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Đang lưu...' : 'Lưu cấu hình'}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add web/app/bql/settings/page.tsx web/app/components/settings/
git commit -m "feat: system settings UI (staff, departments, SLA)"
```

---

## Task 3: Notifications UI

**Files:**
- Create: `web/app/components/NotificationsBell.tsx`
- Create: `web/app/components/NotificationsPanel.tsx`
- Modify: `web/app/components/Header.tsx` (add notifications bell)
- Test: `tests/notifications.test.tsx`

### Steps

- [ ] **Step 1: Create Notifications types and API**

```typescript
// web/lib/notifications.ts
export interface Notification {
  id: number;
  type: string;
  title: string;
  body: string | null;
  data: Record<string, any> | null;
  isRead: boolean;
  createdAt: string;
}

export async function fetchNotifications(): Promise<Notification[]> {
  const response = await fetch('/api/v1/notifications');
  if (!response.ok) throw new Error('Failed to fetch notifications');
  return response.json();
}

export async function markNotificationRead(id: number): Promise<void> {
  await fetch(`/api/v1/notifications/${id}/read`, { method: 'PATCH' });
}

export async function markAllNotificationsRead(): Promise<void> {
  await fetch('/api/v1/notifications/read-all', { method: 'PATCH' });
}
```

- [ ] **Step 2: Create Notifications Bell component**

```typescript
// web/app/components/NotificationsBell.tsx
'use client';

import { useState, useEffect } from 'react';
import { Notification, fetchNotifications } from '@/lib/notifications';
import { NotificationsPanel } from './NotificationsPanel';

export function NotificationsBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showPanel, setShowPanel] = useState(false);
  const [loading, setLoading] = useState(false);

  const unreadCount = notifications.filter((n) => !n.isRead).length;

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const data = await fetchNotifications();
      setNotifications(data);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications();
    // Poll every 30 seconds
    const interval = setInterval(loadNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative">
      <button
        onClick={() => setShowPanel(!showPanel)}
        className="relative p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-full"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>

        {/* Badge */}
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Panel */}
      {showPanel && (
        <NotificationsPanel
          notifications={notifications}
          onClose={() => setShowPanel(false)}
          onRefresh={loadNotifications}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create Notifications Panel component**

```typescript
// web/app/components/NotificationsPanel.tsx
'use client';

import { useState } from 'react';
import { Notification, markNotificationRead, markAllNotificationsRead } from '@/lib/notifications';
import { formatDistanceToNow } from '@/lib/utils';

interface Props {
  notifications: Notification[];
  onClose: () => void;
  onRefresh: () => void;
}

export function NotificationsPanel({ notifications, onClose, onRefresh }: Props) {
  const [loading, setLoading] = useState<number | null>(null);

  const handleMarkRead = async (id: number) => {
    setLoading(id);
    try {
      await markNotificationRead(id);
      onRefresh();
    } finally {
      setLoading(null);
    }
  };

  const handleMarkAllRead = async () => {
    setLoading(-1);
    try {
      await markAllNotificationsRead();
      onRefresh();
    } finally {
      setLoading(null);
    }
  };

  const getNotificationIcon = (type: string) => {
    const icons: Record<string, string> = {
      application_status: '📋',
      application_approved: '✅',
      application_rejected: '❌',
      application_needs_info: '📝',
      ticket_reply: '💬',
      checklist_reminder: '⏰',
      checklist_overdue: '⚠️',
    };
    return icons[type] || '🔔';
  };

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40" onClick={onClose} />

      {/* Panel */}
      <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-lg shadow-lg border z-50">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold">Thông báo</h3>
          {notifications.some((n) => !n.isRead) && (
            <button
              onClick={handleMarkAllRead}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              Đánh dấu đã đọc
            </button>
          )}
        </div>

        <div className="max-h-96 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <p>Không có thông báo nào</p>
            </div>
          ) : (
            notifications.map((notification) => (
              <div
                key={notification.id}
                className={`p-4 border-b hover:bg-gray-50 cursor-pointer ${
                  !notification.isRead ? 'bg-blue-50/50' : ''
                }`}
                onClick={() => {
                  if (!notification.isRead) handleMarkRead(notification.id);
                  // Navigate to notification.data.url
                }}
              >
                <div className="flex gap-3">
                  <span className="text-xl">{getNotificationIcon(notification.type)}</span>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm">{notification.title}</p>
                    {notification.body && (
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                        {notification.body}
                      </p>
                    )}
                    <p className="text-xs text-gray-400 mt-1">
                      {formatDistanceToNow(notification.createdAt)}
                    </p>
                  </div>
                  {!notification.isRead && (
                    <span className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0" />
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="p-3 border-t text-center">
          <button className="text-sm text-blue-600 hover:text-blue-700">
            Xem tất cả thông báo
          </button>
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 4: Modify Header to include Notifications Bell**

```typescript
// In web/app/components/Header.tsx, add:
import { NotificationsBell } from './NotificationsBell';

// In the header, add the bell next to profile:
<div className="flex items-center gap-4">
  <NotificationsBell />
  {/* existing profile button */}
</div>
```

- [ ] **Step 5: Add Push subscription registration**

```typescript
// web/lib/push.ts
export async function requestPushPermission(): Promise<boolean> {
  if (!('Notification' in window) || !('serviceWorker' in navigator)) {
    return false;
  }

  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    return false;
  }

  const registration = await navigator.serviceWorker.ready;
  const vapidPublicKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
  
  if (!vapidPublicKey) {
    console.warn('VAPID public key not configured');
    return false;
  }

  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
  });

  // Send subscription to backend
  const response = await fetch('/api/v1/push/subscriptions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      endpoint: subscription.endpoint,
      keys: {
        p256dh: subscription.getKey('p256dh'),
        auth: subscription.getKey('auth'),
      },
      user_agent: navigator.userAgent,
    }),
  });

  return response.ok;
}

// Helper function
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}
```

- [ ] **Step 6: Commit**

```bash
git add web/app/components/NotificationsBell.tsx web/app/components/NotificationsPanel.tsx web/lib/notifications.ts web/lib/push.ts
git commit -m "feat: notifications UI with push subscription"
```

---

## Task 4: Gamification

**Files:**
- Create: `web/app/components/Gamification.tsx`
- Create: `web/app/components/BadgeDisplay.tsx`
- Modify: `web/app/dashboard/page.tsx` (add gamification section)
- Test: `tests/gamification.test.tsx`

### Steps

- [ ] **Step 1: Create badge definitions**

```typescript
// web/lib/gamification.ts
export interface Badge {
  id: string;
  name: string;
  icon: string;
  description: string;
  condition: string;
}

export const BADGES: Badge[] = [
  {
    id: 'first_step',
    name: 'Bước đầu tiên',
    icon: '🎯',
    description: 'Hoàn thành mục checklist đầu tiên',
    condition: 'Complete 1 checklist item',
  },
  {
    id: 'half_way',
    name: 'Tiến một nửa',
    icon: '📊',
    description: 'Đạt 50% tiến độ checklist',
    condition: '50% checklist complete',
  },
  {
    id: 'resident_card',
    name: 'Thẻ cư dân',
    icon: '🏠',
    description: 'Được duyệt thẻ cư dân',
    condition: 'Resident card approved',
  },
  {
    id: 'vehicle_card',
    name: 'Thẻ xe',
    icon: '🚗',
    description: 'Được duyệt thẻ xe',
    condition: 'Vehicle card approved',
  },
  {
    id: 'all_done',
    name: 'Hoàn tất',
    icon: '🎉',
    description: 'Hoàn thành 100% checklist',
    condition: '100% checklist complete',
  },
  {
    id: 'fast_track',
    name: 'Nhanh như chớp',
    icon: '⚡',
    description: 'Hoàn thành trong 7 ngày',
    condition: 'Complete within 7 days',
  },
];

export function getBadgeById(id: string): Badge | undefined {
  return BADGES.find((b) => b.id === id);
}

export interface UserBadge {
  badgeId: string;
  earnedAt: string;
}

export async function fetchUserBadges(): Promise<UserBadge[]> {
  const response = await fetch('/api/v1/user/badges');
  if (!response.ok) throw new Error('Failed to fetch badges');
  return response.json();
}
```

- [ ] **Step 2: Create Badge Display component**

```typescript
// web/app/components/BadgeDisplay.tsx
'use client';

import { BADGES, Badge, UserBadge, getBadgeById } from '@/lib/gamification';

interface Props {
  earnedBadges: UserBadge[];
  progress?: number; // 0-100
}

export function BadgeDisplay({ earnedBadges, progress }: Props) {
  const earnedIds = new Set(earnedBadges.map((b) => b.badgeId));

  return (
    <div className="space-y-4">
      {/* Progress Bar */}
      {progress !== undefined && (
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">Tiến độ</span>
            <span className="font-medium">{progress}%</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Badges Grid */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-4">
        {BADGES.map((badge) => {
          const earned = earnedIds.has(badge.id);
          const earnedBadge = earnedBadges.find((b) => b.badgeId === badge.id);

          return (
            <div
              key={badge.id}
              className={`relative flex flex-col items-center p-3 rounded-lg border ${
                earned
                  ? 'bg-gradient-to-b from-yellow-50 to-yellow-100 border-yellow-200'
                  : 'bg-gray-50 border-gray-200 opacity-50'
              }`}
              title={badge.description}
            >
              <span className="text-3xl">{badge.icon}</span>
              <span className={`text-xs mt-1 text-center ${earned ? 'font-medium' : 'text-gray-500'}`}>
                {badge.name}
              </span>

              {/* Lock icon for unearned */}
              {!earned && (
                <span className="absolute top-1 right-1 text-gray-400">🔒</span>
              )}

              {/* Earned indicator */}
              {earned && (
                <span className="absolute -top-1 -right-1 text-green-500">✅</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create Badge Earned Celebration**

```typescript
// web/app/components/BadgeCelebration.tsx
'use client';

import { useEffect, useState } from 'react';
import { Badge } from '@/lib/gamification';

interface Props {
  badge: Badge;
  onClose: () => void;
}

export function BadgeCelebration({ badge, onClose }: Props) {
  const [show, setShow] = useState(true);

  useEffect(() => {
    // Auto-close after 5 seconds
    const timer = setTimeout(() => {
      setShow(false);
      setTimeout(onClose, 500); // Wait for animation
    }, 5000);

    return () => clearTimeout(timer);
  }, [onClose]);

  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 animate-pulse" />

      {/* Content */}
      <div className="relative bg-white rounded-2xl p-8 max-w-sm mx-4 text-center animate-bounce-in">
        <div className="text-6xl mb-4">{badge.icon}</div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          🎉 Chúc mừng!
        </h2>
        <p className="text-lg text-gray-600 mb-2">
          Bạn đã đạt được huy hiệu
        </p>
        <p className="text-xl font-semibold text-blue-600 mb-6">
          {badge.name}
        </p>
        <p className="text-sm text-gray-500 mb-6">
          {badge.description}
        </p>
        <button
          onClick={() => {
            setShow(false);
            setTimeout(onClose, 300);
          }}
          className="px-6 py-2 bg-blue-600 text-white rounded-full hover:bg-blue-700"
        >
          Tiếp tục
        </button>
      </div>

      <style jsx>{`
        @keyframes bounce-in {
          0% {
            transform: scale(0.5);
            opacity: 0;
          }
          50% {
            transform: scale(1.1);
          }
          100% {
            transform: scale(1);
            opacity: 1;
          }
        }
        .animate-bounce-in {
          animation: bounce-in 0.5s ease-out;
        }
      `}</style>
    </div>
  );
}
```

- [ ] **Step 4: Integrate into Dashboard**

```typescript
// In web/app/dashboard/page.tsx, add gamification section:
// (This would be added to the existing dashboard)

import { BadgeDisplay } from '@/components/BadgeDisplay';

// Inside the dashboard, add:
<BadgeDisplay
  earnedBadges={userBadges}
  progress={checklistProgress}
/>
```

- [ ] **Step 5: Commit**

```bash
git add web/app/components/Gamification.tsx web/app/components/BadgeDisplay.tsx web/app/components/BadgeCelebration.tsx web/lib/gamification.ts
git commit -m "feat: gamification with badges and celebrations"
```

---

## Task Dependencies Summary

| Task | Dependencies |
|---|---|
| 1. Dashboard Reports | Backend: Report API |
| 2. Settings UI | Backend: Settings API |
| 3. Notifications UI | Backend: Notifications API, Push subscription |
| 4. Gamification | Backend: Badges API |

---

**Plan complete.** Ready for subagent-driven or inline execution.
