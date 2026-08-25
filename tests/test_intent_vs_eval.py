"""Cổng nhận ý định không được nuốt câu hỏi của bộ eval.

Chạy **toàn bộ** `eval/questions.yaml` qua đúng cái cổng mà `/chat` dùng, trên
đúng dữ liệu `seed_data` + `seed_form_schema` thật. Chỉ hai câu FG (cố ý viết
để kích hoạt luồng điền hồ sơ) được giữ lại; 35 câu còn lại phải nhường hết
cho RAG.

**Vì sao cần một test riêng cho việc này.** Ngày 25/08 đo được 14/35 câu bị
luồng form giữ mất — trong đó có Q31 *"Cho tôi công thức nấu phở bò"*, câu demo
bước 7 chứng minh hệ thống từ chối thay vì bịa. Không có gì báo động: `/chat`
vẫn trả 200, test vẫn xanh, chỉ có `answer_source` lặng lẽ thành `no_context`
và `run_eval` sẽ chấm thành "từ chối" — trông y như RAG hỏng.

Đây là chỗ hai vai giao nhau: luồng điền hồ sơ chạy TRƯỚC RAG, nên mỗi lần nới
điều kiện nhận ý định là một lần có thể lấy mất câu hỏi của US-05. Test này
đứng ngay ranh giới đó.
"""

from pathlib import Path

import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from scripts.seed_data import CHECKLIST_ITEMS
from scripts.seed_form_schema import PROCEDURES
from src.ai import form_dialog
from src.models.db import Base, ChecklistItem

# Hai câu cố ý viết để kích hoạt luồng điền hồ sơ — xem `eval/questions.yaml`.
FORM_QUESTIONS = {"FG01": "form_generation", "FG02": "disambiguation"}

QUESTIONS = yaml.safe_load(
    (Path(__file__).resolve().parents[1] / "eval" / "questions.yaml").read_text(encoding="utf-8")
)["questions"]


@pytest.fixture(scope="module")
def seeded_db():
    """Checklist thật + form_schema thật — không rút gọn.

    Dùng chính `CHECKLIST_ITEMS` và `PROCEDURES` chứ không dựng dữ liệu riêng:
    tên thủ tục thật mới sinh ra được các va chạm chữ như "phở"/"phòng".
    """
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    session.add_all([ChecklistItem(**item) for item in CHECKLIST_ITEMS])
    session.commit()

    for task_name, payload in PROCEDURES.items():
        row = session.query(ChecklistItem).filter(
            ChecklistItem.task_name == task_name
        ).first()
        if row is not None:
            row.form_schema = payload.model_dump() if payload else None
    session.commit()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture(autouse=True)
def _llm_phai_hong(monkeypatch):
    """Không câu nào trong bộ eval được phép cần tới LLM để phân loại đúng.

    LLM hỏng có chủ ý: lớp 3 chỉ nên chạy cho câu paraphrase thật sự, và bộ
    eval không có câu nào như vậy. Test đỏ ở đây nghĩa là cổng vừa bắt đầu tiêu
    tiền cho những câu lẽ ra chặn được tất định.
    """
    monkeypatch.setattr("src.ai.intent.get_chat_llm", lambda: None)


@pytest.mark.asyncio
@pytest.mark.parametrize("question", QUESTIONS, ids=lambda q: q["id"])
async def test_chi_hai_cau_fg_duoc_vao_luong_dien_ho_so(seeded_db, question):
    turn = await form_dialog.run_form_turn(seeded_db, question["question"], None, None)
    intent_mong_doi = FORM_QUESTIONS.get(question["id"])

    if intent_mong_doi is None:
        assert turn is None, (
            f"{question['id']} bị luồng điền hồ sơ giữ mất "
            f"(intent={turn.intent}) — RAG không bao giờ được hỏi: "
            f"{question['question']!r}"
        )
        return

    assert turn is not None, f"{question['id']} phải vào luồng điền hồ sơ"
    assert turn.intent == intent_mong_doi


@pytest.mark.asyncio
async def test_fg01_mo_dung_thu_tuc_chu_khong_phai_thu_tuc_gan_giong(seeded_db):
    """"…thẻ XE MÁY…" từng bị kéo về "thẻ thang MÁY" — mở nhầm form.

    Giữ lại được câu hỏi là chưa đủ; phải mở đúng thủ tục người ta hỏi.
    """
    turn = await form_dialog.run_form_turn(
        seeded_db, "Tôi muốn đăng ký thẻ xe máy biển 29P1-123.45", None, None
    )
    assert turn is not None
    item = seeded_db.get(ChecklistItem, turn.checklist_item_id)
    assert item.task_name == "Đăng ký thẻ xe"
