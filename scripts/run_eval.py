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

Hai chỉ số (LLM judge, model KHÁC model sinh câu trả lời — xem `JUDGE_MODEL`):
  - **correctness**: LLM đánh giá câu trả lời có đúng sự thật không.
  - **citation**: LLM đánh giá nguồn trích dẫn có phù hợp không.

Câu FG01/FG02 (`expect: form_generation|disambiguation`) đi qua luồng AI dẫn
dắt điền hồ sơ, không qua RAG — chấm bằng `intent` + `expected_fields` thay vì
answer_source/sources, và KHÔNG tốn lượt LLM judge (không có nghĩa để đánh giá
"đúng sự thật" cho một câu hỏi làm rõ).

**Latency**: đo round-trip HTTP thật của mỗi câu (không tính `--delay` nghỉ
giữa các câu), báo p50/p95/trung bình, so với mục tiêu <3s.

LƯU Ý CHI PHÍ: mỗi câu tốn một lần embed + một lần gọi LLM. Chạy cả bộ (hiện
37 câu, 35 qua RAG) là ~35 request embedding — đáng kể với hạn mức free tier
của Google. LLM judge thêm ~35 request nữa (~$0.14 cho gpt-4o-mini).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
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

# Mục tiêu report.md đã khai từ 12/08 và luôn ghi "chưa đo" — dùng để in
# PASS/FAIL cạnh con số đo được, không chỉ trưng con số trần trụi.
LATENCY_TARGET_MS = 3000


def _percentile(sorted_values: list[float], pct: float) -> float | None:
    """Percentile kiểu nội suy tuyến tính (giống numpy mặc định).

    Tự viết thay vì kéo thêm numpy chỉ để tính một con số — script này vốn đã
    tối giản dependency (chỉ httpx + yaml + langchain-core).
    """
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * pct
    lo, hi = int(rank), min(int(rank) + 1, len(sorted_values) - 1)
    if lo == hi:
        return sorted_values[lo]
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (rank - lo)


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


# Model GIÁM KHẢO — cố ý KHÁC model sinh câu trả lời (gpt-4o-mini). Bản trước
# dùng chung `get_chat_llm()` cho cả hai việc: model tự chấm bài của chính nó
# (self-judge) thiên vị đúng lỗi của mình — một câu trả lời sai nhưng "nghe
# giống văn phong đúng" của gpt-4o-mini dễ được chính gpt-4o-mini cho điểm cao
# hơn một giám khảo độc lập sẽ cho. Đi qua OpenRouter với model khác hẳn nhà
# cung cấp, không phụ thuộc CHAT_PROVIDER của app — sinh câu trả lời và chấm
# bài giờ là hai đường hoàn toàn tách biệt.
JUDGE_MODEL = "anthropic/claude-sonnet-5"


def _get_judge_llm(
    model: str | None = None, max_tokens: int | None = None
) -> BaseChatModel:
    """Giám khảo độc lập qua OpenRouter — xem `JUDGE_MODEL` ở trên.

    `model` để `run_ragas.py` đổi sang giám khảo rẻ hơn khi cần: RAGAS gọi LLM
    nhiều lần cho mỗi câu nên tốn gấp bội `run_eval`. Đổi thì phải giữ nguyên
    ràng buộc gốc — giám khảo KHÁC model sinh câu trả lời (`gpt-4o-mini`).
    """
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    if not settings.open_router_api_key:
        raise RuntimeError(
            "Cần OPEN_ROUTER_API_KEY trong .env để chạy model giám khảo qua OpenRouter."
        )
    return ChatOpenAI(
        model=model or JUDGE_MODEL,
        api_key=settings.open_router_api_key,
        base_url=settings.openrouter_base_url,
        temperature=0,
        timeout=30,
        # `max_tokens` KHONG phai chi de cat bot dau ra. OpenRouter giu cho
        # credit theo dung con so nay truoc khi goi model: khong dat thi no
        # lay tran dau ra cua model (sonnet-5: 65_536 token) va tinh tien giu
        # cho theo tran do. So du con it hon muc giu cho la moi request bi tu
        # choi 402 "requested up to 65536 tokens, but can only afford ..." du
        # cau tra loi that chi dai vai tram token va tien du thua.
        max_tokens=max_tokens,
    )


