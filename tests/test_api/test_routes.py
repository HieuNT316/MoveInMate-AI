"""Test luồng API — chạy đúng kịch bản demo GATE 2.

Người dùng seed sẵn: 1 = BQL, 2 = chủ hộ đã onboarding, 3 = người thuê chưa
onboarding.
"""

import pytest

from src.api import routes as api_routes
from src.services.vectorstore import RetrievalError

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
    """401 chứ không phải 422: thiếu xác thực là chuyện quyền, không phải sai kiểu dữ liệu."""
    response = await client.get("/api/v1/checklist")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


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


# --- Khớp tên thủ tục AI suy ra với checklist thật -----------------------
#
# Bug thật phát hiện 10/08: AI nói "Đăng ký thẻ cư dân" nhưng checklist ghi
# "Làm thẻ cư dân (chủ hộ)" — khác động từ đầu câu nên so nguyên cụm thất
# bại, checklist_item_id ra null dù thủ tục có tồn tại. Khoá lại bằng test.

_THE_ITEMS = [
    {"id": 2, "task_name": "Làm thẻ cư dân (chủ hộ)"},
    {"id": 6, "task_name": "Đăng ký thẻ xe"},
    {"id": 8, "task_name": "Kích hoạt thẻ hồ bơi"},
]


@pytest.mark.parametrize(
    ("procedure_name", "expected_id"),
    [
        ("Đăng ký thẻ cư dân", 2),  # khác động từ (đăng ký / làm) — phải vẫn khớp
        ("Làm thẻ cư dân", 2),
        ("thẻ cư dân", 2),
        ("Đăng ký thẻ xe", 6),
        ("Xin cấp thẻ hồ bơi", 8),
        ("Đăng ký tạm trú", None),  # không có trong checklist — không được bịa ra id
    ],
)
def test_khop_ten_thu_tuc_khong_lam_lan_thu_tuc_khac(procedure_name, expected_id):
    match = api_routes._match_checklist_item(procedure_name, _THE_ITEMS)
    assert (match["id"] if match else None) == expected_id


def test_the_xe_va_the_cu_dan_khong_bao_gio_khop_nhau():
    """Trực tiếp khoá lại rủi ro bị hỏi: hỏi thẻ cư dân không được điều hướng nhầm sang thẻ xe."""
    assert api_routes._match_checklist_item("thẻ cư dân", _THE_ITEMS)["id"] == 2
    assert api_routes._match_checklist_item("thẻ xe", _THE_ITEMS)["id"] == 6


# --- Hỏi đáp -------------------------------------------------------------
#
# Nội dung/chất lượng của rag_retrieve + generate (ngưỡng, gộp nguồn, guard
# chống bịa...) đã có tests/test_agents/test_chat_graph.py mock riêng. Ở đây
# chỉ kiểm tra phần API: route có gọi đúng chat_graph, có ghi CHAT_HISTORY,
# và có map lỗi hạ tầng sang đúng mã HTTP hay không — không gọi mạng thật.


class _FakeChatGraph:
    def __init__(self, result: dict | None = None, error: Exception | None = None):
        self.result = result or {
            "answer": "Câu trả lời giả lập.",
            "sources": [{"document_id": 1, "title": "Tài liệu A", "snippet": "...", "source_type": "bql_internal"}],
            "answer_source": "rag",
        }
        self.error = error

    async def ainvoke(self, state: dict) -> dict:
        if self.error:
            raise self.error
        return {"query": state["query"], **self.result}


@pytest.fixture
def fake_chat_graph(monkeypatch):
    fake = _FakeChatGraph()
    monkeypatch.setattr(api_routes, "chat_graph", fake)
    return fake


