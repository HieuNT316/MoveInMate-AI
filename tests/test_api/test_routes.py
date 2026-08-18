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
        # Ghi lại state nhận được mỗi lần gọi — để test kiểm tra route có
        # truyền đúng `chat_history` (lịch sử hội thoại) vào graph hay không.
        self.received_states: list[dict] = []

    async def ainvoke(self, state: dict) -> dict:
        self.received_states.append(state)
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

    conversations = (await client.get("/api/v1/chat/conversations", headers=OWNER)).json()
    assert conversations == []


@pytest.mark.asyncio
async def test_lich_su_chat_chi_cua_chinh_minh(client, fake_chat_graph):
    reply = (
        await client.post("/api/v1/chat", json={"message": "thẻ cư dân"}, headers=OWNER)
    ).json()

    mine = (await client.get("/api/v1/chat/conversations", headers=OWNER)).json()
    others = (await client.get("/api/v1/chat/conversations", headers=RENTER)).json()

    assert len(mine) == 1
    assert mine[0]["preview"] == "thẻ cư dân"
    assert others == []

    # Xem chi tiết đúng hội thoại mình vừa tạo.
    conversation_id = reply["conversation_id"]
    messages = (
        await client.get(f"/api/v1/chat/conversations/{conversation_id}/messages", headers=OWNER)
    ).json()
    assert len(messages) == 1

    # Người khác đoán đúng UUID cũng không xem/tiếp tục được — cách ly ở tầng DB.
    forbidden = await client.get(
        f"/api/v1/chat/conversations/{conversation_id}/messages", headers=RENTER
    )
    assert forbidden.status_code == 404


# --- Hội thoại nhiều lượt (multi-turn) -----------------------------------


@pytest.mark.asyncio
async def test_gui_tiep_dung_conversation_id_thi_gop_vao_cung_hoi_thoai(client, fake_chat_graph):
    first = (
        await client.post("/api/v1/chat", json={"message": "Thẻ xe cần gì?"}, headers=OWNER)
    ).json()
    conversation_id = first["conversation_id"]

    second = await client.post(
        "/api/v1/chat",
        json={"message": "Còn phí thì sao?", "conversation_id": conversation_id},
        headers=OWNER,
    )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id

    conversations = (await client.get("/api/v1/chat/conversations", headers=OWNER)).json()
    assert len(conversations) == 1
    assert conversations[0]["message_count"] == 2


@pytest.mark.asyncio
async def test_gui_tiep_thi_chat_graph_nhan_duoc_lich_su_gan_nhat(client, fake_chat_graph):
    """Xác nhận route thật sự truyền `chat_history` vào graph, không chỉ gộp DB."""
    first = (
        await client.post("/api/v1/chat", json={"message": "Thẻ xe cần gì?"}, headers=OWNER)
    ).json()

    await client.post(
        "/api/v1/chat",
        json={"message": "Còn phí thì sao?", "conversation_id": first["conversation_id"]},
        headers=OWNER,
    )

    first_call, second_call = fake_chat_graph.received_states
    assert first_call["chat_history"] == []
    assert second_call["chat_history"] == [
        {"question": "Thẻ xe cần gì?", "answer": "Câu trả lời giả lập."}
    ]