def _fetch_full_context(query: str) -> str:
    """Truy xuất lại TOÀN BỘ chunk chưa gộp cho đúng câu hỏi này.

    Tái tạo chính xác ngữ cảnh `generate_node` đã dùng để viết câu trả lời,
    thay vì `sources[]` mà `/chat` trả về (đã gộp theo `document_id`, mỗi tài
    liệu chỉ giữ một đoạn trích 220 ký tự cho người dùng đọc — xem
    `_SNIPPET_LEN` ở `rag_retrieve.py`). Gọi thẳng `rag_retrieve_node`, không
    qua HTTP: Chroma tĩnh (KB không đổi giữa hai lần gọi cùng phiên chấm), câu
    hỏi ở đây không có lịch sử hội thoại nên `standalone_query == query` —
    kết quả giống hệt lần gọi thật trong `/chat`, không phải suy đoán.

    Tốn thêm một lượt gọi embedding mỗi câu — cộng dồn ngang với chi phí sinh
    câu trả lời ban đầu. Đổi lại giám khảo mới chấm công bằng, không phải vì
    số đẹp hơn.
    """
    import asyncio

    from src.agents.nodes.rag_retrieve import rag_retrieve_node

    try:
        result = asyncio.run(rag_retrieve_node({"query": query}))
    except Exception:  # noqa: BLE001
        return "(không truy xuất lại được để giám khảo xem — lỗi mạng/embedding)"

    chunks = result.get("retrieved") or []
    if not chunks:
        return "(không có tài liệu)"
    return "\n\n".join(f"[{c['title']}]\n{c['content']}" for c in chunks)


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
        # Vòng sửa 1 (đã làm): thay title bằng snippet — vẫn không đủ. `sources[]`
        # do `/chat` trả về đã GỘP theo document_id (mỗi tài liệu giữ đúng 1 đoạn
        # trích, cắt cứng 220 ký tự — `_SNIPPET_LEN` trong rag_retrieve.py, giới
        # hạn hiển thị cho NGƯỜI DÙNG, không phải giới hạn dữ liệu `generate` có).
        # `generate_node` thực tế dùng TOÀN BỘ chunk CHƯA gộp, đầy đủ nội dung.
        #
        # Giám khảo chấm "trích dẫn đúng không" mà chỉ thấy một phần nhỏ hơn hẳn
        # những gì AI thực sự dùng để trả lời — tất nhiên sẽ chấm SAI những câu
        # đúng nhưng viện tới phần nội dung nằm ngoài 220 ký tự đó. Sửa: gọi lại
        # thẳng `rag_retrieve_node` cho ĐÚNG câu hỏi này, lấy full context y hệt
        # generate đã thấy — không phải đoán hay nới lỏng tiêu chí chấm.
        sources_str = _fetch_full_context(question["question"])
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
        # Giám khảo qua OpenRouter (Claude Sonnet 5) hay bọc markdown quanh
        # dòng nhãn, kiểu "**1. correct: KHÔNG CHẮC CHẮN**" — khác hẳn phong
        # cách trả lời trần của gpt-4o-mini lúc còn tự chấm. `.strip("`\"'")`
        # cũ không đụng tới `*`/`_`/`#`, nên regex neo đầu dòng trượt luôn.
        line = line.strip()
        line = re.sub(r"^[#*_\s]+|[#*_\s]+$", "", line).strip("`\"'")
        low = line.lower()

        # 1. correct — bắt (.+) chứ không phải (\S+): "KHÔNG CHẮC CHẮN" là
        # nhãn BA từ, \S+ trước đây chỉ chụp được "không" rồi không khớp
        # `elif "không chắc" in val` — âm thầm luôn ra None cho đúng cái nhãn
        # dùng khi model không chắc, mù thông tin đúng lúc cần biết nhất.
        m = re.search(r"(?:^|\n)\s*1[.\):]*\s*correct[^:]*:\s*(.+)", low)
        if not m:
            m = re.search(r"correct[^:]*:\s*(.+)", low)
        if m:
            val = m.group(1).strip()
            if "đúng" in val:
                correctness = "ĐÚNG"
            elif "không chắc" in val:
                correctness = "KHÔNG CHẮC CHẮN"
            elif "sai" in val:
                correctness = "SAI"

        # 2. citation — cùng lý do, bắt trọn phần còn lại của dòng.
        #
        # Prompt chỉ cho 3 lựa chọn (ĐÚNG/SAI/KHÔNG ÁP DỤNG) nhưng giám khảo
        # cẩn trọng (đo được với Claude Sonnet 5 qua OpenRouter) tự thêm
        # "KHÔNG CHẮC CHẮN" khi không đủ căn cứ xác minh — chấp nhận thay vì
        # coi là lỗi parse, đó là phản hồi trung thực chứ không phải sai định
        # dạng. Không tính vào `llm_cite_count` (chỉ ĐÚNG/KHÔNG ÁP DỤNG được
        # tính đạt) — cùng logic thận trọng như "SAI".
        m = re.search(r"(?:^|\n)\s*2[.\):]*\s*citation[^:]*:\s*(.+)", low)
        if not m:
            m = re.search(r"citation[^:]*:\s*(.+)", low)
        if m:
            val = m.group(1).strip()
            if "đúng" in val:
                citation = "ĐÚNG"
            elif "không áp dụng" in val:
                citation = "KHÔNG ÁP DỤNG"
            elif "không chắc" in val:
                citation = "KHÔNG CHẮC CHẮN"
            elif "sai" in val:
                citation = "SAI"

    return {
        "llm_correct": correctness,
        "llm_citation": citation,
        "llm_judge_error": correctness is None,
    }