@pytest.mark.asyncio
async def test_hoi_dap_tra_ve_nguon_trich_dan(client, fake_chat_graph):
    response = await client.post(
        "/api/v1/chat", json={"message": "Làm thẻ xe cần giấy tờ gì?"}, headers=OWNER
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer_source"] == "rag"
    assert data["sources"], "Câu trả lời phải kèm nguồn trích dẫn"
    assert data["sources"][0]["title"]


@pytest.mark.asyncio
async def test_suggested_action_duoc_khop_voi_checklist_that(client, monkeypatch):
    """AI đoán đúng tên thủ tục có thật trong checklist của OWNER (có xe)."""
    fake = _FakeChatGraph(
        result={
            "answer": "Bạn có muốn tôi đưa bạn tới đó không?",
            "sources": [],
            "answer_source": "rag",
            "suggested_action": {"type": "navigate_to_submission", "procedure_name": "Đăng ký thẻ xe"},
        }
    )
    monkeypatch.setattr(api_routes, "chat_graph", fake)

    response = await client.post(
        "/api/v1/chat", json={"message": "Nộp hồ sơ thẻ xe ở đâu?"}, headers=OWNER
    )
    data = response.json()["suggested_action"]
    assert data["type"] == "navigate_to_submission"
    assert data["checklist_item_id"] is not None


@pytest.mark.asyncio
async def test_suggested_action_khong_khop_thi_id_la_null(client, monkeypatch):
    """AI đoán tên thủ tục không khớp mục nào — FE phải tự ẩn nút, không điều hướng sai chỗ."""
    fake = _FakeChatGraph(
        result={
            "answer": "...",
            "sources": [],
            "answer_source": "rag",
            "suggested_action": {
                "type": "navigate_to_submission",
                "procedure_name": "Thủ tục không tồn tại trong checklist",
            },
        }
    )
    monkeypatch.setattr(api_routes, "chat_graph", fake)

    response = await client.post(
        "/api/v1/chat", json={"message": "Nộp hồ sơ ở đâu?"}, headers=OWNER
    )
    assert response.json()["suggested_action"]["checklist_item_id"] is None


@pytest.mark.asyncio
async def test_khong_goi_tool_thi_response_khong_co_suggested_action(client, fake_chat_graph):
    response = await client.post(
        "/api/v1/chat", json={"message": "Làm thẻ xe cần giấy tờ gì?"}, headers=OWNER
    )
    assert response.json()["suggested_action"] is None


@pytest.mark.asyncio
async def test_cau_hoi_khong_co_context_thi_tu_choi(client, monkeypatch):
    fake = _FakeChatGraph(result={"answer": "Xin lỗi, không tìm thấy... liên hệ Ban quản lý.", "sources": [], "answer_source": "no_context"})
    monkeypatch.setattr(api_routes, "chat_graph", fake)

    response = await client.post(
        "/api/v1/chat", json={"message": "Giá vàng hôm nay bao nhiêu?"}, headers=OWNER
    )
    data = response.json()
    assert data["answer_source"] == "no_context"
    assert data["sources"] == []


@pytest.mark.asyncio
async def test_loi_ha_tang_rag_tra_503_khong_ghi_lich_su(client, monkeypatch):
    """docs/architecture_diagram.md mục 5: lỗi embedding/Chroma là 503, không phải câu từ chối thường."""
    fake = _FakeChatGraph(error=RetrievalError("Google API sập"))
    monkeypatch.setattr(api_routes, "chat_graph", fake)

    response = await client.post(
        "/api/v1/chat", json={"message": "thẻ cư dân"}, headers=OWNER
    )
    assert response.status_code == 503

    history = (await client.get("/api/v1/chat/history", headers=OWNER)).json()
    assert history == []


@pytest.mark.asyncio
async def test_lich_su_chat_chi_cua_chinh_minh(client, fake_chat_graph):
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
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/api/v1/onboarding", RENTER_PROFILE),
        ("patch", "/api/v1/profile", {"has_car": True}),
        ("get", "/api/v1/checklist", None),
        ("patch", "/api/v1/checklist/1", {"completed": True}),
    ],
)
async def test_bql_khong_vao_duoc_route_cua_cu_dan(client, method, path, body):
    """Chiều đối xứng của test trên — thiếu nó thì BQL có checklist nhận nhà."""
    kwargs = {"headers": ADMIN} | ({"json": body} if body is not None else {})
    response = await getattr(client, method)(path, **kwargs)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_bql_van_xem_duoc_ho_so_cua_chinh_minh(client):
    """`GET /profile` phải mở cho cả hai vai: frontend đọc `role` từ đây."""
    response = await client.get("/api/v1/profile", headers=ADMIN)
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_bql_tao_tai_khoan_cu_dan(client, fake_auth_provisioning):
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
    # Mật khẩu tạm chỉ trả về đúng lần này để BQL bàn giao cho cư dân.
    assert created["temporary_password"]


