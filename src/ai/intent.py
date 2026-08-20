"""Detect procedure intent from user message — 3 layers: keyword exact, fuzzy, LLM fallback.

Used by AI form generation (task 3).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Literal, NamedTuple

from sqlalchemy.orm import Session

from src.models.db import ChecklistItem

# Stopwords — từ quá chung không phân biệt được thủ tục. "the" (thẻ),
# "xe", "ki", "lam" xuất hiện trong hầu hết task names, dùng chúng làm
# keyword sẽ gây false positive. "dang" (đăng) KHÔNG stopword vì nó phân biệt
# được "đăng ký" vs "làm" — hai hành động khác nhau trong cùng ngữ cảnh.
_STOPWORDS = frozenset([
    "cua", "va", "hoac", "voi", "cho", "nay", "kia", "cac",
    "la", "co", "khong", "duoc", "de", "ve", "qua", "tai",
    "tu", "trong", "nhung", "cac", "mot", "h nay", "h kia",
    "lam", "ki", "the", "xe", "nha", "phong", "be",
    "thang", "cu", "dan", "tru", "chinh", "giao",
])


class ProcedureMatch(NamedTuple):
    item: ChecklistItem | None
    confidence: Literal["high", "medium", "low"]
    ambiguous: bool = False
    disambiguation_options: list[ChecklistItem] = []


def _normalize(text: str) -> str:
    """Bo dau tieng Viet, chuyen thanh lowercase."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(
        c for c in decomposed
        if unicodedata.category(c) != "Mn"
    ).replace("đ", "d")


def _extract_keywords(text: str) -> list[str]:
    """Tach tu khoa 3+ ky tu (sau khi bo dau), loai bo stopwords."""
    norm = _normalize(text)
    words = re.findall(r"\b\w{3,}\b", norm)
    return [w for w in words if len(w) >= 3 and w not in _STOPWORDS]


def _task_name_contains(task_name: str, keyword: str) -> bool:
    """So khớp keyword trong task_name, Unicode-normalized de xu ly tieng Viet."""
    return keyword in _normalize(task_name)


def _has_form(item: ChecklistItem) -> bool:
    """True khi item co form_schema (khong None).

    Luc nay dien ra trong Python sau ORM hydration, dam bao hoat dong
    nhat ky tren moi dialect (vi du SQLite luu None cua JSON thanh chuoi
    'null' trong cot, khong phai SQL NULL).
    """
    return item.form_schema is not None


def detect_procedure_intent(message: str, db: Session) -> ProcedureMatch:
    """3 layers: keyword exact → fuzzy → LLM fallback."""
    norm = _normalize(message)
    keywords = _extract_keywords(message)

    # Lớp 1: Keyword exact — so sánh trong Python de dam bao Unicode normalization
    # chính xác. SQLite ILIKE khong nhan Unicode decomposition.
    all_items = db.query(ChecklistItem).all()
    form_items = [item for item in all_items if _has_form(item)]
    for kw in keywords:
        candidates = [item for item in form_items if _task_name_contains(item.task_name, kw)]
        if len(candidates) == 1:
            return ProcedureMatch(item=candidates[0], confidence="high")

    # Lớp 2: Fuzzy
    candidates = [
        item for item in form_items
        if _normalize(item.task_name) in norm
    ]
    if len(candidates) == 1:
        return ProcedureMatch(item=candidates[0], confidence="medium")
    if len(candidates) > 1:
        return ProcedureMatch(
            item=None, confidence="low",
            ambiguous=True,
            disambiguation_options=candidates
        )

    # Lớp 3: LLM fallback (hỏi resident chọn)
    return ProcedureMatch(
        item=None, confidence="low",
        ambiguous=True,
        disambiguation_options=form_items[:4]
    )
