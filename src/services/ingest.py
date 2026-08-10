"""Nạp tài liệu KB (`data/kb/**/*.md`) vào Chroma.

Tách khỏi bước LẤY dữ liệu (`scripts/scrape_kb.py`, `scripts/fetch_legal_kb.py`)
như đã ghi chú sẵn ở hai script đó. Mỗi file `.md` có frontmatter YAML
(title, source_type, ...) do các script trên sinh ra.

Chạy lại được nhiều lần: mỗi file ánh xạ tới đúng một dòng `DOCUMENTS`
(khoá theo `file_path`), và chunk cũ của document đó bị xoá khỏi Chroma
trước khi ghi chunk mới — tránh sót chunk cũ khi nội dung file đổi.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from itertools import islice
from pathlib import Path

import yaml
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from sqlalchemy.orm import Session

from src.models.db import Document
from src.services.vectorstore import get_vectorstore

KB_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "kb"
REPO_ROOT = KB_DIR.parent.parent

# Khớp DocSourceType trong src/models/schemas.py — sai giá trị dừng ngay lúc
# ingest thay vì âm thầm trích nguồn sai loại lúc trả lời.
VALID_SOURCE_TYPES = {"bql_internal", "public_regulation", "unofficial_web"}

_HEADERS_TO_SPLIT = [("#", "h1"), ("##", "h2"), ("###", "h3"), ("####", "h4")]
_CHUNK_TOKENS = 500
_CHUNK_OVERLAP = 50

# Google AI Studio free-tier giới hạn ~100 đơn vị embedding/phút, tính theo
# SỐ ĐOẠN VĂN BẢN gửi lên chứ không phải số lệnh gọi API (một file dài như
# Thông tư 05/2024 tự nó đủ 175 chunk để vượt ngưỡng trong một lượt gọi). Chia
# nhỏ batch + nghỉ giữa các batch + thử lại có backoff khi dính 429 (đo thực
# tế 10/08: 20 chunk / 8s tương đương 150 chunk/phút vẫn bị 429 — hạ xuống 15
# chunk / 12s ≈ 75 chunk/phút để có biên an toàn).
_EMBED_BATCH_SIZE = 15
_EMBED_BATCH_DELAY_SECONDS = 12.0
_EMBED_MAX_RETRIES = 5
_EMBED_RETRY_BASE_SECONDS = 20.0

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n\n(.*)$", re.DOTALL)


@dataclass
class ParsedDoc:
    title: str
    source_type: str
    body: str


class IngestError(ValueError):
    """Frontmatter thiếu hoặc sai — lỗi dữ liệu KB, dừng ngay để người nạp sửa."""


def _parse_frontmatter(text: str, path: Path) -> ParsedDoc:
    match = _FRONTMATTER.match(text)
    if not match:
        raise IngestError(f"{path}: thiếu frontmatter YAML hợp lệ (--- ... ---)")

    meta = yaml.safe_load(match.group(1)) or {}
    title = meta.get("title")
    source_type = meta.get("source_type")

    if not title:
        raise IngestError(f"{path}: frontmatter thiếu 'title'")
    if source_type not in VALID_SOURCE_TYPES:
        raise IngestError(
            f"{path}: source_type '{source_type}' không hợp lệ, "
            f"phải là một trong {sorted(VALID_SOURCE_TYPES)}"
        )
    return ParsedDoc(title=title, source_type=source_type, body=match.group(2))


def _batched(items: list[LCDocument], size: int) -> list[list[LCDocument]]:
    it = iter(items)
    return list(iter(lambda: list(islice(it, size)), []))


def _add_documents_with_backoff(store: object, docs: list[LCDocument]) -> None:
    """Ghi `docs` theo batch nhỏ, thử lại có backoff khi bị rate-limit (429)."""
    for batch in _batched(docs, _EMBED_BATCH_SIZE):
        for attempt in range(1, _EMBED_MAX_RETRIES + 1):
            try:
                store.add_documents(batch)
                break
            except Exception as exc:
                if attempt == _EMBED_MAX_RETRIES:
                    raise
                wait = _EMBED_RETRY_BASE_SECONDS * attempt
                print(
                    f"    lỗi tạm thời khi embed ({type(exc).__name__}), "
                    f"thử lại sau {wait:.0f}s (lần {attempt}/{_EMBED_MAX_RETRIES})..."
                )
                time.sleep(wait)
        time.sleep(_EMBED_BATCH_DELAY_SECONDS)


def _get_or_create_document(db: Session, file_path: str, title: str) -> int:
    existing = db.query(Document).filter(Document.file_path == file_path).one_or_none()
    if existing is not None:
        existing.title = title
        db.commit()
        return existing.document_id

    doc = Document(title=title, file_path=file_path)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc.document_id


def _chunk(body: str) -> list[str]:
    """Cắt theo tiêu đề Markdown trước; đoạn nào còn dài thì cắt tiếp theo token.

    Chiến lược theo docs/architecture_diagram.md mục 3.5: ưu tiên ranh giới
    mục/tiêu đề, fallback ~500 token / overlap 50 khi tài liệu không có cấu
    trúc rõ (hoặc một mục vẫn dài hơn 500 token).
    """
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=_HEADERS_TO_SPLIT, strip_headers=False
    )
    sections = header_splitter.split_text(body)

    token_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=_CHUNK_TOKENS,
        chunk_overlap=_CHUNK_OVERLAP,
    )

    chunks: list[str] = []
    for section in sections:
        chunks.extend(token_splitter.split_text(section.page_content))
    return [c.strip() for c in chunks if c.strip()]


def ingest_file(db: Session, path: Path) -> int:
    """Nạp một file `.md`. Trả về số chunk đã ghi (0 nếu file rỗng sau khi cắt)."""
    parsed = _parse_frontmatter(path.read_text(encoding="utf-8"), path)
    relative = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    document_id = _get_or_create_document(db, relative, parsed.title)

    store = get_vectorstore()
    store.delete(where={"document_id": document_id})

    chunks = _chunk(parsed.body)
    if not chunks:
        return 0

    docs = [
        LCDocument(
            page_content=chunk,
            metadata={
                "document_id": document_id,
                "title": parsed.title,
                "source_type": parsed.source_type,
            },
        )
        for chunk in chunks
    ]
    _add_documents_with_backoff(store, docs)
    return len(docs)


def ingest_all(db: Session) -> list[tuple[str, int]]:
    """Nạp mọi file `.md` trong `data/kb/` (đệ quy). Trả về (tên file, số chunk)."""
    return [(path.name, ingest_file(db, path)) for path in sorted(KB_DIR.rglob("*.md"))]
