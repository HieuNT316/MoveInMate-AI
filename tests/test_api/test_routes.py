"""Test luồng API — chạy đúng kịch bản demo GATE 2.

Người dùng seed sẵn: 1 = BQL, 2 = chủ hộ đã onboarding, 3 = người thuê chưa
onboarding.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from src.api import routes as api_routes
from src.models.db import Application, ChatHistory
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
async def test_health_deep_bao_so_chunk_trong_chroma(client, monkeypatch):
    from src.services import vectorstore

    class _FakeCollection:
        def count(self) -> int:
            return 42

    class _FakeStore:
        _collection = _FakeCollection()

    monkeypatch.setattr(vectorstore, "get_vectorstore", lambda: _FakeStore())

    r = await client.get("/health/deep")
    assert r.status_code == 200
    assert r.json()["chroma"]["documents"] == 42


@pytest.mark.asyncio
async def test_health_deep_tra_503_khi_chroma_rong(client, monkeypatch):
    """Chroma rỗng = trợ lý từ chối MỌI câu hỏi, mà không chỉ báo nào đỏ.
    Đúng kiểu sự cố 11/08."""
    from src.services import vectorstore

    class _EmptyCollection:
        def count(self) -> int:
            return 0

    class _FakeStore:
        _collection = _EmptyCollection()

    monkeypatch.setattr(vectorstore, "get_vectorstore", lambda: _FakeStore())

    r = await client.get("/health/deep")
    assert r.status_code == 503


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
async def test_thong_bao_nhac_cu_dan_chua_hoan_thanh(client):
    response = await client.get("/api/v1/notifications", headers=OWNER)

    assert response.status_code == 200
    notifications = response.json()
    reminder = next(row for row in notifications if row["kind"] == "checklist")
    assert "chưa hoàn thành" in reminder["title"]
    assert reminder["href"].startswith("/checklist?item=")


@pytest.mark.asyncio
async def test_thong_bao_huong_cu_dan_chua_onboarding_vao_form(client):
    response = await client.get("/api/v1/notifications", headers=RENTER)

    assert response.status_code == 200
    assert response.json() == [{
        "id": "onboarding",
        "kind": "onboarding",
        "title": "Hoàn tất thiết lập hồ sơ",
        "message": "Trả lời 4 câu hỏi để nhận checklist phù hợp với căn hộ của bạn.",
        "href": "/onboarding",
        "action_label": "Thiết lập ngay",
    }]


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


# --- Che PII trước khi ghi chat_history (V8, src/services/pii.py) --------


@pytest.mark.asyncio
async def test_cccd_trong_cau_hoi_bi_che_truoc_khi_luu_db(client, db_session, monkeypatch):
    """Bảo đảm V8: CCCD cư dân tự gõ không được nằm trần trong DB.

    Đọc thẳng bảng `chat_history` qua `db_session` — chính session mà
    `client` dùng qua `get_db` — thay vì qua endpoint đọc lại, để kiểm đúng
    những gì đã INSERT, không phải những gì route trả về.
    """
    fake = _FakeChatGraph(
        result={
            "answer": "Bạn cần mang CCCD gốc khi đến quầy.",
            "sources": [],
            "answer_source": "rag",
        }
    )
    monkeypatch.setattr(api_routes, "chat_graph", fake)

    cccd = "037201012345"
    await client.post(
        "/api/v1/chat",
        json={"message": f"CCCD của tôi là {cccd}, xử lý giúp tôi"},
        headers=OWNER,
    )

    row = db_session.query(ChatHistory).order_by(ChatHistory.chat_id.desc()).first()
    assert row is not None
    assert cccd not in row.question
    assert "[ĐÃ ẨN THÔNG TIN CÁ NHÂN]" in row.question


@pytest.mark.asyncio
async def test_hotline_trong_answer_song_sot_trong_db(client, db_session, monkeypatch):
    """Ngược lại: hotline BQL trong `answer` không được bị che khi ghi DB —
    đây là chính lý do `answer` không bị áp regex số điện thoại (docstring
    `src/services/pii.py`)."""
    hotline_answer = "Gọi an ninh: 0827 001 090 hoặc gửi xe: 0946 982 323"
    fake = _FakeChatGraph(
        result={"answer": hotline_answer, "sources": [], "answer_source": "rag"}
    )
    monkeypatch.setattr(api_routes, "chat_graph", fake)

    await client.post(
        "/api/v1/chat", json={"message": "Số hotline an ninh là gì?"}, headers=OWNER
    )

    row = db_session.query(ChatHistory).order_by(ChatHistory.chat_id.desc()).first()
    assert row.answer == hotline_answer


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


def test_index_chan_insert_truc_tiep_khi_dang_mo(db_session):
    """Đi thẳng qua session, bỏ qua `get_open_application` — nếu chỉ tầng ứng
    dụng chặn thì insert này sẽ lọt qua êm ru. Đây là test lẽ ra sẽ đỏ nếu
    index bị xoá khỏi model/migration, hoặc bị đổi thành non-partial."""
    db_session.add(
        Application(
            user_id=2, checklist_item_id=CAR_CARD_ITEM, status="received", kind="bql_processing"
        )
    )
    db_session.commit()

    db_session.add(
        Application(
            user_id=2, checklist_item_id=CAR_CARD_ITEM, status="processing", kind="bql_processing"
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    # SQLite in-memory: session vẫn "bẩn" sau lỗi, không rollback thì mọi thao
    # tác sau đó trong cùng transaction đều ăn theo lỗi này.
    db_session.rollback()


def test_index_khong_chan_insert_khi_ho_so_cu_da_dong(db_session):
    """Companion của test trên — index phải là BỘ PHẬN, không phải toàn cục."""
    first = Application(
        user_id=2, checklist_item_id=CAR_CARD_ITEM, status="received", kind="bql_processing"
    )
    db_session.add(first)
    db_session.commit()

    first.status = "rejected"
    db_session.commit()

    db_session.add(
        Application(
            user_id=2, checklist_item_id=CAR_CARD_ITEM, status="received", kind="bql_processing"
        )
    )
    db_session.commit()  # không raise — hồ sơ cũ đã đóng nên index không áp.


@pytest.mark.asyncio
async def test_dua_vao_index_van_tra_409_khong_phai_500(client, monkeypatch):
    """Mô phỏng race: cả hai request đọc "chưa có hồ sơ mở" trước khi request
    đầu commit. `get_open_application` bị giả để luôn trả None — giống hệt
    tình huống request thứ hai đọc TRƯỚC khi request thứ nhất ghi xong — nên
    `create_application` phải tự đụng `IntegrityError` từ index. Route phải
    trả 409 giống hệt nhánh kiểm tuần tự, không phải 500."""
    payload = {"checklist_item_id": CAR_CARD_ITEM}
    first = await client.post("/api/v1/applications", json=payload, headers=OWNER)
    assert first.status_code == 201

    monkeypatch.setattr(api_routes.store, "get_open_application", lambda *a, **k: None)

    second = await client.post("/api/v1/applications", json=payload, headers=OWNER)
    assert second.status_code == 409
    assert second.json()["detail"] == (
        f"Bạn đã có hồ sơ đang xử lý cho “{first.json()['task_name']}”."
    )


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
    # Từ 18/08 danh sách không ký URL nữa — xem GET .../attachments/{id}/url.
    assert att["url"] is None

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
    # Từ 18/08 danh sách không ký URL nữa — xem GET .../attachments/{id}/url.
    assert row["attachments"][0]["url"] is None


@pytest.mark.asyncio
async def test_danh_sach_ho_so_khong_ky_url(client):
    """Ký ở đây là một lời gọi mạng đồng bộ cho MỖI tệp, chặn event loop."""
    app = await _create(client, CAR_CARD_ITEM)
    await _upload(client, app["application_id"])

    mine = (await client.get("/api/v1/applications", headers=OWNER)).json()[0]
    assert mine["attachments"][0]["url"] is None


# --- Loại giấy tờ & "còn thiếu gì" (US-13 / D1) --------------------------


@pytest.mark.asyncio
async def test_checklist_kem_danh_sach_giay_to_can_nop(client):
    items = (await client.get("/api/v1/checklist", headers=OWNER)).json()["items"]
    car = next(i for i in items if i["id"] == CAR_CARD_ITEM)

    assert [d["code"] for d in car["required_documents"]] == [
        "cccd", "dang_ky_xe", "the_cu_dan",
    ]
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
    for code in ("cccd", "dang_ky_xe", "the_cu_dan"):
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
    assert [d["code"] for d in mine["missing_documents"]] == ["dang_ky_xe", "the_cu_dan"]


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
    assert [d["code"] for d in mine["missing_documents"]] == ["cccd", "the_cu_dan"]


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
        f"/api/v1/admin/applications/{app['application_id']}/attachments/9999",
        json={"document_type": "cccd"},
        headers=ADMIN,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_bql_cung_thay_con_thieu_gi(client):
    """Dashboard BQL mới là nơi chính dùng tính năng này — phải kiểm riêng,
    không dựa vào việc nó dùng chung hàm với danh sách của cư dân."""
    app = await _create(client, CAR_CARD_ITEM)
    await _upload(client, app["application_id"])

    row = next(
        r for r in (await client.get("/api/v1/admin/applications", headers=ADMIN)).json()
        if r["application_id"] == app["application_id"]
    )
    assert row["missing_documents"] is None
    assert row["unlabelled_count"] == 1


@pytest.mark.asyncio
async def test_khong_gan_lai_duoc_tep_thuoc_ho_so_khac(client):
    """Đây mới là phép thử về quyền: id tệp có thật, nhưng thuộc hồ sơ khác.
    Chỉ kiểm id không tồn tại thì không chứng minh được gì."""
    first = await _create(client, CAR_CARD_ITEM)
    second = await _create(client, 1)
    att_id = (await _upload(client, first["application_id"])).json()["attachment_id"]

    response = await client.patch(
        f"/api/v1/admin/applications/{second['application_id']}/attachments/{att_id}",
        json={"document_type": "cccd"},
        headers=ADMIN,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_go_loai_ve_chua_phan_loai(client):
    """Gán nhầm phải quay lại được trạng thái trung thực "chưa ai xem"."""
    app = await _create(client, CAR_CARD_ITEM)
    aid = app["application_id"]
    att_id = (await _upload(client, aid)).json()["attachment_id"]

    url = f"/api/v1/admin/applications/{aid}/attachments/{att_id}"
    await client.patch(url, json={"document_type": "cccd"}, headers=ADMIN)
    cleared = await client.patch(url, json={"document_type": None}, headers=ADMIN)

    assert cleared.status_code == 200
    assert cleared.json()["document_type"] is None

    mine = (await client.get("/api/v1/applications", headers=OWNER)).json()[0]
    assert mine["unlabelled_count"] == 1
    assert mine["missing_documents"] is None


# --- Ký URL theo yêu cầu (18/08) ----------------------------------------


@pytest.mark.asyncio
async def test_chu_ho_so_lay_duoc_link_xem_anh(client):
    app = await _create(client, CAR_CARD_ITEM)
    aid = app["application_id"]
    att_id = (await _upload(client, aid)).json()["attachment_id"]

    r = await client.get(
        f"/api/v1/applications/{aid}/attachments/{att_id}/url", headers=OWNER
    )
    assert r.status_code == 200
    assert r.json()["url"].startswith("https://")


@pytest.mark.asyncio
async def test_bql_lay_duoc_link_cua_moi_ho_so(client):
    app = await _create(client, CAR_CARD_ITEM)
    aid = app["application_id"]
    att_id = (await _upload(client, aid)).json()["attachment_id"]

    r = await client.get(
        f"/api/v1/applications/{aid}/attachments/{att_id}/url", headers=ADMIN
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_cu_dan_khac_khong_lay_duoc_link(client):
    app = await _create(client, CAR_CARD_ITEM)
    aid = app["application_id"]
    att_id = (await _upload(client, aid)).json()["attachment_id"]

    r = await client.get(
        f"/api/v1/applications/{aid}/attachments/{att_id}/url", headers=RENTER
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_id_tep_cua_ho_so_khac_tra_404(client):
    """Không kiểm cặp (hồ sơ, tệp) thì đoán được id tệp là đọc được ảnh CCCD
    của người khác. Đúng lỗi bản review D1 đã bắt ở endpoint gán loại."""
    first = await _create(client, CAR_CARD_ITEM)
    second = await _create(client, RESIDENCY_ITEM)
    att_id = (await _upload(client, first["application_id"])).json()["attachment_id"]

    r = await client.get(
        f"/api/v1/applications/{second['application_id']}/attachments/{att_id}/url",
        headers=OWNER,
    )
    assert r.status_code == 404


# --- Quản lý tài khoản cư dân (18/08) -----------------------------------


@pytest.mark.asyncio
async def test_bql_khoa_va_mo_tai_khoan(client):
    locked = await client.patch(
        "/api/v1/admin/residents/2/status",
        json={"account_status": "locked"},
        headers=ADMIN,
    )
    assert locked.status_code == 200
    assert locked.json()["account_status"] == "locked"

    assert (await client.get("/api/v1/profile", headers=OWNER)).status_code == 403

    await client.patch(
        "/api/v1/admin/residents/2/status",
        json={"account_status": "active"},
        headers=ADMIN,
    )
    assert (await client.get("/api/v1/profile", headers=OWNER)).status_code == 200


@pytest.mark.asyncio
async def test_khong_khoa_duoc_tai_khoan_bql(client):
    """User 1 là BQL. Quy tắc 'chỉ cư dân' gánh luôn việc BQL không tự khoá mình."""
    r = await client.patch(
        "/api/v1/admin/residents/1/status",
        json={"account_status": "locked"},
        headers=ADMIN,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cu_dan_khong_khoa_duoc_ai(client):
    r = await client.patch(
        "/api/v1/admin/residents/3/status",
        json={"account_status": "locked"},
        headers=OWNER,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_dat_lai_mat_khau_tra_mat_khau_tam(client):
    """User 2 đã gắn auth_user_id trong conftest."""
    r = await client.post("/api/v1/admin/residents/2/reset-password", headers=ADMIN)
    assert r.status_code == 200
    assert len(r.json()["temporary_password"]) >= 12


@pytest.mark.asyncio
async def test_dat_lai_mat_khau_khi_chua_co_tai_khoan_dang_nhap_tra_409(client):
    """User 3 chưa có auth_user_id — không có mật khẩu nào để đặt lại.

    Không phải trường hợp lý thuyết: `seed_data` xoá sạch auth_user_id, ai chạy
    seed mà quên `provision_auth` là rơi vào đúng đây.
    """
    r = await client.post("/api/v1/admin/residents/3/reset-password", headers=ADMIN)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_profile_khong_lo_auth_user_id(client):
    """`_user_dict` nay trả `auth_user_id` để route quản trị dùng, nhưng
    `ProfileResponse` không khai trường này nên nó không được lọt ra API."""
    r = await client.get("/api/v1/profile", headers=OWNER)
    assert r.status_code == 200
    assert "auth_user_id" not in r.json()


@pytest.mark.asyncio
async def test_bql_xem_duoc_chi_tiet_mot_cu_dan(client):
    await _create(client, CAR_CARD_ITEM)

    r = await client.get("/api/v1/admin/residents/2", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["profile"]["full_name"] == "Trần Văn An"
    assert body["account_status"] == "active"
    assert len(body["checklist"]["items"]) > 0
    assert len(body["applications"]) == 1


@pytest.mark.asyncio
async def test_chi_tiet_phan_anh_muc_da_hoan_thanh(client):
    """conftest đánh dấu user 2 đã xong mục 1."""
    body = (await client.get("/api/v1/admin/residents/2", headers=ADMIN)).json()
    done = [i["id"] for i in body["checklist"]["items"] if i["completed"]]
    assert 1 in done


@pytest.mark.asyncio
async def test_cu_dan_khong_xem_duoc_chi_tiet_nguoi_khac(client):
    r = await client.get("/api/v1/admin/residents/3", headers=OWNER)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_chi_tiet_tai_khoan_bql_tra_404(client):
    r = await client.get("/api/v1/admin/residents/1", headers=ADMIN)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_chi_tiet_cu_dan_khong_ton_tai_tra_404(client):
    r = await client.get("/api/v1/admin/residents/9999", headers=ADMIN)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_bql_co_trang_thai_tai_khoan(client):
    rows = (await client.get("/api/v1/admin/dashboard", headers=ADMIN)).json()
    assert all("account_status" in r for r in rows["residents"])


# --- BQL nạp tài liệu (US-08) -------------------------------------------
#
# `fake_ingest` (autouse, tests/conftest.py) chặn cả `ingest_file` thật lẫn
# `SessionLocal` thật — job nền không được chạm production DB hay Google
# embedding API. Vẫn khai rõ tham số ở đây cho dễ đọc dù không bắt buộc.
#
# Route ghi file `.md` THẬT vào `data/kb/bql/` trước khi tạo bản ghi DB (đó là
# phần route không mock được qua fixture) — nên các test dưới đây tự dọn tệp
# mình tạo ra, để `git status` sạch sau khi chạy.


@pytest.fixture(autouse=True)
def _cleanup_bql_kb_files():
    from src.services.ingest import KB_DIR

    bql_dir = KB_DIR / "bql"
    before = set(bql_dir.iterdir())
    yield
    for path in set(bql_dir.iterdir()) - before:
        path.unlink()


@pytest.mark.asyncio
async def test_bql_nap_tai_lieu_moi(client, fake_ingest):
    r = await client.post(
        "/api/v1/admin/documents",
        json={"title": "Quy trình mới", "content": "# Quy trình\n\nNội dung."},
        headers=ADMIN,
    )
    assert r.status_code == 201
    assert r.json()["title"] == "Quy trình mới"
    # Response của POST là snapshot NGAY LÚC TẠO — trước khi job nền chạy
    # (BackgroundTasks chỉ chạy SAU khi body đã gửi), nên luôn là "pending" ở
    # đây. Trạng thái sau embed được kiểm ở test riêng bên dưới bằng cách
    # tra lại qua GET.
    assert r.json()["embed_status"] == "pending"


@pytest.mark.asyncio
async def test_bql_nap_tai_lieu_thanh_cong_chuyen_sang_ready(client, fake_ingest):
    """State machine pending -> processing -> ready phải QUAN SÁT ĐƯỢC.

    `fake_ingest` trỏ `SessionLocal` giả về CHÍNH `db_session` của test, nên
    `_embed_document` ghi trạng thái vào đúng nơi test đọc lại được. Xoá hẳn
    `_embed_document` (hoặc quên gọi `set_embed_status(..., "ready")`) sẽ làm
    assertion dưới đây đỏ — khác với round trước, lúc "ready" nằm trong set
    ba giá trị nên test không bao giờ fail dù job nền bị xoá.

    `await client.post(...)` đã chạy xong nghĩa là background task cũng đã
    chạy xong: `ASGITransport` thực thi `BackgroundTasks` như một phần của
    cùng lệnh gọi ASGI app mà `client.post` await, không phải một luồng/task
    tách biệt — nên không cần chờ gì thêm trước khi GET lại.
    """
    r = await client.post(
        "/api/v1/admin/documents",
        json={"title": "Quy trình embed thành công", "content": "# A\n\nB."},
        headers=ADMIN,
    )
    document_id = r.json()["document_id"]

    rows = (await client.get("/api/v1/admin/documents", headers=ADMIN)).json()
    updated = next((d for d in rows if d["document_id"] == document_id), None)
    assert updated is not None
    assert updated["embed_status"] == "ready"


@pytest.mark.asyncio
async def test_bql_nap_tai_lieu_loi_embed_chuyen_sang_failed(client, fake_ingest, monkeypatch):
    """`ingest_file` lỗi thì trạng thái phải dừng ở "failed", KHÔNG mất dòng.

    Ghi đè lại `routes.ingest_file` (đã được `fake_ingest` gắn sẵn) thành hàm
    luôn raise, mô phỏng lỗi thật (Google API lỗi, file hỏng, v.v.) mà không
    chạm mạng.
    """
    from src.api import routes

    def _raise(_db, _path):
        raise RuntimeError("giả lập lỗi embed")

    monkeypatch.setattr(routes, "ingest_file", _raise)

    r = await client.post(
        "/api/v1/admin/documents",
        json={"title": "Quy trình embed lỗi", "content": "# A\n\nB."},
        headers=ADMIN,
    )
    document_id = r.json()["document_id"]

    rows = (await client.get("/api/v1/admin/documents", headers=ADMIN)).json()
    updated = next((d for d in rows if d["document_id"] == document_id), None)
    assert updated is not None
    assert updated["embed_status"] == "failed"


@pytest.mark.asyncio
async def test_cu_dan_khong_nap_duoc_tai_lieu(client, fake_ingest):
    r = await client.post(
        "/api/v1/admin/documents",
        json={"title": "X", "content": "Y"},
        headers=OWNER,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_tai_lieu_rong_bi_tu_choi(client, fake_ingest):
    r = await client.post(
        "/api/v1/admin/documents",
        json={"title": "X", "content": "   "},
        headers=ADMIN,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_bql_xem_duoc_danh_sach_tai_lieu(client, fake_ingest):
    await client.post(
        "/api/v1/admin/documents",
        json={"title": "Quy trình mới", "content": "# A\n\nB."},
        headers=ADMIN,
    )
    rows = (await client.get("/api/v1/admin/documents", headers=ADMIN)).json()
    assert any(d["title"] == "Quy trình mới" for d in rows)


# --- Giới hạn tốc độ theo IP (task 18, guardrail V2/C3) -------------------
#
# `src/services/rate_limit.py` có test riêng cho phần thuần (cửa sổ cố định,
# dọn bucket hết hạn) ở `tests/test_services/test_rate_limit.py`. Ở đây chỉ
# kiểm hành vi qua HTTP thật: đúng endpoint bị chặn, đúng mã 429, IP tách theo
# `X-Forwarded-For`, và endpoint KHÔNG bị giới hạn (polling) không bị vạ lây.
#
# Số lượt CỐ TÌNH viết cứng bằng đúng giá trị mặc định nêu trong task 18 (10
# lượt/phút cho `/chat`, 20 lượt/phút cho tải tệp/nạp tài liệu) thay vì đọc lại
# từ `get_settings()`: nếu đọc lại từ settings, test sẽ luôn tự khớp theo bất
# kỳ giá trị nào đang cấu hình — kể cả khi cấu hình không thật sự được endpoint
# tôn trọng — nên không bao giờ tự phát hiện được lỗi "trần đã bị nới lỏng".
# Việc viết cứng đã được XÁC MINH bằng cách tạm nới `chat_rate_limit_per_minute`
# trong `src/config.py` lên rất cao và quan sát đúng test dưới đây báo đỏ (xem
# `.superpowers/sdd/2026-08-18-ux-va-console-bql/task-18-report.md`).
#
# `tests/conftest.py::_reset_rate_limits` (autouse) xoá sạch bộ đếm trước mỗi
# test — nếu không, các test /chat rải rác phía trên (không test nào tự coi
# mình đang "dùng hạn mức") sẽ cộng dồn vào cùng bucket IP mặc định của
# `httpx.ASGITransport` và làm rớt 429 ngẫu nhiên tuỳ thứ tự chạy.

CHAT_LIMIT_PER_MINUTE = 10
UPLOAD_LIMIT_PER_MINUTE = 20


@pytest.mark.asyncio
async def test_chat_qua_han_muc_phut_tra_429_kem_retry_after(client, fake_chat_graph):
    """Lượt thứ N+1 trong CÙNG một phút (N = 10, `chat_rate_limit_per_minute`
    mặc định) phải bị chặn — không phải lượt thứ N hay N+2."""
    for _ in range(CHAT_LIMIT_PER_MINUTE):
        r = await client.post(
            "/api/v1/chat", json={"message": "Thẻ xe cần gì?"}, headers=OWNER
        )
        assert r.status_code == 200

    blocked = await client.post(
        "/api/v1/chat", json={"message": "Thẻ xe cần gì?"}, headers=OWNER
    )
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    detail = blocked.json()["detail"]
    # Thông điệp cho người dùng, không phải chi tiết nội bộ.
    assert "quota" not in detail.lower()
    assert "hạn mức" not in detail.lower()
    assert "đợi" in detail


@pytest.mark.asyncio
async def test_chat_qua_cua_so_thi_goi_lai_duoc(client, fake_chat_graph, monkeypatch):
    """Đồng hồ giả (không `sleep()` thật) — sang cửa sổ mới thì được gọi lại."""
    from src.services import rate_limit

    state = {"now": 1_000_000.0}
    monkeypatch.setattr(rate_limit, "clock", lambda: state["now"])

    for _ in range(CHAT_LIMIT_PER_MINUTE):
        r = await client.post(
            "/api/v1/chat", json={"message": "Thẻ xe cần gì?"}, headers=OWNER
        )
        assert r.status_code == 200
    blocked = await client.post(
        "/api/v1/chat", json={"message": "Thẻ xe cần gì?"}, headers=OWNER
    )
    assert blocked.status_code == 429

    state["now"] += 60  # sang cửa sổ phút kế tiếp
    r = await client.post(
        "/api/v1/chat", json={"message": "Thẻ xe cần gì?"}, headers=OWNER
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_hai_ip_khac_nhau_khong_dung_chung_han_muc_chat(client, fake_chat_graph):
    """Đây là test khoá lại đúng lỗi dễ mắc nhất: nếu limiter lỡ khoá theo IP
    của proxy Railway (giống nhau cho mọi người) thay vì `X-Forwarded-For`,
    IP thứ hai sẽ bị ăn ké hạn mức đã cạn của IP thứ nhất."""
    ip1 = {**OWNER, "X-Forwarded-For": "203.0.113.10"}
    ip2 = {**OWNER, "X-Forwarded-For": "203.0.113.20"}

    for _ in range(CHAT_LIMIT_PER_MINUTE):
        r = await client.post(
            "/api/v1/chat", json={"message": "Thẻ xe cần gì?"}, headers=ip1
        )
        assert r.status_code == 200
    assert (
        await client.post("/api/v1/chat", json={"message": "Thẻ xe cần gì?"}, headers=ip1)
    ).status_code == 429

    # IP thứ hai chưa từng gọi — không được phép bị chặn theo.
    r = await client.post(
        "/api/v1/chat", json={"message": "Thẻ xe cần gì?"}, headers=ip2
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_tai_anh_qua_han_muc_phut_bi_chan_429(client):
    """Endpoint tải tệp minh chứng có ngưỡng riêng (`upload_rate_limit_per_minute`,
    mặc định 20/phút), tách khỏi ngưỡng `/chat`."""
    app = await _create(client, RESIDENCY_ITEM)
    for _ in range(UPLOAD_LIMIT_PER_MINUTE):
        r = await _upload(client, app["application_id"])
        assert r.status_code == 201

    r = await _upload(client, app["application_id"])
    assert r.status_code == 429


@pytest.mark.asyncio
async def test_nap_tai_lieu_qua_han_muc_khong_lam_hong_polling_embed_status(
    client, fake_ingest
):
    """Frontend poll `GET /admin/documents` liên tục trong lúc chờ embed —
    endpoint đó KHÔNG bị giới hạn, kể cả khi `POST /admin/documents` đã bị
    chặn 429. Đây là lằn ranh cố ý của task 18: chỉ chặn endpoint TỐN TIỀN,
    không chặn endpoint đọc."""
    for i in range(UPLOAD_LIMIT_PER_MINUTE):
        r = await client.post(
            "/api/v1/admin/documents",
            json={"title": f"Quy trình giới hạn {i}", "content": "# A\n\nB."},
            headers=ADMIN,
        )
        assert r.status_code == 201

    blocked = await client.post(
        "/api/v1/admin/documents",
        json={"title": "Quy trình vượt hạn mức", "content": "# A\n\nB."},
        headers=ADMIN,
    )
    assert blocked.status_code == 429

    # GET không bị đụng tới — polling vẫn sống, không bị vạ lây.
    for _ in range(5):
        r = await client.get("/api/v1/admin/documents", headers=ADMIN)
        assert r.status_code == 200


# --- AI Form Generation (Task 5) ----------------------------------------


@pytest.mark.asyncio
async def test_get_form_schema_ok(client, db_session):
    from src.models.db import ChecklistItem

    # Seed data khong co form_schema — them item voi form_schema de test.
    item = ChecklistItem(
        checklist_item_id=99,
        task_name="Thu tuc test",
        item_type="bql_actionable",
        form_schema={"fields": [], "attachments": []},
    )
    db_session.add(item)
    db_session.commit()

    res = await client.get("/api/v1/checklist/99/form-schema", headers=OWNER)
    assert res.status_code == 200
    assert "fields" in res.json()


@pytest.mark.asyncio
async def test_get_form_schema_null(client, db_session):
    from src.models.db import ChecklistItem

    # Lay item tu seed data (khong co form_schema).
    item = db_session.query(ChecklistItem).filter(
        ChecklistItem.form_schema.is_(None)
    ).first()
    res = await client.get(f"/api/v1/checklist/{item.checklist_item_id}/form-schema", headers=OWNER)
    assert res.status_code == 404


# --- AI dẫn dắt điền hồ sơ, đi qua HTTP thật (22/08) --------------------
#
# Ba bug lọt tới nhánh này (`ChatRequest` thiếu `checklist_item_id`, dùng
# `item.id` thay `item.checklist_item_id`, phản hồi thiếu trường bắt buộc của
# `ChatResponse`) đều là loại chỉ lộ ra khi gọi thật qua HTTP — unit test gọi
# thẳng hàm không đụng tới lớp Pydantic. Giữ ít nhất một luồng trọn vẹn ở đây.


@pytest.fixture
def vehicle_form(db_session):
    """Gắn `form_schema` vào một thủ tục có thật trong seed."""
    from src.models.db import ChecklistItem

    item = db_session.query(ChecklistItem).filter(
        ChecklistItem.task_name == "Đăng ký thẻ xe"
    ).one()
    item.form_schema = {
        "fields": [
            {"key": "vehicle_type", "label": "Loại phương tiện", "type": "select",
             "options": ["Ô tô", "Xe máy"], "required": True,
             "question": "Bạn đăng ký thẻ xe gì?"},
            {"key": "plate", "label": "Biển số xe", "type": "text", "required": True,
             "question": "Biển số xe của bạn là gì?", "pattern": r"^[0-9A-Z\-\.]{5,15}$"},
        ],
        "attachments": [],
    }
    db_session.commit()
    return item


@pytest.mark.asyncio
async def test_luong_dien_ho_so_qua_http(client, fake_chat_graph, vehicle_form):
    """AI hỏi từng trường, FE chỉ việc gửi lại state — không cần nhớ gì ở server."""
    first = (await client.post(
        "/api/v1/chat",
        json={"message": "Tôi muốn đăng ký thẻ xe"},
        headers=OWNER,
    )).json()

    assert first["intent"] == "form_generation"
    assert first["checklist_item_id"] == vehicle_form.checklist_item_id
    assert "Bạn đăng ký thẻ xe gì?" in first["answer"]
    assert first["form_schema"]["fields"][0]["key"] == "vehicle_type"
    assert first["sources"] == [], "lượt điền form không truy xuất tài liệu nên không có nguồn"

    second = (await client.post(
        "/api/v1/chat",
        json={
            "message": "ô tô",
            "checklist_item_id": first["checklist_item_id"],
            "form_data": first["form_data"],
            "conversation_id": first["conversation_id"],
        },
        headers=OWNER,
    )).json()

    assert second["form_data"]["vehicle_type"] == "Ô tô"
    assert "Biển số xe của bạn là gì?" in second["answer"]

    third = (await client.post(
        "/api/v1/chat",
        json={
            "message": "30A-123.45",
            "checklist_item_id": second["checklist_item_id"],
            "form_data": second["form_data"],
            "conversation_id": second["conversation_id"],
        },
        headers=OWNER,
    )).json()

    assert third["intent"] == "form_review"
    assert third["form_data"] == {"vehicle_type": "Ô tô", "plate": "30A-123.45"}


@pytest.mark.asyncio
async def test_cau_hoi_thong_tin_van_di_duong_rag(client, fake_chat_graph, vehicle_form):
    """Hồi quy quan trọng nhất: có `form_schema` rồi thì câu hỏi thường vẫn phải
    được RAG trả lời kèm nguồn, không bị nuốt vào luồng điền form."""
    data = (await client.post(
        "/api/v1/chat",
        json={"message": "Đăng ký thẻ xe cần giấy tờ gì?"},
        headers=OWNER,
    )).json()

    assert data["intent"] == "qa"
    assert data["answer_source"] == "rag"
    assert data["sources"], "US-05 đòi câu trả lời phải kèm nguồn trích dẫn"


@pytest.mark.asyncio
async def test_luot_dien_form_van_vao_lich_su_hoi_thoai(
    client, fake_chat_graph, vehicle_form, db_session
):
    """Thiếu bước ghi lịch sử thì hội thoại điền hồ sơ biến mất khỏi danh sách."""
    first = (await client.post(
        "/api/v1/chat", json={"message": "Tôi muốn đăng ký thẻ xe"}, headers=OWNER
    )).json()

    rows = db_session.query(ChatHistory).filter(
        ChatHistory.conversation_id == uuid.UUID(first["conversation_id"])
    ).all()
    assert len(rows) == 1
    assert rows[0].question == "Tôi muốn đăng ký thẻ xe"
