import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.ai.intent import _extract_keywords, _normalize, detect_procedure_intent
from src.models.db import Base, ChecklistItem


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = session_factory()
    # Seed test data: 2 items, 1 has form_schema
    session.add(ChecklistItem(
        task_name="Đăng ký thẻ xe",
        item_type="bql_actionable",
        form_schema={"fields": [], "attachments": []},
    ))
    session.add(ChecklistItem(
        task_name="Làm thẻ cư dân (chủ hộ)",
        item_type="bql_actionable",
        form_schema=None,
    ))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def test_normalize():
    assert _normalize("Đăng ký") == "dang ky"
    assert _normalize("Ô tô") == "o to"


def test_extract_keywords():
    assert "dang" in _extract_keywords("Tôi muốn đăng ký thẻ xe máy")
    assert len(_extract_keywords("ab")) == 0  # <3 chars


def test_keyword_exact_match(db_session):
    match = detect_procedure_intent("Tôi muốn đăng ký thẻ xe máy", db_session)
    assert match.item is not None
    assert match.item.task_name == "Đăng ký thẻ xe"
    assert match.confidence == "high"
    assert not match.ambiguous


def test_no_form_schema_returns_none(db_session):
    # "Làm thẻ cư dân" has form_schema=None → should not match
    match = detect_procedure_intent("Làm thẻ cư dân", db_session)
    assert match.ambiguous  # falls to LLM fallback


def test_no_match_returns_low_confidence(db_session):
    match = detect_procedure_intent("Cho tôi xem thời tiết Hà Nội", db_session)
    assert match.item is None
    assert match.confidence == "low"
    assert match.ambiguous
