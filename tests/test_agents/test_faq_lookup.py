"""Node `faq_lookup` — trả lời bằng FAQ do BQL soạn, trước khi động tới RAG.

Phần lớn giá trị nằm ở các ca **không** được khớp: FAQ trả lời không kèm trích
dẫn, nên mỗi lần khớp nhầm là một lần cư dân mất phần nguồn tài liệu mà US-05
bắt buộc phải có.
"""

import pytest

from src.agents.nodes.faq_lookup import best_match, faq_lookup_node, similarity

FAQS = [
    {"faq_id": 1, "question": "Làm thẻ cư dân như thế nào?", "answer": "Nộp CCCD tại lễ tân."},
    {"faq_id": 2, "question": "Giờ mở cửa bể bơi?", "answer": "6h–21h hằng ngày."},
    {"faq_id": 3, "question": "Phí gửi xe ô tô hằng tháng?", "answer": "1.200.000đ/tháng."},
]


# --- Hàm thuần -----------------------------------------------------------


def test_so_theo_tu_khong_theo_chuoi_con():
    """"phở" (pho) nằm lọt trong "phòng" (phong) — so chuỗi con là khớp bừa.

    Đúng cái bẫy đã làm hỏng cổng nhận ý định ngày 25/08.
    """
    assert similarity("Cho tôi công thức nấu phở bò", "Giờ mở cửa phòng gym?") == 0.0


def test_cau_gan_giong_thi_diem_cao():
    assert similarity("Làm thẻ cư dân thế nào?", "Làm thẻ cư dân như thế nào?") > 0.8


def test_cau_khac_chu_de_thi_diem_thap():
    assert similarity("Giờ mở cửa bể bơi?", "Làm thẻ cư dân như thế nào?") < 0.3


def test_mat_the_khong_bi_lan_voi_lam_the():
    """Ca nguy hiểm nhất: hai câu chỉ khác một động từ nhưng khác hẳn nghĩa.

    Trả hướng dẫn *làm thẻ* cho người vừa *mất thẻ* là sai mà nghe rất trôi
    chảy — người dùng không có dấu hiệu gì để nhận ra. Bản dùng "bỏ dấu + bỏ
    stopword" chấm cặp này 0.667 và khớp nhầm ở ngưỡng 0.5.
    """
    diem = similarity("Mất thẻ cư dân thì làm sao?", "Làm thẻ cư dân như thế nào?")
    assert diem < 0.5, f"phải nhường cho RAG, đang chấm {diem}"


def test_hoa_diem_thi_khong_chon_bua():
    """Hai FAQ cùng điểm = câu hỏi mơ hồ. Thà để RAG trả lời còn hơn chọn bừa."""
    hoa = [
        {"faq_id": 1, "question": "Thẻ xe ô tô", "answer": "A"},
        {"faq_id": 2, "question": "Thẻ xe ô tô", "answer": "B"},
    ]
    faq, score = best_match("thẻ xe ô tô", hoa)
    assert faq is None
    assert score > 0


# --- Node ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_khong_co_faq_thi_khong_lam_gi():
    """Trạng thái hiện tại của hệ thống — bảng `faq` còn rỗng."""
    assert await faq_lookup_node({"query": "Làm thẻ cư dân thế nào?"}) == {}


@pytest.mark.asyncio
async def test_khop_thi_tra_loi_va_khong_kem_nguon():
    result = await faq_lookup_node({"query": "Làm thẻ cư dân như thế nào?", "faqs": FAQS})

    assert result["answer_source"] == "faq"
    assert result["answer"] == "Nộp CCCD tại lễ tân."
    assert result["matched_faq_id"] == 1
    assert result["sources"] == [], "FAQ do BQL soạn, không trích từ tài liệu nào"


@pytest.mark.asyncio
async def test_khong_du_giong_thi_nhuong_cho_rag():
    """Trả `{}` = state không đổi, graph đi tiếp sang `rag_retrieve`."""
    assert await faq_lookup_node({"query": "Phí bảo trì 2% tính thế nào?", "faqs": FAQS}) == {}


@pytest.mark.asyncio
async def test_dung_cau_da_viet_lai_chu_khong_phai_cau_goc():
    """Câu tiếp nối phải được `rewrite_query` xử lý trước rồi mới so với FAQ.

    So bằng "còn cái đó thì sao?" thì không bao giờ khớp FAQ nào.
    """
    result = await faq_lookup_node({
        "query": "còn cái đó thì sao?",
        "standalone_query": "Giờ mở cửa bể bơi?",
        "faqs": FAQS,
    })
    assert result["matched_faq_id"] == 2


@pytest.mark.asyncio
async def test_nguong_quyet_dinh_khop_hay_khong(monkeypatch):
    """Ngưỡng là núm vặn thật — cùng một câu, hai ngưỡng ra hai kết quả.

    Không đụng `get_settings.cache_clear()`: cache là toàn cục, xoá trong một
    test thì test khác chạy sau nhận `Settings` dựng lại từ `.env` của máy
    người chạy.
    """
    from dataclasses import dataclass

    @dataclass
    class _Nguong:
        faq_min_similarity: float

    cau = {"query": "Làm thẻ cư dân thế nào?", "faqs": FAQS}

    monkeypatch.setattr("src.agents.nodes.faq_lookup.get_settings", lambda: _Nguong(0.95))
    assert await faq_lookup_node(cau) == {}, "ngưỡng ngặt thì nhường RAG"

    monkeypatch.setattr("src.agents.nodes.faq_lookup.get_settings", lambda: _Nguong(0.5))
    assert (await faq_lookup_node(cau))["matched_faq_id"] == 1
