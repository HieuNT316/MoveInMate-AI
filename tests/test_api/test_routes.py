"""Test luồng API — chạy đúng kịch bản demo GATE 2.

Người dùng seed sẵn: 1 = BQL, 2 = chủ hộ đã onboarding, 3 = người thuê chưa
onboarding.
"""

import pytest

ADMIN = {"X-User-Id": "1"}
OWNER = {"X-User-Id": "2"}
RENTER = {"X-User-Id": "3"}

RENTER_PROFILE = {
    "ownership_type": "renter",
    "apartment_type": "1pn",
    "has_car": False,
    "amenity_packages": [],
}


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_khong_co_header_thi_bi_tu_choi(client):
    assert (await client.get("/api/v1/checklist")).status_code == 422


@pytest.mark.asyncio
async def test_user_khong_ton_tai_tra_401(client):
    response = await client.get("/api/v1/profile", headers={"X-User-Id": "999"})
    assert response.status_code == 401


# --- Onboarding ---------------------------------------------------------


@pytest.mark.asyncio
async def test_chua_onboarding_thi_profile_bao_null(client):
    """Frontend dựa vào tín hiệu này để chuyển hướng sang trang onboarding."""
    response = await client.get("/api/v1/profile", headers=RENTER)
    assert response.status_code == 200
    assert response.json()["onboarding_completed_at"] is None


@pytest.mark.asyncio
async def test_checklist_bao_ro_khi_chua_onboarding(client):
    """Không có cờ này thì frontend dễ hiển thị một checklist sai trông hợp lệ."""
    data = (await client.get("/api/v1/checklist", headers=RENTER)).json()
    assert data["onboarding_completed"] is False

    await client.post("/api/v1/onboarding", json=RENTER_PROFILE, headers=RENTER)
    after = (await client.get("/api/v1/checklist", headers=RENTER)).json()
    assert after["onboarding_completed"] is True


@pytest.mark.asyncio
async def test_onboarding_xong_thi_co_checklist(client):
    created = await client.post(
        "/api/v1/onboarding", json=RENTER_PROFILE, headers=RENTER
    )
    assert created.status_code == 200
    assert created.json()["onboarding_completed_at"] is not None

    checklist = await client.get("/api/v1/checklist", headers=RENTER)
    assert checklist.json()["overall"]["total"] > 0


@pytest.mark.asyncio
async def test_submit_lai_khong_ghi_de_moc_hoan_thanh_dau_tien(client):
    """Metric "% hoàn thành trong X ngày đầu" cần mốc đầu tiên, không phải lần cuối."""
    first = (
        await client.post("/api/v1/onboarding", json=RENTER_PROFILE, headers=RENTER)
    ).json()

    changed = {**RENTER_PROFILE, "has_car": True}
    second = (
        await client.post("/api/v1/onboarding", json=changed, headers=RENTER)
    ).json()

    assert second["onboarding_completed_at"] == first["onboarding_completed_at"]
    assert second["has_car"] is True  # hồ sơ vẫn được cập nhật


@pytest.mark.asyncio
async def test_goi_tien_ich_khong_hop_le_bi_tu_choi(client):
    """Giá trị lệch phải báo lỗi, không được âm thầm làm mục tiện ích biến mất."""
    payload = {**RENTER_PROFILE, "amenity_packages": ["swimming"]}
    response = await client.post("/api/v1/onboarding", json=payload, headers=RENTER)
    assert response.status_code == 422


# --- Cá nhân hóa --------------------------------------------------------


