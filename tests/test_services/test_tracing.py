"""LangSmith tracing — cấu hình phải do `.env` quyết, không do environ tình cờ."""

import os

import pytest

from src.config import Settings
from src.services.tracing import configure_tracing

_KEYS = ("LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY", "LANGCHAIN_PROJECT", "LANGCHAIN_ENDPOINT")


@pytest.fixture(autouse=True)
def _moi_truong_sach(monkeypatch):
    for key in _KEYS:
        monkeypatch.delenv(key, raising=False)


def _settings(**kwargs) -> Settings:
    return Settings(_env_file=None, **kwargs)


def test_bat_thi_export_du_bon_bien():
    assert configure_tracing(_settings(
        langchain_tracing_v2=True,
        langchain_api_key="ls-fake",
        langchain_project="moveinmate-test",
    )) is True

    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGCHAIN_API_KEY"] == "ls-fake"
    assert os.environ["LANGCHAIN_PROJECT"] == "moveinmate-test"
    assert os.environ["LANGCHAIN_ENDPOINT"]


def test_tat_thi_don_sach_bien_con_sot_trong_environ(monkeypatch):
    """Sót `LANGCHAIN_TRACING_V2=true` từ shell trước = gửi prompt ra ngoài ngoài ý muốn."""
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "ls-cu-con-sot")

    assert configure_tracing(_settings(langchain_tracing_v2=False)) is False
    assert "LANGCHAIN_TRACING_V2" not in os.environ
    assert "LANGCHAIN_API_KEY" not in os.environ


def test_bat_ma_thieu_key_thi_tat_han_chu_khong_de_hong_chat():
    """Thiếu key mà vẫn bật thì LangChain ném lỗi ở MỌI lượt gọi LLM."""
    assert configure_tracing(_settings(
        langchain_tracing_v2=True, langchain_api_key=""
    )) is False
    assert "LANGCHAIN_TRACING_V2" not in os.environ


def test_khong_in_key_ra_log(caplog):
    caplog.set_level("INFO", logger="moveinmate")
    configure_tracing(_settings(
        langchain_tracing_v2=True, langchain_api_key="ls-bi-mat-tuyet-doi"
    ))
    assert "ls-bi-mat-tuyet-doi" not in caplog.text, "repo có hook đẩy log lên server chấm"
