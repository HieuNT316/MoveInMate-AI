"""Chấm bộ câu hỏi trong `eval/questions.yaml` qua API thật.

Chạy:  python -m scripts.run_eval                      # API cục bộ
       python -m scripts.run_eval --api https://...    # bản deploy
       python -m scripts.run_eval --limit 10           # chạy thử ít câu

Đo TOÀN BỘ đường đi (retrieve → generate → guard) chứ không chỉ retrieval, vì
đó mới là thứ cư dân nhận được. Một câu retrieval đúng nhưng LLM trả lời lạc đề
vẫn là câu sai với người dùng.

Ba chỉ số (keyword):
  - **Đúng loại**: câu cần trả lời thì có trả lời, câu ngoài phạm vi thì từ chối.
  - **Đủ ý**: câu trả lời chứa từ khoá bắt buộc (`must_mention`).
  - **Có nguồn**: câu trả lời được kèm ít nhất một trích dẫn.

Hai chỉ số (LLM judge):
  - **correctness**: LLM đánh giá câu trả lời có đúng sự thật không.
  - **citation**: LLM đánh giá nguồn trích dẫn có phù hợp không.

LƯU Ý CHI PHÍ: mỗi câu tốn một lần embed + một lần gọi LLM. Chạy cả bộ 35 câu
là 35 request embedding — đáng kể với hạn mức free tier của Google.
LLM judge thêm 35 request nữa (~$0.14 cho gpt-4o-mini).
"""

from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml
from langchain_core.language_models import BaseChatModel

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


def _get_judge_llm() -> BaseChatModel:
    """Trả về ChatOpenLM mà app đang dùng (đọc từ get_settings())."""
    from src.services.llm import get_chat_llm  # noqa: F401

    return get_chat_llm()


