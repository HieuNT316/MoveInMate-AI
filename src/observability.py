"""Log có cấu trúc (V5) + hạ tầng cho bắt lỗi tập trung (V9).

Xem docs/ROLES_AND_PLAN.md mục V5/V9. Mỗi dòng log là một object JSON, luôn
có `request_id` để lần một request qua nhiều lớp.

An toàn secret: `OperationalError` của SQLAlchemy nhét nguyên chuỗi kết nối
(kèm mật khẩu) vào message của exception. `logger.exception(...)` ghi lại
traceback đầy đủ, nên nếu không xử lý, mật khẩu Supabase sẽ nằm thẳng trong
log — và repo có pre-push hook đẩy log lên server chấm điểm. `_redact()` áp
cùng kiểu regex với `safe_database_url()` (src/config.py) lên MỌI dòng log,
không chỉ chỗ ta chủ động gọi `safe_database_url()`.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from contextvars import ContextVar

logger = logging.getLogger("moveinmate")

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Cùng dạng với regex trong safe_database_url(): "scheme://user:password@host".
_SECRET_URL_RE = re.compile(r"(://[^:\s]+:)[^@\s]+(@)")

_EXTRA_FIELDS = ("method", "path", "status_code", "duration_ms")


def _redact(text: str) -> str:
    return _SECRET_URL_RE.sub(r"\1***\2", text)


class RequestIdFilter(logging.Filter):
    """Gắn `request_id` vào mọi LogRecord, trừ khi caller đã tự gắn sẵn.

    Handler bắt lỗi tập trung (main.py) tự gắn `request_id` qua `extra=` vì
    nó chạy sau khi middleware đã reset contextvar — filter không được ghi
    đè giá trị đó.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Một dòng JSON mỗi bản ghi log."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact(record.getMessage()),
            "request_id": getattr(record, "request_id", "-"),
        }
        for field in _EXTRA_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exc_info"] = _redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


_configured = False


def configure_logging(level: str = "INFO") -> None:
    """Cấu hình logging một lần duy nhất, gọi ở src/main.py lúc app khởi động.

    Gọi lại lần nữa (module bị import lại) chỉ chỉnh level, không tạo thêm
    handler — tránh log trùng hoặc mất bản ghi do nhiều `basicConfig` chồng
    nhau.
    """
    global _configured
    root = logging.getLogger()
    if _configured:
        root.setLevel(level)
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    root.handlers = [handler]
    root.setLevel(level)
    _configured = True
