"""Tests for form extraction — regex + heuristic, no LLM."""

from src.ai.form_extraction import _normalize, extract_form_fields
from src.models.schemas import FormFieldSchema, FormSchemaPayload

schema = FormSchemaPayload(
    fields=[
        FormFieldSchema(
            key="vehicle_type",
            label="Loại phương tiện",
            type="select",
            options=["Ô tô", "Xe máy"],
            required=True,
            question="Bạn đăng ký thẻ xe gì?",
        ),
        FormFieldSchema(
            key="plate",
            label="Biển số",
            type="text",
            required=True,
            question="Biển số xe của bạn là gì?",
        ),
        FormFieldSchema(
            key="quantity",
            label="Số thẻ",
            type="number",
            required=False,
            default="1",
            question="Bạn cần bao nhiêu thẻ?",
        ),
    ]
)


def test_extract_select():
    history = [
        {"role": "assistant", "content": "Bạn đăng ký thẻ xe gì?"},
        {"role": "user", "content": "Ô tô"},
    ]
    result = extract_form_fields(schema, history)
    assert result["vehicle_type"] == "Ô tô"


def test_extract_text():
    history = [
        {"role": "assistant", "content": "Biển số xe của bạn là gì?"},
        {"role": "user", "content": "30A-123.45"},
    ]
    result = extract_form_fields(schema, history)
    assert result["plate"] == "30A-123.45"


def test_default_value():
    """Non-numeric input falls back to default for number fields."""
    history = [{"role": "user", "content": "một thôi"}]
    result = extract_form_fields(schema, history)
    assert result["quantity"] == "1"


def test_extract_number():
    """Numeric input is extracted for number fields."""
    history = [{"role": "user", "content": "2"}]
    result = extract_form_fields(schema, history)
    assert result["quantity"] == "2"


def test_normalize_handles_vietnamese_diacritics():
    assert _normalize("Ô tô") == "o to"
    assert _normalize("Xe máy") == "xe may"
    assert _normalize("Đăng ký") == "dang ky"
    assert _normalize("Biển số") == "bien so"