@pytest.mark.asyncio
async def test_chu_ho_va_nguoi_thue_nhan_checklist_khac_nhau(client):
    """Bước ăn điểm nhất của demo: cá nhân hóa theo tình huống từng hộ."""
    await client.post("/api/v1/onboarding", json=RENTER_PROFILE, headers=RENTER)

    owner_items = (await client.get("/api/v1/checklist", headers=OWNER)).json()["items"]
    renter_items = (await client.get("/api/v1/checklist", headers=RENTER)).json()["items"]

    owner_tasks = {item["task_name"] for item in owner_items}
    renter_tasks = {item["task_name"] for item in renter_items}

    assert "Làm thẻ cư dân (chủ hộ)" in owner_tasks
    assert "Làm thẻ cư dân (người thuê)" in renter_tasks
    # Chủ hộ có xe nên thấy mục thẻ xe; người thuê không xe thì không.
    assert "Đăng ký thẻ xe" in owner_tasks
    assert "Đăng ký thẻ xe" not in renter_tasks
    # Chỉ người thuê phải đăng ký tạm trú.
    assert "Đăng ký tạm trú tại công an phường" in renter_tasks
    assert "Đăng ký tạm trú tại công an phường" not in owner_tasks


@pytest.mark.asyncio
async def test_muc_ngoai_pham_vi_bql_duoc_danh_dau(client):
    """Frontend cần `item_type` để gắn nhãn quy trình ngoài BQL."""
    items = (await client.get("/api/v1/checklist", headers=OWNER)).json()["items"]
    assert [i for i in items if i["item_type"] == "third_party_info"]


# --- Tiến độ ------------------------------------------------------------


@pytest.mark.asyncio
async def test_tien_do_bql_khong_tinh_thu_tuc_ben_ngoai(client):
    """BQL không nên bị đánh giá vì thủ tục họ không xử lý được."""
    data = (await client.get("/api/v1/checklist", headers=OWNER)).json()
    third_party_count = sum(
        1 for i in data["items"] if i["item_type"] == "third_party_info"
    )

    assert third_party_count > 0
    assert data["bql_scope"]["total"] == data["overall"]["total"] - third_party_count


@pytest.mark.asyncio
async def test_tick_hoan_thanh_lam_tang_tien_do(client):
    before = (await client.get("/api/v1/checklist", headers=OWNER)).json()
    target = next(i for i in before["items"] if not i["completed"])

    response = await client.patch(
        f"/api/v1/checklist/{target['id']}", json={"completed": True}, headers=OWNER
    )
    assert response.status_code == 200
    after = response.json()

    assert after["overall"]["completed"] == before["overall"]["completed"] + 1
    assert after["overall"]["percent"] >= before["overall"]["percent"]


@pytest.mark.asyncio
async def test_bo_tick_lam_giam_tien_do(client):
    checklist = (await client.get("/api/v1/checklist", headers=OWNER)).json()
    done = next(i for i in checklist["items"] if i["completed"])

    after = (
        await client.patch(
            f"/api/v1/checklist/{done['id']}", json={"completed": False}, headers=OWNER
        )
    ).json()
    assert after["overall"]["completed"] == checklist["overall"]["completed"] - 1


@pytest.mark.asyncio
async def test_tick_muc_khong_ton_tai_tra_404(client):
    response = await client.patch(
        "/api/v1/checklist/9999", json={"completed": True}, headers=OWNER
    )
    assert response.status_code == 404


# --- Sửa hồ sơ ----------------------------------------------------------


@pytest.mark.asyncio
async def test_sua_ho_so_chi_can_gui_field_muon_doi(client):
    """PATCH đúng nghĩa: báo "vừa bán xe" không phải gửi lại cả hồ sơ."""
    before = (await client.get("/api/v1/profile", headers=OWNER)).json()

    response = await client.patch(
        "/api/v1/profile", json={"has_car": False}, headers=OWNER
    )
    assert response.status_code == 200
    after = response.json()

    assert after["has_car"] is False
    # Các field không gửi lên phải giữ nguyên.
    assert after["ownership_type"] == before["ownership_type"]
    assert after["apartment_type"] == before["apartment_type"]
    assert after["amenity_packages"] == before["amenity_packages"]


@pytest.mark.asyncio
async def test_sua_ho_so_thi_checklist_doi_theo(client):
    """Lọc trực tiếp nên không cần logic đồng bộ nào."""
    before = (await client.get("/api/v1/checklist", headers=OWNER)).json()

    await client.patch("/api/v1/profile", json={"has_car": False}, headers=OWNER)
    after = (await client.get("/api/v1/checklist", headers=OWNER)).json()

    assert after["overall"]["total"] < before["overall"]["total"]
    assert "Đăng ký thẻ xe" not in {i["task_name"] for i in after["items"]}