# Hai câu FG01/FG02 (thêm 20/08) khai `expect: form_generation|disambiguation`
# — không đi qua RAG nên "đúng loại" không thể xét bằng answer_source/sources
# như 35 câu còn lại. Thiếu nhánh riêng thì `_grade` áp nhầm luật của RAG lên
# hai câu này và LUÔN chấm sai, bất kể luồng điền hồ sơ có chạy đúng hay không
# — đúng dạng hỏng thầm lặng: script vẫn chạy, in ra FAIL, nhưng vì lý do sai.
_FORM_INTENTS = {"form_generation", "disambiguation"}


def _grade(question: dict, payload: dict) -> dict:
    expect = question["expect"]
    answer = payload.get("answer", "")
    answer_source = payload.get("answer_source", "")
    sources = payload.get("sources") or []
    intent = payload.get("intent", "qa")

    if expect in _FORM_INTENTS:
        # Luồng AI dẫn dắt điền hồ sơ trả `answer_source="no_context"` cho MỌI
        # lượt (không có nghĩa "từ chối" — chỉ là không truy xuất tài liệu, xem
        # src/api/routes.py). Đúng/sai ở đây chỉ tuỳ `intent`, không tuỳ
        # answer_source; và không có tài liệu để trích nên không xét `sources`.
        right_kind = intent == expect
        cited_ok = True  # không áp dụng cho luồng form
        missing = [
            f"{key}={value!r} (thực tế: {(payload.get('form_data') or {}).get(key)!r})"
            for key, value in question.get("expected_fields", {}).items()
            if (payload.get("form_data") or {}).get(key) != value
        ]
    else:
        refused = answer_source == "no_context"
        want_refuse = expect == "refuse"
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
        "expect": expect,
        "answer_source": answer_source,
        "intent": intent,
        "right_kind": right_kind,
        "missing_terms": missing,
        "cited_ok": cited_ok,
        "passed": right_kind and not missing and cited_ok,
        "sources": [s.get("title", "")[:60] for s in sources],
        "answer": answer[:300],
        # LLM judge fields — populated by _grade_llm() in main; luồng form
        # không nhận judge (xem vòng lặp trong main()), ở đây giữ None làm mặc
        # định cho nhất quán schema.
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
        # Đo đúng round-trip HTTP thật, không tính thời gian sleep giữa các
        # câu — đó là độ trễ cư dân thật sự chờ, thứ report.md khai "chưa đo"
        # từ 12/08 dù script đã gọi HTTP thật ngay từ đầu.
        started = time.perf_counter()
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
        latency_ms = (time.perf_counter() - started) * 1000

        row = _grade(question, payload)
        row["latency_ms"] = round(latency_ms, 1)
        results.append(row)
        payloads.append(payload)
        mark = "PASS" if row["passed"] else "FAIL"
        print(
            f"  {mark}  {row['id']}  [{row['answer_source']:10}] "
            f"{latency_ms:6.0f}ms  {question['question'][:44]}"
        )
        if not row["passed"] and row["missing_terms"]:
            print(f"          thieu: {row['missing_terms']}")
        if i > 0:
            time.sleep(args.delay)

    # ── LLM judge ─────────────────────────────────────────────────────────────
    print(f"\n{'='*54}")
    print("Danh gia LLM judge...")
    for question, row, payload in zip(questions, results, payloads):
        if question["expect"] in _FORM_INTENTS:
            # "Câu trả lời có đúng sự thật không" không có nghĩa cho một câu
            # hỏi làm rõ ("Bạn muốn thẻ cư dân chủ hộ hay người thuê?") — bỏ
            # qua để không tốn lượt gọi LLM vô nghĩa. `judged`/`cited_judged`
            # ở dưới đã tự loại các dòng `llm_correct is None`.
            print(f"  SKIP  {row['id']}  (luong form, khong can LLM judge)")
            continue
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

    # Latency — round-trip HTTP thật đã đo trong vòng lặp ở trên, không tính
    # thời gian `time.sleep(args.delay)` giữa các câu.
    latencies = sorted(r["latency_ms"] for r in results if r.get("latency_ms") is not None)
    p50 = _percentile(latencies, 0.50)
    p95 = _percentile(latencies, 0.95)
    avg_latency = statistics.mean(latencies) if latencies else None

    print(f"\n{'='*54}")
    print(f"Tong the         : {passed}/{total} ({passed/total*100:.0f}%)")
    print(f"Dung loai        : {kind_ok}/{total} ({kind_ok/total*100:.0f}%)")
    print(f"  cau tra loi duoc: {sum(1 for r in answerable if r['right_kind'])}/{len(answerable)}")
    print(f"  cau phai tu choi: {sum(1 for r in refusals if r['right_kind'])}/{len(refusals)}")
    print(f"\nLLM judge (n={len(judged)}, loi={judge_errors}):")
    print(f"  correctness     : {llm_correct_count}/{len(judged)} ({llm_correct_rate:.0f}%)")
    print(f"  citation        : {llm_cite_count}/{len(cited_judged)} ({llm_cite_rate:.0f}%)")
    if latencies:
        target_mark = "OK" if p95 is not None and p95 < LATENCY_TARGET_MS else "CHUA DAT"
        print(f"\nLatency (n={len(latencies)}, muc tieu <{LATENCY_TARGET_MS/1000:.0f}s):")
        print(f"  p50             : {p50:.0f}ms")
        print(f"  p95             : {p95:.0f}ms  [{target_mark}]")
        print(f"  trung binh      : {avg_latency:.0f}ms")
        print(f"  min / max       : {latencies[0]:.0f}ms / {latencies[-1]:.0f}ms")

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
                "judge_model": JUDGE_MODEL,
                "total": total,
                "passed": passed,
                "right_kind": kind_ok,
                "llm_correct_count": llm_correct_count,
                "llm_correct_rate": round(llm_correct_rate, 1),
                "llm_cite_count": llm_cite_count,
                "llm_cite_rate": round(llm_cite_rate, 1),
                "llm_judge_errors": judge_errors,
                "latency_ms": {
                    "p50": round(p50, 1) if p50 is not None else None,
                    "p95": round(p95, 1) if p95 is not None else None,
                    "avg": round(avg_latency, 1) if avg_latency is not None else None,
                    "min": latencies[0] if latencies else None,
                    "max": latencies[-1] if latencies else None,
                    "target_ms": LATENCY_TARGET_MS,
                    "meets_target": (p95 < LATENCY_TARGET_MS) if p95 is not None else None,
                },
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
                "judge_model": JUDGE_MODEL,
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
                "latency_ms": {
                    "p50": round(p50, 1) if p50 is not None else None,
                    "p95": round(p95, 1) if p95 is not None else None,
                    "avg": round(avg_latency, 1) if avg_latency is not None else None,
                    "target_ms": LATENCY_TARGET_MS,
                    "meets_target": (p95 < LATENCY_TARGET_MS) if p95 is not None else None,
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