@pytest.mark.asyncio
async def test_khong_tao_ho_so_khi_supabase_tu_choi(client, monkeypatch):
    """Email trùng bị Supabase chặn — không được để lại hồ sơ mồ côi trong DB."""

    def _reject(_email, _password):
        raise api_routes.SupabaseAdminError("email đã tồn tại")

    monkeypatch.setattr(api_routes, "create_auth_user", _reject)
    payload = {
        "full_name": "Trùng Email",
        "email": "an.tran@demo.vn",
        "apartment": "S1.01-0101",
        "building": "Sapphire 1",
    }
    response = await client.post("/api/v1/admin/users", json=payload, headers=ADMIN)
    assert response.status_code == 502

    listing = (await client.get("/api/v1/admin/dashboard", headers=ADMIN)).json()
    assert not any(r["full_name"] == "Trùng Email" for r in listing["residents"])


@pytest.mark.asyncio
async def test_dashboard_bql_chi_bao_cao_pham_vi_cua_minh(client):
    data = (await client.get("/api/v1/admin/dashboard", headers=ADMIN)).json()
    assert data["total_residents"] >= 2

    owner_row = next(r for r in data["residents"] if r["user_id"] == 2)
    checklist = (await client.get("/api/v1/checklist", headers=OWNER)).json()

    assert owner_row["bql_scope"] == checklist["bql_scope"]
    assert owner_row["bql_scope"]["total"] < checklist["overall"]["total"]


# --- Tài khoản demo (tạm thời, xoá cùng lúc với /auth/demo-accounts) ----


@pytest.mark.asyncio
async def test_danh_sach_demo_co_nguoi_thue_va_chu_ho_khac_checklist(client):
    """Đây là bằng chứng cá nhân hóa: cùng dữ liệu, hai persona ra hai con số."""
    accounts = (await client.get("/api/v1/auth/demo-accounts")).json()

    assert any(a["role"] == "admin" for a in accounts)
    residents = [a for a in accounts if a["role"] == "resident"]
    assert len(residents) >= 2
    assert len({a["checklist_total"] for a in residents}) > 1


# --- Đối chiếu tất định khi LLM không gọi tool (12/08) -------------------


@pytest.mark.asyncio
async def test_khong_goi_tool_nhung_co_y_dinh_hanh_dong_van_gan_nut(
    client, fake_chat_graph
):
    """Tool đo được 0/5 trên bản deploy — nút phải hiện được mà không cần nó."""
    response = await client.post(
        "/api/v1/chat",
        json={"message": "Cho tôi nộp hồ sơ làm thẻ cư dân"},
        headers=OWNER,
    )
    action = response.json()["suggested_action"]
    assert action is not None
    assert action["checklist_item_id"] is not None
    # Trả về tên THẬT trong checklist, không phải chuỗi người dùng gõ.
    assert action["procedure_name"] == "Làm thẻ cư dân (chủ hộ)"


@pytest.mark.asyncio
async def test_cau_hoi_thong_tin_khong_gan_nut(client, fake_chat_graph):
    """Ranh giới vai AI cố ý giữ: hỏi giấy tờ là hỏi, không phải muốn đi nộp."""
    for question in [
        "Làm thẻ xe cần giấy tờ gì?",
        "Hồ sơ làm thẻ cư dân gồm những gì?",
        "Đăng ký thẻ xe mất bao lâu?",
    ]:
        response = await client.post(
            "/api/v1/chat", json={"message": question}, headers=OWNER
        )
        assert response.json()["suggested_action"] is None, question


@pytest.mark.asyncio
async def test_y_dinh_hanh_dong_nhung_khong_khop_thu_tuc_nao(client, fake_chat_graph):
    """Không khớp thì im lặng, không đoán bừa một mục gần đúng."""
    response = await client.post(
        "/api/v1/chat",
        json={"message": "Cho tôi nộp hồ sơ xin nghỉ phép"},
        headers=OWNER,
    )
    assert response.json()["suggested_action"] is None


@pytest.mark.asyncio
async def test_nguoi_thue_va_chu_ho_dieu_huong_toi_muc_khac_nhau(
    client, fake_chat_graph
):
    """Đối chiếu chạy trên checklist RIÊNG của từng người, không phải bảng chung."""
    await client.post("/api/v1/onboarding", json=RENTER_PROFILE, headers=RENTER)
    payload = {"message": "Cho tôi nộp hồ sơ làm thẻ cư dân"}

    owner = (await client.post("/api/v1/chat", json=payload, headers=OWNER)).json()
    renter = (await client.post("/api/v1/chat", json=payload, headers=RENTER)).json()

    assert owner["suggested_action"]["procedure_name"] == "Làm thẻ cư dân (chủ hộ)"
    assert renter["suggested_action"]["procedure_name"] == "Làm thẻ cư dân (người thuê)"
