"""Chấm bộ câu hỏi trong `eval/questions.yaml` qua API thật.

Chạy:  python -m scripts.run_eval                      # API cục bộ
       python -m scripts.run_eval --api https://...    # bản deploy
       python -m scripts.run_eval --limit 10           # chạy thử ít câu

Đo TOÀN BỘ đường đi (retrieve → generate → guard) chứ không chỉ retrieval, vì
đó mới là thứ cư dân nhận được. Một câu retrieval đúng nhưng LLM trả lời lạc đề
vẫn là câu sai với người dùng.

Ba chỉ số:
  - **Đúng loại**: câu cần trả lời thì có trả lời, câu ngoài phạm vi thì từ chối.
  - **Đủ ý**: câu trả lời chứa từ khoá bắt buộc (`must_mention`).
  - **Có nguồn**: câu trả lời được kèm ít nhất một trích dẫn.

LƯU Ý CHI PHÍ: mỗi câu tốn một lần embed + một lần gọi LLM. Chạy cả bộ 35 câu
là 35 request embedding — đáng kể với hạn mức free tier của Google.
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

from src.config import get_settings

QUESTIONS = Path("eval/questions.yaml")
OUT_DIR = Path("eval/results")


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return stripped.replace("đ", "d")


def _access_token() -> str:
    """Đăng nhập một tài khoản demo để có Bearer token."""
    settings = get_settings()
    response = httpx.post(
        f"{settings.supabase_url}/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": settings.supabase_anon_key},
        json={"email": "tran.hong.tuan1@moveinmate.demo", "password": "MoveInMate!2026"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _grade(question: dict, payload: dict) -> dict:
    answer_source = payload.get("answer_source", "")
    answer = payload.get("answer", "")
    sources = payload.get("sources") or []

    refused = answer_source == "no_context"
    want_refuse = question["expect"] == "refuse"

    right_kind = refused if want_refuse else not refused
    missing = [
        kw for kw in question.get("must_mention", []) if _norm(kw) not in _norm(answer)
    ]
    # Câu từ chối thì KHÔNG được kèm nguồn — hiện trích dẫn dưới một câu
    # "tôi không biết" là kiểu hiển thị gây hiểu nhầm nhất.
    cited_ok = (not sources) if want_refuse else bool(sources)

    return {
        "id": question["id"],
        "procedure": question["procedure"],
        "expect": question["expect"],
        "answer_source": answer_source,
        "right_kind": right_kind,
        "missing_terms": missing,
        "cited_ok": cited_ok,
        "passed": right_kind and not missing and cited_ok,
        "sources": [s.get("title", "")[:60] for s in sources],
        "answer": answer[:300],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Chấm bộ câu hỏi đánh giá")
    parser.add_argument("--api", default="http://localhost:8000/api/v1")
    parser.add_argument("--limit", type=int, default=0, help="Chỉ chạy N câu đầu")
    args = parser.parse_args()

    questions = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    if args.limit:
        questions = questions[: args.limit]

    headers = {"Authorization": f"Bearer {_access_token()}"}
    results = []

    for question in questions:
        try:
            response = httpx.post(
                f"{args.api}/chat",
                headers=headers,
                json={"message": question["question"]},
                timeout=120,
            )
            payload = response.json() if response.status_code == 200 else {}
            if response.status_code != 200:
                payload = {"answer": f"HTTP {response.status_code}", "answer_source": "error"}
        except httpx.HTTPError as exc:
            payload = {"answer": f"loi mang: {exc}", "answer_source": "error"}

        row = _grade(question, payload)
        results.append(row)
        mark = "PASS" if row["passed"] else "FAIL"
        print(f"  {mark}  {row['id']}  [{row['answer_source']:10}] {question['question'][:52]}")
        if not row["passed"] and row["missing_terms"]:
            print(f"          thieu tu khoa: {row['missing_terms']}")

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    kind_ok = sum(1 for r in results if r["right_kind"])
    answerable = [r for r in results if r["expect"] == "answer"]
    refusals = [r for r in results if r["expect"] == "refuse"]

    print(f"\n{'='*54}")
    print(f"Tong the        : {passed}/{total} ({passed/total*100:.0f}%)")
    print(f"Dung loai        : {kind_ok}/{total} ({kind_ok/total*100:.0f}%)")
    print(f"  cau tra loi duoc: {sum(1 for r in answerable if r['right_kind'])}/{len(answerable)}")
    print(f"  cau phai tu choi: {sum(1 for r in refusals if r['right_kind'])}/{len(refusals)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    path = OUT_DIR / f"run-{stamp}.json"
    path.write_text(
        json.dumps(
            {
                "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "api": args.api,
                "total": total,
                "passed": passed,
                "right_kind": kind_ok,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nChi tiet: {path}")


if __name__ == "__main__":
    main()
