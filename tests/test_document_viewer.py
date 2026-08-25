"""Tests for document viewer with signed URLs (Task 7, Phase 2).

Tests:
- GET /documents/{document_id}/content returns signed URL
- Admin/manager can access BQL internal documents
- Resident cannot access BQL internal documents (403)
- Resident can access non-internal documents
- 404 for non-existent document
"""
from __future__ import annotations

import pytest

from src.models.db import Document

ADMIN = {"X-User-Id": "1"}
RESIDENT = {"X-User-Id": "2"}


def _create_doc(db_session, title: str, file_path: str):
    doc = Document(title=title, file_path=file_path, embed_status="ready")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc.document_id


# --- Happy paths ----------------------------------------------------------


@pytest.mark.asyncio
async def test_get_public_document_returns_signed_url(client, db_session, monkeypatch):
    """Cư dân nhận được signed URL cho tài liệu không phải internal."""
    from src.services import storage

    doc_id = _create_doc(db_session, "Quy dinh ve do cho", "data/kb/public/rules.pdf")

    # generate_signed_url is sync, not async
    def _fake_signed_url(bucket: str, path: str, expires_in: int = 900) -> str:
        return f"https://signed.example.com/{path}?expires={expires_in}"

    monkeypatch.setattr(storage, "generate_signed_url", _fake_signed_url)

    r = await client.get(f"/api/v1/documents/{doc_id}/content", headers=RESIDENT)
    assert r.status_code == 200
    data = r.json()
    assert data["document_id"] == doc_id
    assert data["title"] == "Quy dinh ve do cho"
    assert "signed_url" in data
    assert data["signed_url"].startswith("https://signed.example.com/")


@pytest.mark.asyncio
async def test_admin_can_access_internal_document(client, db_session, monkeypatch):
    """Admin nhận được signed URL cho tài liệu BQL internal."""
    from src.services import storage

    doc_id = _create_doc(db_session, "Quy trinh noi bo", "data/kb/bql/internal-proc.md")

    def _fake_signed_url(bucket: str, path: str, expires_in: int = 900) -> str:
        return f"https://signed.example.com/{path}"

    monkeypatch.setattr(storage, "generate_signed_url", _fake_signed_url)

    r = await client.get(f"/api/v1/documents/{doc_id}/content", headers=ADMIN)
    assert r.status_code == 200
    assert r.json()["signed_url"].startswith("https://signed.example.com/")


# --- Permission denied ----------------------------------------------------


@pytest.mark.asyncio
async def test_resident_cannot_access_internal_document(client, db_session):
    """Cư dân nhận 403 khi cố truy cập tài liệu internal của BQL."""
    doc_id = _create_doc(db_session, "Quy trinh noi bo", "data/kb/bql/internal-proc.md")

    r = await client.get(f"/api/v1/documents/{doc_id}/content", headers=RESIDENT)
    assert r.status_code == 403
    assert "Access denied" in r.json()["detail"]


# --- Not found -----------------------------------------------------------


@pytest.mark.asyncio
async def test_get_nonexistent_document_returns_404(client, db_session):
    """Document ID không tồn tại trả 404."""
    r = await client.get("/api/v1/documents/99999/content", headers=ADMIN)
    assert r.status_code == 404
