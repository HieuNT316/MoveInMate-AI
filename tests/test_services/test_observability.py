"""Log có cấu trúc (V5, `src/observability.py`).

Test hình dạng JSON và guard chống lộ secret trực tiếp trên `JsonFormatter`,
không qua toàn bộ pipeline logging — cấu hình logging chạy một lần lúc
`src.main` được import (`configure_logging`), gọi lại giữa các test dễ đụng
vào cơ chế bắt log của pytest hơn là cần thiết cho việc kiểm hình dạng JSON.
"""

import json
import logging

from src.observability import JsonFormatter, RequestIdFilter, request_id_var


def _make_record(msg: str, exc_info=None) -> logging.LogRecord:
    record = logging.LogRecord(
        name="moveinmate.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=exc_info,
    )
    RequestIdFilter().filter(record)
    return record


def test_dong_log_la_json_hop_le_co_request_id():
    token = request_id_var.set("req-abc-123")
    try:
        record = _make_record("xin chao")
    finally:
        request_id_var.reset(token)

    rendered = JsonFormatter().format(record)
    payload = json.loads(rendered)

    assert payload["request_id"] == "req-abc-123"
    assert payload["message"] == "xin chao"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "moveinmate.test"
    assert "timestamp" in payload


def test_mat_khau_trong_connection_string_khong_lot_vao_log():
    """Test chốt: đây là test đáng lẽ đã bắt được cả nhóm lỗi lộ secret.

    Mô phỏng đúng hình dạng OperationalError của SQLAlchemy — nhét thẳng
    connection string (kèm mật khẩu) vào message của exception.
    """
    secret_password = "S3cretSupabasePass!"
    try:
        raise RuntimeError(
            f"could not connect to server: postgresql://appuser:{secret_password}"
            "@db.example.supabase.co:5432/postgres"
        )
    except RuntimeError:
        import sys

        record = _make_record("unhandled_exception", exc_info=sys.exc_info())

    rendered = JsonFormatter().format(record)

    assert secret_password not in rendered
    assert "***" in rendered


def test_request_id_da_gan_san_khong_bi_filter_ghi_de():
    """Handler bắt lỗi tập trung tự gắn request_id qua `extra=` sau khi
    contextvar đã bị middleware reset — filter không được ghi đè giá trị đó.
    """
    record = logging.LogRecord(
        name="moveinmate.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="unhandled_exception",
        args=(),
        exc_info=None,
    )
    record.request_id = "explicit-id"
    RequestIdFilter().filter(record)

    assert record.request_id == "explicit-id"