@pytest.mark.asyncio
async def test_sua_ho_so_rong_bi_tu_choi(client):
    response = await client.patch("/api/v1/profile", json={}, headers=OWNER)
    assert response.status_code == 400


# --- Hỏi đáp ------------------------------------------------------------


@pytest.mark.asyncio
async def test_hoi_dap_tra_ve_nguon_trich_dan(client):
    response = await client.post(
        "/api/v1/chat", json={"message": "Làm thẻ xe cần giấy tờ gì?"}, headers=OWNER
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer_source"] == "rag"
    assert data["sources"], "Câu trả lời phải kèm nguồn trích dẫn"
    assert data["sources"][0]["title"]


@pytest.mark.asyncio
async def test_hoi_dap_khop_ca_khi_go_khong_dau(client):
    """Người Việt hay gõ không dấu; không chuẩn hoá thì hệ thống từ chối nhầm."""
    response = await client.post(
        "/api/v1/chat",
        json={"message": "Toi can giay to gi de lam the xe?"},
        headers=OWNER,
    )
    data = response.json()
    assert data["answer_source"] == "rag"
    assert data["sources"]


@pytest.mark.asyncio
async def test_cau_hoi_ngoai_tai_lieu_thi_tu_choi_chu_khong_bia(client):
    """Ràng buộc của đề bài, và là bước ăn điểm thứ hai của demo."""
    response = await client.post(
        "/api/v1/chat", json={"message": "Giá vàng hôm nay bao nhiêu?"}, headers=OWNER
    )
    data = response.json()
    assert data["answer_source"] == "no_context"
    assert data["sources"] == []
    assert "Ban quản lý" in data["answer"]


@pytest.mark.asyncio
async def test_thu_tuc_ben_ngoai_trich_nguon_quy_dinh_cong_khai(client):
    """Không được mạo nhận quy trình của cơ quan khác là tài liệu nội bộ BQL."""
    response = await client.post(
        "/api/v1/chat", json={"message": "đăng ký tạm trú thế nào?"}, headers=RENTER
    )
    sources = response.json()["sources"]
    assert sources
    assert all(s["source_type"] == "public_regulation" for s in sources)


@pytest.mark.asyncio
async def test_lich_su_chat_chi_cua_chinh_minh(client):
    await client.post("/api/v1/chat", json={"message": "thẻ cư dân"}, headers=OWNER)

    mine = (await client.get("/api/v1/chat/history", headers=OWNER)).json()
    others = (await client.get("/api/v1/chat/history", headers=RENTER)).json()

    assert len(mine) == 1
    assert others == []


# --- Ban quản lý --------------------------------------------------------


@pytest.mark.asyncio
async def test_cu_dan_khong_vao_duoc_route_cua_bql(client):
    response = await client.get("/api/v1/admin/dashboard", headers=OWNER)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_bql_tao_tai_khoan_cu_dan(client):
    payload = {
        "full_name": "Phạm Văn Cường",
        "email": "cuong.pham@demo.vn",
        "apartment": "S3.02-1105",
        "building": "Sapphire 3",
    }
    response = await client.post("/api/v1/admin/users", json=payload, headers=ADMIN)
    assert response.status_code == 201
    created = response.json()
    assert created["role"] == "resident"
    assert created["onboarding_completed_at"] is None


@pytest.mark.asyncio
async def test_dashboard_bql_chi_bao_cao_pham_vi_cua_minh(client):
    data = (await client.get("/api/v1/admin/dashboard", headers=ADMIN)).json()
    assert data["total_residents"] >= 2

    owner_row = next(r for r in data["residents"] if r["user_id"] == 2)
    checklist = (await client.get("/api/v1/checklist", headers=OWNER)).json()

    assert owner_row["bql_scope"] == checklist["bql_scope"]
    assert owner_row["bql_scope"]["total"] < checklist["overall"]["total"]