@pytest.mark.asyncio
async def test_gui_tiep_conversation_id_khong_ton_tai_tra_404(client, fake_chat_graph):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.post(
        "/api/v1/chat", json={"message": "Còn gì nữa?", "conversation_id": fake_id}, headers=OWNER
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_gui_tiep_conversation_id_cua_nguoi_khac_tra_404(client, fake_chat_graph):
    """Không cho user A 'hỏi tiếp' vào hội thoại của user B dù đoán đúng UUID."""
    owner_reply = (
        await client.post("/api/v1/chat", json={"message": "Thẻ xe cần gì?"}, headers=OWNER)
    ).json()

    response = await client.post(
        "/api/v1/chat",
        json={"message": "Chen ngang", "conversation_id": owner_reply["conversation_id"]},
        headers=RENTER,
    )
    assert response.status_code == 404


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


# --- Hồ sơ nộp trực tuyến (US-13) ---------------------------------------
#
# Checklist của chủ hộ (user 2, có ô tô, gói pool) gồm cả mục BQL xử lý được
# lẫn mục của công an phường — đủ để kiểm cả hai nhánh.

CAR_CARD_ITEM = 6      # "Đăng ký thẻ xe"        — bql_actionable
RESIDENCY_ITEM = 5     # "Cập nhật thông tin cư trú" — third_party_info
RENTER_ONLY_ITEM = 3   # "Làm thẻ cư dân (người thuê)" — không có ở checklist chủ hộ


@pytest.mark.asyncio
async def test_checklist_kem_thong_tin_dinh_tuyen(client):
    """Cư dân phải biết nộp ở đâu, bộ phận nào xử lý, bao lâu — trước khi nộp."""
    items = (await client.get("/api/v1/checklist", headers=OWNER)).json()["items"]

    car = next(i for i in items if i["id"] == CAR_CARD_ITEM)
    assert car["handling_department"] == "An ninh"
    assert car["submission_location"] == "Quầy lễ tân tầng 1"
    assert car["processing_time"]

    # Thủ tục của công an phường thì BQL không có bộ phận nào để định tuyến.
    outside = next(i for i in items if i["id"] == RESIDENCY_ITEM)
    assert outside["handling_department"] is None
    assert outside["submission_location"] is None


@pytest.mark.asyncio
async def test_nop_ho_so_thanh_cong(client):
    response = await client.post(
        "/api/v1/applications",
        json={"checklist_item_id": CAR_CARD_ITEM, "note": "Xe 30A-123.45"},
        headers=OWNER,
    )
    assert response.status_code == 201
    app = response.json()

    assert app["status"] == "received"
    assert app["task_name"] == "Đăng ký thẻ xe"
    assert app["handling_department"] == "An ninh"
    assert app["note"] == "Xe 30A-123.45"
    assert app["bql_note"] is None


@pytest.mark.asyncio
async def test_nop_ho_so_khong_tick_checklist(client):
    """Nộp là gửi yêu cầu đi, tick là tự xác nhận đã xong — hai việc khác nhau.

    Gộp lại sẽ khiến tiến độ báo hoàn thành trong khi BQL còn chưa xử lý.
    """
    before = (await client.get("/api/v1/checklist", headers=OWNER)).json()
    await client.post(
        "/api/v1/applications", json={"checklist_item_id": CAR_CARD_ITEM}, headers=OWNER
    )
    after = (await client.get("/api/v1/checklist", headers=OWNER)).json()

    assert after["overall"]["completed"] == before["overall"]["completed"]
    assert next(i for i in after["items"] if i["id"] == CAR_CARD_ITEM)["completed"] is False


@pytest.mark.asyncio
async def test_khong_nop_duoc_muc_ngoai_checklist_cua_minh(client):
    """404 chứ không phải 403: không xác nhận hộ rằng id đó có tồn tại."""
    response = await client.post(
        "/api/v1/applications", json={"checklist_item_id": RENTER_ONLY_ITEM}, headers=OWNER
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_nop_trung_khi_ho_so_dang_mo_bi_tu_choi(client):
    payload = {"checklist_item_id": CAR_CARD_ITEM}
    first = await client.post("/api/v1/applications", json=payload, headers=OWNER)
    assert first.status_code == 201

    second = await client.post("/api/v1/applications", json=payload, headers=OWNER)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_ho_so_da_dong_thi_nop_lai_duoc(client):
    """Bị từ chối rồi thì phải được nộp lại — nếu không cư dân kẹt vĩnh viễn."""
    payload = {"checklist_item_id": CAR_CARD_ITEM}
    created = (await client.post("/api/v1/applications", json=payload, headers=OWNER)).json()

    await client.patch(
        f"/api/v1/admin/applications/{created['application_id']}",
        json={"status": "rejected", "bql_note": "Sai biển số"},
        headers=ADMIN,
    )

    again = await client.post("/api/v1/applications", json=payload, headers=OWNER)
    assert again.status_code == 201


@pytest.mark.asyncio
async def test_cu_dan_chi_thay_ho_so_cua_chinh_minh(client):
    await client.post(
        "/api/v1/applications", json={"checklist_item_id": CAR_CARD_ITEM}, headers=OWNER
    )
    assert len((await client.get("/api/v1/applications", headers=OWNER)).json()) == 1
    assert (await client.get("/api/v1/applications", headers=RENTER)).json() == []


@pytest.mark.asyncio
async def test_bql_xem_duoc_ho_so_kem_thong_tin_cu_dan(client):
    await client.post(
        "/api/v1/applications", json={"checklist_item_id": CAR_CARD_ITEM}, headers=OWNER
    )
    rows = (await client.get("/api/v1/admin/applications", headers=ADMIN)).json()

    assert len(rows) == 1
    assert rows[0]["full_name"] == "Trần Văn An"
    assert rows[0]["apartment"]


@pytest.mark.asyncio
async def test_bql_loc_ho_so_theo_bo_phan(client):
    """Mỗi bộ phận chỉ xem phần việc của mình — đây là chỗ định tuyến có ích."""
    await client.post(
        "/api/v1/applications", json={"checklist_item_id": CAR_CARD_ITEM}, headers=OWNER
    )
    await client.post(
        "/api/v1/applications", json={"checklist_item_id": 1}, headers=OWNER
    )

    security = (
        await client.get("/api/v1/admin/applications?department=An ninh", headers=ADMIN)
    ).json()
    assert [r["task_name"] for r in security] == ["Đăng ký thẻ xe"]


@pytest.mark.asyncio
async def test_bql_loc_theo_trang_thai_khong_hop_le_bi_tu_choi(client):
    response = await client.get(
        "/api/v1/admin/applications?status=dang_treo", headers=ADMIN
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bql_doi_trang_thai_ho_so(client):
    created = (
        await client.post(
            "/api/v1/applications", json={"checklist_item_id": CAR_CARD_ITEM}, headers=OWNER
        )
    ).json()

    updated = (
        await client.patch(
            f"/api/v1/admin/applications/{created['application_id']}",
            json={"status": "needs_info", "bql_note": "Thiếu bản sao đăng ký xe"},
            headers=ADMIN,
        )
    ).json()

    assert updated["status"] == "needs_info"
    assert updated["bql_note"] == "Thiếu bản sao đăng ký xe"

    # Cư dân thấy ngay lời nhắn đó.
    mine = (await client.get("/api/v1/applications", headers=OWNER)).json()
    assert mine[0]["bql_note"] == "Thiếu bản sao đăng ký xe"


@pytest.mark.asyncio
async def test_doi_trang_thai_khong_kem_ghi_chu_thi_giu_nguyen_ghi_chu_cu(client):
    """Xoá mất lý do "cần bổ sung" cũ sẽ khiến cư dân không biết phải làm gì."""
    created = (
        await client.post(
            "/api/v1/applications", json={"checklist_item_id": CAR_CARD_ITEM}, headers=OWNER
        )
    ).json()
    app_id = created["application_id"]

    await client.patch(
        f"/api/v1/admin/applications/{app_id}",
        json={"status": "needs_info", "bql_note": "Thiếu đăng ký xe"},
        headers=ADMIN,
    )
    after = (
        await client.patch(
            f"/api/v1/admin/applications/{app_id}", json={"status": "processing"}, headers=ADMIN
        )
    ).json()

    assert after["status"] == "processing"
    assert after["bql_note"] == "Thiếu đăng ký xe"


@pytest.mark.asyncio
async def test_doi_trang_thai_ho_so_khong_ton_tai_tra_404(client):
    response = await client.patch(
        "/api/v1/admin/applications/9999", json={"status": "approved"}, headers=ADMIN
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_phan_quyen_tren_route_ho_so(client):
    """Hai chiều: cư dân không vào được route BQL, BQL không nộp hồ sơ cư dân."""
    assert (await client.get("/api/v1/admin/applications", headers=OWNER)).status_code == 403
    assert (
        await client.post(
            "/api/v1/applications", json={"checklist_item_id": CAR_CARD_ITEM}, headers=ADMIN
        )
    ).status_code == 403


# --- Ảnh minh chứng (US-13, phần thủ tục ngoài phạm vi BQL) --------------
#
# Thủ tục ở cơ quan khác không có form online để điền — cư dân chụp đơn đăng ký
# hoặc màn hình VNeID nộp lên, BQL chỉ ghi nhận chứ không xử lý.

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def _upload(client, application_id, content=PNG, name="vneid.png", ctype="image/png"):
    return client.post(
        f"/api/v1/applications/{application_id}/attachments",
        files={"file": (name, content, ctype)},
        headers=OWNER,
    )


async def _create(client, item_id, headers=OWNER):
    return (
        await client.post(
            "/api/v1/applications", json={"checklist_item_id": item_id}, headers=headers
        )
    ).json()


@pytest.mark.asyncio
async def test_thu_tuc_ngoai_pham_vi_nop_duoc_dang_tu_khai(client):
    """Trước 15/08 mục này trả 400. Cư dân vẫn cần chỗ chứng minh đã đăng ký."""
    response = await client.post(
        "/api/v1/applications", json={"checklist_item_id": RESIDENCY_ITEM}, headers=OWNER
    )
    assert response.status_code == 201

    app = response.json()
    assert app["kind"] == "self_declared"
    # Không bộ phận nào của BQL tiếp nhận — đừng để giao diện nói đang xử lý.
    assert app["handling_department"] is None


@pytest.mark.asyncio
async def test_thu_tuc_cua_bql_van_la_ho_so_duoc_xu_ly(client):
    app = await _create(client, CAR_CARD_ITEM)
    assert app["kind"] == "bql_processing"
    assert app["handling_department"] == "An ninh"


@pytest.mark.asyncio
async def test_tai_anh_minh_chung_len(client):
    app = await _create(client, RESIDENCY_ITEM)
    response = await _upload(client, app["application_id"])
    assert response.status_code == 201

    att = response.json()
    assert att["filename"] == "vneid.png"
    assert att["content_type"] == "image/png"
    assert att["size_bytes"] == len(PNG)
    assert att["url"]

    mine = (await client.get("/api/v1/applications", headers=OWNER)).json()
    assert len(mine[0]["attachments"]) == 1


@pytest.mark.asyncio
async def test_ten_file_khong_duoc_dung_lam_duong_dan_luu_tru(client, fake_storage):
    """Tên client gửi lên chỉ để hiển thị — dùng nó làm đường dẫn là mở cửa
    cho path traversal và cho việc đoán tệp của người khác."""
    app = await _create(client, RESIDENCY_ITEM)
    await _upload(client, app["application_id"], name="../../../etc/passwd.png")

    path = next(iter(fake_storage))
    assert ".." not in path
    assert "etc" not in path
    assert path.startswith(f"{app['application_id']}/")

    att = (await client.get("/api/v1/applications", headers=OWNER)).json()[0]["attachments"][0]
    assert att["filename"] == "passwd.png"  # chỉ giữ phần tên, bỏ đường dẫn


@pytest.mark.asyncio
async def test_dinh_dang_khong_cho_phep_bi_tu_choi(client):
    app = await _create(client, RESIDENCY_ITEM)
    response = await _upload(
        client, app["application_id"], content=b"<script>", name="x.html", ctype="text/html"
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_tep_qua_lon_bi_tu_choi(client):
    app = await _create(client, RESIDENCY_ITEM)
    huge = b"\x89PNG\r\n\x1a\n" + b"0" * (5 * 1024 * 1024 + 1)
    response = await _upload(client, app["application_id"], content=huge)
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_tep_rong_bi_tu_choi(client):
    app = await _create(client, RESIDENCY_ITEM)
    response = await _upload(client, app["application_id"], content=b"")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_khong_tai_duoc_len_ho_so_cua_nguoi_khac(client):
    """404 chứ không 403: đừng xác nhận hộ rằng hồ sơ đó có tồn tại."""
    app = (
        await client.post(
            "/api/v1/applications", json={"checklist_item_id": 1}, headers=RENTER
        )
    ).json()

    response = await _upload(client, app["application_id"])
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_khong_ghi_nhan_ho_so_tu_khai_khi_chua_co_minh_chung(client):
    """Ghi nhận hồ sơ trống nghĩa là BQL xác nhận cư dân đã đăng ký tạm trú mà
    không hề nhìn thấy bằng chứng nào."""
    app = await _create(client, RESIDENCY_ITEM)

    refused = await client.patch(
        f"/api/v1/admin/applications/{app['application_id']}",
        json={"status": "approved"},
        headers=ADMIN,
    )
    assert refused.status_code == 409

    # Có ảnh rồi thì ghi nhận được.
    await _upload(client, app["application_id"])
    accepted = await client.patch(
        f"/api/v1/admin/applications/{app['application_id']}",
        json={"status": "approved"},
        headers=ADMIN,
    )
    assert accepted.status_code == 200


@pytest.mark.asyncio
async def test_ho_so_bql_van_duyet_duoc_du_khong_co_tep(client):
    """Ràng buộc minh chứng chỉ áp cho hồ sơ tự khai — thẻ xe nộp trực tiếp
    tại quầy thì BQL vẫn duyệt bình thường."""
    app = await _create(client, CAR_CARD_ITEM)
    response = await client.patch(
        f"/api/v1/admin/applications/{app['application_id']}",
        json={"status": "approved"},
        headers=ADMIN,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_bql_thay_duoc_minh_chung_cua_cu_dan(client):
    app = await _create(client, RESIDENCY_ITEM)
    await _upload(client, app["application_id"])

    rows = (await client.get("/api/v1/admin/applications", headers=ADMIN)).json()
    row = next(r for r in rows if r["application_id"] == app["application_id"])
    assert row["kind"] == "self_declared"
    assert len(row["attachments"]) == 1
    assert row["attachments"][0]["url"]


# --- Loại giấy tờ & "còn thiếu gì" (US-13 / D1) --------------------------


@pytest.mark.asyncio
async def test_checklist_kem_danh_sach_giay_to_can_nop(client):
    items = (await client.get("/api/v1/checklist", headers=OWNER)).json()["items"]
    car = next(i for i in items if i["id"] == CAR_CARD_ITEM)

    assert [d["code"] for d in car["required_documents"]] == ["cccd", "dang_ky_xe"]
    # Kèm nhãn để frontend khỏi phải giữ bảng riêng.
    assert all(d["label"] for d in car["required_documents"])


@pytest.mark.asyncio
async def test_thu_tuc_ngoai_pham_vi_khong_khai_giay_to_bat_buoc(client):
    """KB đòi CT01 *hoặc* VNeID — phép đối chiếu là AND nên ép một loại cụ thể
    sẽ báo thiếu sai cho người nộp bằng cách hợp lệ khác."""
    items = (await client.get("/api/v1/checklist", headers=OWNER)).json()["items"]
    outside = next(i for i in items if i["id"] == RESIDENCY_ITEM)
    assert outside["required_documents"] == []


@pytest.mark.asyncio
async def test_tai_len_kem_loai_giay_to(client):
    app = await _create(client, CAR_CARD_ITEM)
    r = await client.post(
        f"/api/v1/applications/{app['application_id']}/attachments",
        files={"file": ("cavet.png", PNG, "image/png")},
        data={"document_type": "dang_ky_xe"},
        headers=OWNER,
    )
    assert r.status_code == 201
    assert r.json()["document_type"] == "dang_ky_xe"


@pytest.mark.asyncio
async def test_loai_giay_to_khong_hop_le_bi_tu_choi(client):
    app = await _create(client, CAR_CARD_ITEM)
    r = await client.post(
        f"/api/v1/applications/{app['application_id']}/attachments",
        files={"file": ("x.png", PNG, "image/png")},
        data={"document_type": "so_do_giay_to_la"},
        headers=OWNER,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_du_giay_to_thi_bao_khong_thieu(client):
    app = await _create(client, CAR_CARD_ITEM)
    aid = app["application_id"]
    for code in ("cccd", "dang_ky_xe"):
        await client.post(
            f"/api/v1/applications/{aid}/attachments",
            files={"file": (f"{code}.png", PNG, "image/png")},
            data={"document_type": code},
            headers=OWNER,
        )

    mine = (await client.get("/api/v1/applications", headers=OWNER)).json()[0]
    assert mine["missing_documents"] == []
    assert mine["unlabelled_count"] == 0


@pytest.mark.asyncio
async def test_thieu_mot_loai_thi_bao_dung_loai_do(client):
    app = await _create(client, CAR_CARD_ITEM)
    await client.post(
        f"/api/v1/applications/{app['application_id']}/attachments",
        files={"file": ("cccd.png", PNG, "image/png")},
        data={"document_type": "cccd"},
        headers=OWNER,
    )

    mine = (await client.get("/api/v1/applications", headers=OWNER)).json()[0]
    assert [d["code"] for d in mine["missing_documents"]] == ["dang_ky_xe"]


@pytest.mark.asyncio
async def test_tep_chua_phan_loai_thi_khong_ket_luan_thieu_gi(client):
    """Điểm cốt lõi của D1: hồ sơ ĐANG CÓ ảnh mà báo "thiếu" thì Ban quản lý
    tưởng cư dân chưa nộp và đi đòi thứ đã có."""
    app = await _create(client, CAR_CARD_ITEM)
    await _upload(client, app["application_id"])  # không gửi document_type

    mine = (await client.get("/api/v1/applications", headers=OWNER)).json()[0]
    assert mine["missing_documents"] is None
    assert mine["unlabelled_count"] == 1


@pytest.mark.asyncio
async def test_bql_gan_lai_loai_thi_tinh_lai_duoc_con_thieu_gi(client):
    app = await _create(client, CAR_CARD_ITEM)
    aid = app["application_id"]
    up = await _upload(client, aid, name="anh-cavet.png")
    att_id = up.json()["attachment_id"]

    fixed = await client.patch(
        f"/api/v1/admin/applications/{aid}/attachments/{att_id}",
        json={"document_type": "dang_ky_xe"},
        headers=ADMIN,
    )
    assert fixed.status_code == 200
    assert fixed.json()["document_type"] == "dang_ky_xe"

    mine = (await client.get("/api/v1/applications", headers=OWNER)).json()[0]
    assert mine["unlabelled_count"] == 0
    assert [d["code"] for d in mine["missing_documents"]] == ["cccd"]


@pytest.mark.asyncio
async def test_cu_dan_khong_gan_lai_loai_duoc(client):
    app = await _create(client, CAR_CARD_ITEM)
    up = await _upload(client, app["application_id"])
    r = await client.patch(
        f"/api/v1/admin/applications/{app['application_id']}/attachments/"
        f"{up.json()['attachment_id']}",
        json={"document_type": "cccd"},
        headers=OWNER,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_gan_lai_tep_khong_ton_tai_tra_404(client):
    app = await _create(client, CAR_CARD_ITEM)
    r = await client.patch(
        f"/api/v1/applications/{app['application_id']}/attachments/9999".replace(
            "/api/v1/applications", "/api/v1/admin/applications"
        ),
        json={"document_type": "cccd"},
        headers=ADMIN,
    )
    assert r.status_code == 404