def _grade_llm(
    question: dict,
    row: dict,
    payload: dict,
) -> dict:
    """Đánh giá câu trả lời bằng LLM (judge).

    Luồng:
      1. Gọi LLM với prompt đánh giá (15s timeout).
      2. Parse output tìm token ĐÚNG / SAI / KHÔNG CHẮC CHẮN / KHÔNG ÁP DỤNG.
      3. Nếu gọi hoặc parse thất bại: fallback về keyword-only cho câu đó.
    """
    answer = row.get("answer", "")
    # payload["sources"] là list[dict]; row["sources"] đã bị stringify trong _grade().
    sources: list[dict] = payload.get("sources") or []

    if sources:
        sources_str = "\n".join(
            f"- {s.get('title', s.get('content', ''))[:120]}"
            for s in sources
        )
    else:
        sources_str = "(không có trích dẫn)"

    prompt = (
        "Bạn là một chuyên gia đánh giá câu trả lời của trợ lý AI cho hệ thống "
        "hỏi đáp thủ tục hành chính chung cư.\n\n"
        f"Câu hỏi: {question['question']}\n"
        f"Câu trả lời: {answer}\n"
        f"Nguồn được trích dẫn: {sources_str}\n\n"
        "Đánh giá:\n"
        "1. correct: [ĐÚNG / SAI / KHÔNG CHẮC CHẮN]\n"
        "2. citation: [ĐÚNG / SAI / KHÔNG ÁP DỤNG]\n"
    )

    try:
        llm = _get_judge_llm()
        msg = llm.invoke(prompt)
        raw_text = msg.content if hasattr(msg, "content") else str(msg)
    except Exception:  # noqa: BLE001
        return {"llm_correct": None, "llm_citation": None, "llm_judge_error": True}

    correctness: str | None = None
    citation: str | None = None

    for line in raw_text.splitlines():
        line = line.strip().strip("`\"'")
        low = line.lower()

        # 1. correct
        m = re.search(r"(?:^|\n)\s*1[.\):]*\s*correct[^:]*:\s*(\S+)", low)
        if not m:
            m = re.search(r"correct[^:]*:\s*(\S+)", low)
        if m:
            val = m.group(1).strip()
            if "đúng" in val:
                correctness = "ĐÚNG"
            elif "sai" in val:
                correctness = "SAI"
            elif "không chắc" in val:
                correctness = "KHÔNG CHẮC CHẮN"

        # 2. citation
        m = re.search(r"(?:^|\n)\s*2[.\):]*\s*citation[^:]*:\s*(\S+)", low)
        if not m:
            m = re.search(r"citation[^:]*:\s*(\S+)", low)
        if m:
            val = m.group(1).strip()
            if "đúng" in val:
                citation = "ĐÚNG"
            elif "không áp dụng" in val:
                citation = "KHÔNG ÁP DỤNG"
            elif "sai" in val:
                citation = "SAI"

    return {
        "llm_correct": correctness,
        "llm_citation": citation,
        "llm_judge_error": correctness is None,
    }


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
        # LLM judge fields — populated by _grade_llm() in main
        "llm_correct": None,
        "llm_citation": None,
        "llm_judge_error": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Chấm bộ câu hỏi đánh giá")
    parser.add_argument("--api", default="http://localhost:8000/api/v1")
    parser.add_argument("--limit", type=int, default=0, help="Chỉ chạy N câu đầu")
    parser.add_argument("--delay", type=float, default=7.0,
        help="Giây nghỉ giữa mỗi câu hỏi (tránh rate limit, mặc định 7)")
    args = parser.parse_args()

    questions = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    if args.limit:
        questions = questions[: args.limit]

    headers = {"Authorization": f"Bearer {_access_token()}"}
    results = []
    payloads: list[dict] = []

    # ── Gọi API để lấy câu trả lời ────────────────────────────────────────
    for i, question in enumerate(questions):
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
        payloads.append(payload)
        mark = "PASS" if row["passed"] else "FAIL"
        print(f"  {mark}  {row['id']}  [{row['answer_source']:10}] {question['question'][:52]}")
        if not row["passed"] and row["missing_terms"]:
            print(f"          thieu tu khoa: {row['missing_terms']}")
        if i > 0:
            time.sleep(args.delay)

    # ── LLM judge ─────────────────────────────────────────────────────────────
    print(f"\n{'='*54}")
    print("Danh gia LLM judge...")
    for question, row, payload in zip(questions, results, payloads):
        judge = _grade_llm(question, row, payload)

        row.update(judge)
        correct_label = judge.get("llm_correct") or "??"
        cite_label = judge.get("llm_citation") or "??"
        print(
            f"  LLM   {row['id']}  correct={correct_label:18} citation={cite_label}"
        )

    # ── Tổng hợp ─────────────────────────────────────────────────────────────
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    kind_ok = sum(1 for r in results if r["right_kind"])
    answerable = [r for r in results if r["expect"] == "answer"]
    refusals = [r for r in results if r["expect"] == "refuse"]

    # LLM judge correctness
    judged = [r for r in results if r.get("llm_correct") is not None]
    llm_correct_count = sum(1 for r in judged if r["llm_correct"] == "ĐÚNG")
    llm_correct_rate = llm_correct_count / len(judged) * 100 if judged else 0

    # LLM judge citation (chỉ cho câu trả lời, không phải refuse)
    answer_rows = [r for r in results if r["expect"] == "answer"]
    cited_judged = [r for r in answer_rows if r.get("llm_citation") is not None]
    llm_cite_count = sum(
        1 for r in cited_judged if r["llm_citation"] in ("ĐÚNG", "KHÔNG ÁP DỤNG")
    )
    llm_cite_rate = llm_cite_count / len(cited_judged) * 100 if cited_judged else 0

    judge_errors = sum(1 for r in results if r.get("llm_judge_error"))

    print(f"\n{'='*54}")
    print(f"Tong the         : {passed}/{total} ({passed/total*100:.0f}%)")
    print(f"Dung loai        : {kind_ok}/{total} ({kind_ok/total*100:.0f}%)")
    print(f"  cau tra loi duoc: {sum(1 for r in answerable if r['right_kind'])}/{len(answerable)}")
    print(f"  cau phai tu choi: {sum(1 for r in refusals if r['right_kind'])}/{len(refusals)}")
    print(f"\nLLM judge (n={len(judged)}, loi={judge_errors}):")
    print(f"  correctness     : {llm_correct_count}/{len(judged)} ({llm_correct_rate:.0f}%)")
    print(f"  citation        : {llm_cite_count}/{len(cited_judged)} ({llm_cite_rate:.0f}%)")

    # ── Regression check ───────────────────────────────────────────────────────
    _regression_check(llm_correct_rate, passed / total * 100)

    # ── Lưu kết quả ────────────────────────────────────────────────────────────
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
                "llm_correct_count": llm_correct_count,
                "llm_correct_rate": round(llm_correct_rate, 1),
                "llm_cite_count": llm_cite_count,
                "llm_cite_rate": round(llm_cite_rate, 1),
                "llm_judge_errors": judge_errors,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Lưu metrics riêng
    metrics_path = OUT_DIR / f"run-{stamp}-metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "api": args.api,
                "keyword": {
                    "total": total,
                    "passed": passed,
                    "pass_rate": round(passed / total * 100, 1),
                    "right_kind": kind_ok,
                },
                "llm_judge": {
                    "correct_count": llm_correct_count,
                    "correct_rate": round(llm_correct_rate, 1),
                    "cite_count": llm_cite_count,
                    "cite_rate": round(llm_cite_rate, 1),
                    "judge_errors": judge_errors,
                    "judged_total": len(judged),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nChi tiet: {path}")
    print(f"Metrics : {metrics_path}")


def _regression_check(current_llm_rate: float, current_kw_rate: float) -> None:
    """So sánh kết quả với lần chạy mới nhất trong eval/results/.

    Nếu LLM correctness giảm >= 5 điểm phần trăm so với lần chạy trước: in
    cảnh báo.
    """
    result_files = sorted(OUT_DIR.glob("run-*.json"))
    # Lọc bỏ metrics file (tên dạng run-YYYYMMDD-HHMM-metrics.json)
    result_files = [f for f in result_files if "-metrics" not in f.name]
    if not result_files:
        return

    latest = result_files[-1]
    try:
        prev = json.loads(latest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    prev_llm_rate = prev.get("llm_correct_rate")
    prev_passed = prev.get("passed")
    prev_total = prev.get("total")
    prev_kw_rate = prev_passed / prev_total * 100 if prev_passed and prev_total else None

    if prev_llm_rate is not None:
        diff = current_llm_rate - prev_llm_rate
        if diff < -5:
            print(
                f"\nWARNING  REGRESSION: LLM accuracy dropped {abs(diff):.0f}% "
                f"({prev_llm_rate:.0f}% -> {current_llm_rate:.0f}%) "
                f"vs {latest.name}"
            )
        elif diff < 0:
            print(
                f"\nINFO     LLM accuracy down {abs(diff):.0f}% "
                f"({prev_llm_rate:.0f}% -> {current_llm_rate:.0f}%) "
                f"vs {latest.name} — within threshold"
            )

    # Keyword regression
    if prev_kw_rate is not None:
        kw_diff = current_kw_rate - prev_kw_rate
        if kw_diff < -5:
            print(
                f"\nWARNING  REGRESSION: Keyword pass rate dropped {abs(kw_diff):.0f}% "
                f"({prev_kw_rate:.0f}% -> {current_kw_rate:.0f}%) "
                f"vs {latest.name}"
            )
        elif kw_diff < 0:
            print(
                f"\nINFO     Keyword pass rate down {abs(kw_diff):.0f}% "
                f"({prev_kw_rate:.0f}% -> {current_kw_rate:.0f}%) "
                f"vs {latest.name} — within threshold"
            )


if __name__ == "__main__":
    main()
