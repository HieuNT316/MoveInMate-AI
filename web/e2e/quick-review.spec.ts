import { expect, test } from "@playwright/test";

const application = {
  application_id: 91,
  checklist_item_id: 8,
  user_id: 2,
  full_name: "Nguyễn Văn An",
  apartment: "A-1205",
  task_name: "Đăng ký thẻ cư dân",
  status: "received",
  kind: "bql_processing",
  attachments: [],
  missing_documents: [{ code: "cccd", label: "Căn cước công dân" }],
  unlabelled_count: 0,
  handling_department: "Lễ tân",
  submission_location: "Quầy BQL",
  processing_time: "2 ngày",
  note: null,
  bql_note: null,
  created_at: "2026-08-20T08:00:00Z",
  updated_at: "2026-08-20T08:00:00Z",
};

test("BQL mở được hàng đợi và panel duyệt nhanh", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("moveinmate.demo-user-id", "1"));
  await page.route("**/api/v1/**", async (route) => {
    const url = route.request().url();
    if (url.includes("/admin/applications")) return route.fulfill({ json: [application] });
    if (url.includes("/profile")) return route.fulfill({ json: { user_id: 1, full_name: "Ban quản lý", email: "bql@example.com", apartment: "BQL", building: "BQL", role: "admin", ownership_type: null, apartment_type: null, has_car: null, amenity_packages: [], onboarding_completed_at: null } });
    if (url.includes("/notifications")) return route.fulfill({ json: [] });
    return route.fulfill({ json: [] });
  });

  await page.goto("/bql/applications");
  await expect(page.getByRole("button", { name: "Chờ duyệt" })).toBeVisible();
  await expect(page.getByText("Đăng ký thẻ cư dân")).toBeVisible();
  await page.getByRole("button", { name: /Xem hồ sơ/ }).click();
  await expect(page.getByRole("dialog", { name: "Duyệt nhanh hồ sơ" })).toBeVisible();
  await expect(page.getByText("Thiếu Căn cước công dân")).toBeVisible();
  await expect(page.getByRole("button", { name: "Lưu và hồ sơ tiếp theo" })).toBeVisible();
});
