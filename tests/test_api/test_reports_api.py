"""Test tầng API cho báo cáo, cấu hình và huy hiệu.

Phần tính toán đã có test riêng (`tests/test_services/`). Ở đây chỉ canh những
thứ chỉ tầng HTTP mới sai được: phân quyền, mã lỗi, và hình dạng JSON trả về.
"""

import pytest

ADMIN = {"X-User-Id": "1"}
OWNER = {"X-User-Id": "2"}
RENTER = {"X-User-Id": "3"}

REPORT_PATHS = [
    "/api/v1/admin/applications/report",
    "/api/v1/admin/departments/report",
    "/api/v1/admin/staff/report",
]


class TestReportPermissions:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", REPORT_PATHS)
    async def test_admin_can_read(self, client, path):
        assert (await client.get(path, headers=ADMIN)).status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", REPORT_PATHS)
    async def test_resident_forbidden(self, client, path):
        """Cư dân KHÔNG được xem báo cáo vận hành của toàn toà nhà."""
        assert (await client.get(path, headers=OWNER)).status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", REPORT_PATHS)
    async def test_anonymous_rejected(self, client, path):
        assert (await client.get(path)).status_code in (401, 403)


class TestApplicationsReportApi:
    @pytest.mark.asyncio
    async def test_shape_on_empty_data(self, client):
        """DB chưa có hồ sơ nào vẫn trả đủ khối, không 404 và không lỗi."""
        body = (await client.get(REPORT_PATHS[0], headers=ADMIN)).json()

        assert body["summary"]["total"] == 0
        assert body["summary"]["onTimeRate"] is None
        assert body["coverage"]["measurable"] == 0
        assert body["overdue"] == []

    @pytest.mark.asyncio
    async def test_bad_date_returns_422_not_500(self, client):
        """Lỗi của người gọi phải là 422, không phải 500."""
        response = await client.get(
            f"{REPORT_PATHS[0]}?date_from=hom-qua", headers=ADMIN
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reversed_period_rejected(self, client):
        response = await client.get(
            f"{REPORT_PATHS[0]}?date_from=2026-09-01&date_to=2026-08-01", headers=ADMIN
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_blank_date_accepted(self, client):
        """Ô lọc bị xoá trống gửi lên `?date_from=` — không được thành lỗi."""
        response = await client.get(f"{REPORT_PATHS[0]}?date_from=", headers=ADMIN)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_overdue_limit_validated(self, client):
        response = await client.get(f"{REPORT_PATHS[0]}?overdue_limit=0", headers=ADMIN)
        assert response.status_code == 422


class TestStaffReportApi:
    @pytest.mark.asyncio
    async def test_declares_basis(self, client):
        """`basis` phải có trong kết quả — giao diện cần nó để chú thích đúng
        rằng đây là hồ sơ được GÁN, không phải ai thao tác."""
        body = (await client.get(REPORT_PATHS[2], headers=ADMIN)).json()
        assert body["basis"] == "assigned_to"
        assert "unassigned" in body


class TestSettingsApi:
    @pytest.mark.asyncio
    async def test_get_returns_defaults(self, client):
        body = (await client.get("/api/v1/admin/settings", headers=ADMIN)).json()
        assert body["reports"]["defaultPeriodDays"] == 30

    @pytest.mark.asyncio
    async def test_patch_updates(self, client):
        response = await client.patch(
            "/api/v1/admin/settings",
            headers=ADMIN,
            json={"reports": {"defaultPeriodDays": 60}},
        )
        assert response.status_code == 200
        assert response.json()["reports"]["defaultPeriodDays"] == 60

    @pytest.mark.asyncio
    async def test_patch_persists(self, client):
        await client.patch(
            "/api/v1/admin/settings",
            headers=ADMIN,
            json={"reports": {"defaultPeriodDays": 60}},
        )
        body = (await client.get("/api/v1/admin/settings", headers=ADMIN)).json()
        assert body["reports"]["defaultPeriodDays"] == 60

    @pytest.mark.asyncio
    async def test_unknown_key_rejected(self, client):
        response = await client.patch(
            "/api/v1/admin/settings", headers=ADMIN, json={"reports": {"khongCo": 1}}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_out_of_range_rejected(self, client):
        response = await client.patch(
            "/api/v1/admin/settings",
            headers=ADMIN,
            json={"reports": {"overdueWarningDays": 99}},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_resident_cannot_read_or_write(self, client):
        assert (await client.get("/api/v1/admin/settings", headers=OWNER)).status_code == 403
        response = await client.patch(
            "/api/v1/admin/settings", headers=OWNER, json={"reports": {"defaultPeriodDays": 60}}
        )
        assert response.status_code == 403


class TestUserBadgesApi:
    @pytest.mark.asyncio
    async def test_lists_all_badges(self, client):
        body = (await client.get("/api/v1/user/badges", headers=RENTER)).json()
        assert body["totalCount"] == 6
        assert body["earnedCount"] == 0
        assert len(body["badges"]) == 6

    @pytest.mark.asyncio
    async def test_unearned_badge_shape(self, client):
        body = (await client.get("/api/v1/user/badges", headers=RENTER)).json()
        badge = body["badges"][0]
        assert badge["isEarned"] is False
        assert badge["earnedAt"] is None
        assert badge["icon"]

    @pytest.mark.asyncio
    async def test_admin_cannot_read_resident_badges(self, client):
        """Endpoint dành cho cư dân; BQL không có huy hiệu."""
        assert (await client.get("/api/v1/user/badges", headers=ADMIN)).status_code == 403


class TestBadgeAwardingThroughApi:
    @pytest.mark.asyncio
    async def test_tick_awards_first_step(self, client, db_session):
        """Tick một mục → badge xuất hiện trong `newly_earned_badges`.

        Đây là ca chính của móc nối: trao badge phải xảy ra ở ĐƯỜNG GHI, không
        phải lúc đọc.
        """
        from src.models.db import ChecklistCompletion

        db_session.query(ChecklistCompletion).delete()
        db_session.commit()

        item_id = (await client.get("/api/v1/checklist", headers=OWNER)).json()["items"][0]["id"]
        body = (
            await client.patch(
                f"/api/v1/checklist/{item_id}", headers=OWNER, json={"completed": True}
            )
        ).json()
        assert "first_step" in body["newly_earned_badges"]

    @pytest.mark.asyncio
    async def test_badge_visible_after_tick(self, client, db_session):
        from src.models.db import ChecklistCompletion

        db_session.query(ChecklistCompletion).delete()
        db_session.commit()

        item_id = (await client.get("/api/v1/checklist", headers=OWNER)).json()["items"][0]["id"]
        await client.patch(
            f"/api/v1/checklist/{item_id}", headers=OWNER, json={"completed": True}
        )

        body = (await client.get("/api/v1/user/badges", headers=OWNER)).json()
        first_step = next(b for b in body["badges"] if b["key"] == "first_step")
        assert first_step["isEarned"] is True

    @pytest.mark.asyncio
    async def test_second_tick_awards_nothing_new(self, client):
        """Badge đã trao không trao lại — `newly_earned_badges` rỗng."""
        items = (await client.get("/api/v1/checklist", headers=OWNER)).json()["items"]
        await client.patch(
            f"/api/v1/checklist/{items[0]['id']}", headers=OWNER, json={"completed": True}
        )
        body = (
            await client.patch(
                f"/api/v1/checklist/{items[1]['id']}", headers=OWNER, json={"completed": True}
            )
        ).json()
        assert "first_step" not in body["newly_earned_badges"]

    @pytest.mark.asyncio
    async def test_untick_returns_empty_list(self, client):
        items = (await client.get("/api/v1/checklist", headers=OWNER)).json()["items"]
        body = (
            await client.patch(
                f"/api/v1/checklist/{items[0]['id']}", headers=OWNER, json={"completed": False}
            )
        ).json()
        assert body["newly_earned_badges"] == []

    @pytest.mark.asyncio
    async def test_get_checklist_never_reports_new_badges(self, client):
        """GET không biết cái gì là 'vừa mới' — luôn rỗng."""
        body = (await client.get("/api/v1/checklist", headers=OWNER)).json()
        assert body["newly_earned_badges"] == []
