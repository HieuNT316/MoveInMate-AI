"""Supabase Storage cho ảnh minh chứng hồ sơ (US-13).

Vì sao không lưu thẳng vào Postgres hay đĩa của Railway: đĩa container là tạm,
mất sau mỗi lần deploy; nhét ảnh vào DB thì phình bảng và mọi truy vấn hồ sơ
phải kéo theo binary. Supabase đã có sẵn trong dự án, không thêm nhà cung cấp.

**Bucket PRIVATE, không có ngoại lệ.** Đây là ảnh CCCD, VNeID, đơn đăng ký tạm
trú — giấy tờ tuỳ thân. Bucket public nghĩa là ai đoán đúng đường dẫn cũng xem
được. Đọc chỉ qua signed URL hết hạn ngắn do backend ký sau khi đã kiểm quyền.

Cùng lý do đó, ảnh **không bao giờ** được embed vào Chroma (quy tắc kiến trúc ở
architecture_diagram.md): vector store không phân quyền theo người dùng, đã
index là bất kỳ ai hỏi đúng câu đều truy xuất được.
"""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath

import httpx

from src.config import get_settings

# Chỉ nhận ảnh và PDF. Danh sách ĐÓNG, không đoán theo đuôi file: cư dân nộp
# minh chứng thì ba định dạng này là đủ, mở rộng thêm chỉ tăng bề mặt tấn công.
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "application/pdf": ".pdf",
}


class StorageError(RuntimeError):
    """Supabase Storage từ chối hoặc không gọi tới được."""


def _config() -> tuple[str, dict[str, str], str]:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        raise StorageError("Chưa cấu hình SUPABASE_URL / SUPABASE_SERVICE_KEY")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }
    return f"{settings.supabase_url}/storage/v1", headers, settings.supabase_storage_bucket


def ensure_bucket() -> None:
    """Tạo bucket private nếu chưa có. Gọi được nhiều lần, đã có thì bỏ qua."""
    base, headers, bucket = _config()
    try:
        existing = httpx.get(f"{base}/bucket/{bucket}", headers=headers, timeout=30)
        if existing.status_code == 200:
            return
        created = httpx.post(
            f"{base}/bucket",
            headers=headers,
            json={"id": bucket, "name": bucket, "public": False},
            timeout=30,
        )
    except httpx.HTTPError as exc:
        raise StorageError(f"Không gọi được Supabase Storage: {exc}") from exc

    # 409 = người khác vừa tạo xong, cũng coi là thành công.
    if created.status_code >= 400 and created.status_code != 409:
        raise StorageError(f"Không tạo được bucket: {created.text[:200]}")


def build_object_path(application_id: int, content_type: str) -> str:
    """Đường dẫn lưu trữ — KHÔNG dùng tên file người dùng gửi lên.

    Tên gốc chỉ được giữ trong DB để hiển thị. Dùng nó làm đường dẫn thật là
    mở đường cho path traversal ("../") và cho việc đoán tên file của người khác.
    """
    suffix = ALLOWED_CONTENT_TYPES[content_type]
    return f"{application_id}/{uuid.uuid4().hex}{suffix}"


def upload(path: str, data: bytes, content_type: str) -> None:
    base, headers, bucket = _config()
    try:
        response = httpx.post(
            f"{base}/object/{bucket}/{path}",
            headers={**headers, "Content-Type": content_type},
            content=data,
            timeout=60,
        )
    except httpx.HTTPError as exc:
        raise StorageError(f"Không tải được tệp lên: {exc}") from exc

    if response.status_code >= 400:
        raise StorageError(f"Supabase từ chối tệp: {response.text[:200]}")


def signed_url(path: str) -> str | None:
    """URL đọc tạm thời. Trả None nếu ký hỏng — thiếu một ảnh còn hơn vỡ cả trang."""
    base, headers, bucket = _config()
    settings = get_settings()
    try:
        response = httpx.post(
            f"{base}/object/sign/{bucket}/{path}",
            headers=headers,
            json={"expiresIn": settings.attachment_url_ttl_seconds},
            timeout=30,
        )
        if response.status_code >= 400:
            return None
        # Supabase trả đường dẫn tương đối dạng "/object/sign/<bucket>/...".
        relative = response.json()["signedURL"]
        return f"{base}{relative}" if relative.startswith("/") else relative
    except (httpx.HTTPError, KeyError, ValueError):
        return None


def display_name(filename: str | None) -> str:
    """Tên hiển thị đã làm sạch — bỏ mọi thành phần đường dẫn client gửi kèm."""
    if not filename:
        return "tệp đính kèm"
    return PurePosixPath(filename.replace("\\", "/")).name[:255] or "tệp đính kèm"
