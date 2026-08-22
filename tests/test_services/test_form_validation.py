"""Tests for validate_form_data in store.py."""

from src.models.schemas import FormFieldSchema, FormSchemaPayload
from src.services.store import validate_form_data


def test_validate_missing_required():
    schema = FormSchemaPayload(fields=[
        FormFieldSchema(key="plate", label="Biển số", type="text",
                       required=True, pattern=r"^[0-9A-Z\-]{5,15}$",
                       question="Nhập biển số xe"),
    ])
    errors = validate_form_data(schema, {})
    assert any("Thiếu: Biển số" in e for e in errors)


def test_validate_invalid_pattern():
    schema = FormSchemaPayload(fields=[
        FormFieldSchema(key="plate", label="Biển số", type="text",
                       required=True, pattern=r"^[0-9A-Z\-]{5,15}$",
                       question="Nhập biển số xe"),
    ])
    errors = validate_form_data(schema, {"plate": "abc"})
    assert any("sai định dạng" in e for e in errors)


def test_validate_ok():
    schema = FormSchemaPayload(fields=[
        FormFieldSchema(key="plate", label="Biển số", type="text",
                       required=True, pattern=r"^[0-9A-Z\.\-]{5,15}$",
                       question="Nhập biển số xe"),
    ])
    errors = validate_form_data(schema, {"plate": "30A-123.45"})
    assert errors == []
