"""Đánh giá RAG bằng RAGAS — bộ chỉ số chuẩn ngành, chạy song song `run_eval.py`.

Chạy:  python -m scripts.run_ragas                   # API cục bộ
       python -m scripts.run_ragas --api https://... # bản deploy
       python -m scripts.run_ragas --limit 3         # chạy thử ít câu

**Khác gì `run_eval.py`?** `run_eval` chấm bằng từ khoá (`must_mention`) và một
LLM giám khảo tự viết prompt. RAGAS phân rã câu trả lời thành từng mệnh đề rồi
kiểm từng mệnh đề một, theo cách đã được công bố và dùng chung trong ngành —
nên số so sánh được với dự án khác, còn `run_eval` thì không.

**Chỉ chấm 28 câu `expect: answer`.** Bảy câu `expect: refuse` bị loại có chủ
đích: hệ thống từ chối thì `contexts` rỗng, mà cả ba chỉ số dưới đây đều đo
quan hệ giữa câu trả lời và ngữ cảnh truy xuất — không có ngữ cảnh thì không có
gì để đo. Chất lượng từ chối vẫn được `run_eval.py` chấm riêng (7/7 ở lần đo
gần nhất). Hai câu FG (luồng điền hồ sơ) cũng không đi qua RAG nên loại luôn.

**Ba chỉ số, đều KHÔNG cần đáp án mẫu:**

| Chỉ số | Hỏi gì | Cần embedding? |
|---|---|---|
| `faithfulness` | Từng ý trong câu trả lời có nằm trong tài liệu truy xuất không (chống bịa) | không |
| `answer_relevancy` | Câu trả lời có đúng trọng tâm câu hỏi không, hay lạc đề/lan man | **có** |
| `context_precision` | Đoạn tài liệu lấy về có thật sự dùng được không, hay lẫn rác | không |

Cố ý **không** chạy `context_recall` và `answer_correctness`: hai chỉ số đó cần
`ground_truth` — câu trả lời mẫu do người viết cho từng câu hỏi. `questions.yaml`
hiện chỉ có `must_mention` (từ khoá bắt buộc), **không phải** đáp án mẫu. Bịa ra
đáp án mẫu chỉ để chạy được thêm hai chỉ số thì con số ra sẽ đo chính cái mình
vừa bịa, không đo hệ thống.

**Giám khảo là Claude Sonnet 5 qua OpenRouter**, không phải gpt-4o-mini đang
sinh câu trả lời — cùng lý do đã áp cho `run_eval.py`: model tự chấm bài mình
thì thiên vị đúng lỗi của mình.

LƯU Ý CHI PHÍ: RAGAS gọi LLM nhiều lần cho MỖI câu (tách mệnh đề, rồi kiểm từng
mệnh đề, rồi chấm từng đoạn ngữ cảnh) — nặng hơn `run_eval` đáng kể. Cộng thêm
1 lượt embedding truy xuất lại ngữ cảnh + vài lượt cho `answer_relevancy`. Hạn
mức embedding Google là 1000/ngày tính theo project và dùng chung cả nhóm.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from scripts.run_eval import JUDGE_MODEL, _access_token, _get_judge_llm
from src.config import get_settings

QUESTIONS = Path("eval/questions.yaml")
OUT_DIR = Path("eval/results")


def _fetch_contexts(query: str) -> list[str]:
    """Ngữ cảnh RAG thật cho câu hỏi này, dạng danh sách chunk rời.

    RAGAS cần `retrieved_contexts` là list[str] để chấm từng đoạn một —
    `run_eval._fetch_full_context` nối sẵn thành một chuỗi nên không dùng lại
    được ở đây, dù cùng nguồn dữ liệu.

    Gọi thẳng `rag_retrieve_node`, không qua HTTP: `/chat` chỉ trả `sources[]`
    đã gộp theo `document_id` và cắt còn 220 ký tự mỗi tài liệu (giới hạn hiển
    thị cho người dùng). Chấm `faithfulness` trên bản cắt đó sẽ phạt oan mọi
    câu trả lời viện tới phần nội dung nằm ngoài 220 ký tự.
    """
    from src.agents.nodes.rag_retrieve import rag_retrieve_node

    try:
        result = asyncio.run(rag_retrieve_node({"query": query}))
    except Exception as exc:  # noqa: BLE001
        print(f"    LOI truy xuat: {exc}")
        return []

    return [c["content"] for c in (result.get("retrieved") or [])]


def _ask(
    api: str, headers: dict[str, str], question: str, *, retries: int = 4
) -> dict[str, Any]:
    """Hỏi `/chat` thật — đo đúng thứ cư dân nhận được, không mô phỏng.

    Thử lại có giãn cách khi gặp 429/503. Lần chạy 05/09 mất 8/28 câu vì
    OpenRouter trả 429 theo cụm (Q11-Q14, Q25-Q28): không phải hệ thống trả lời
    sai, chỉ là chạm hạn mức tần suất. Bỏ hẳn những câu đó làm mẫu teo còn 20 và
    lệch theo đúng vị trí câu hỏi trong file — chỉ số ra vẫn "sạch" về mặt NaN
    nhưng không còn đại diện cho cả bộ. Chờ rồi hỏi lại thì đúng hơn là loại.
    """
    delay = 5.0
    for attempt in range(retries):
        try:
            response = httpx.post(
                f"{api}/chat",
                headers=headers,
                json={"message": question},
                timeout=120,
            )
            if response.status_code == 200:
                return response.json()
            if response.status_code in (429, 503) and attempt < retries - 1:
                print(f"       HTTP {response.status_code}, cho {delay:.0f}s roi hoi lai")
                time.sleep(delay)
                delay *= 2
                continue
            return {"answer": f"HTTP {response.status_code}", "answer_source": "error"}
        except httpx.HTTPError as exc:
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return {"answer": f"loi mang: {exc}", "answer_source": "error"}
    return {"answer": "het luot thu lai", "answer_source": "error"}


def _build_metrics(llm: Any, embeddings: Any) -> list[Any]:
    """Ba chỉ số không cần đáp án mẫu.

    Tên lớp đổi giữa các bản RAGAS (`answer_relevancy` → `ResponseRelevancy`,
    `LLMContextPrecisionWithoutReference` chỉ có từ 0.2). Thử lần lượt thay vì
    ghim một bản: script này không nên hỏng chỉ vì nhóm nâng cấp thư viện.
    """
    from ragas.metrics import Faithfulness

    metrics: list[Any] = [Faithfulness(llm=llm)]

    try:
        from ragas.metrics import ResponseRelevancy

        metrics.append(ResponseRelevancy(llm=llm, embeddings=embeddings))
    except ImportError:
        from ragas.metrics import AnswerRelevancy

        metrics.append(AnswerRelevancy(llm=llm, embeddings=embeddings))

    try:
        from ragas.metrics import LLMContextPrecisionWithoutReference

        metrics.append(LLMContextPrecisionWithoutReference(llm=llm))
    except ImportError:
        print("  (ban RAGAS nay khong co context_precision khong-can-reference, bo qua)")

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Chấm bộ câu hỏi bằng RAGAS")
    parser.add_argument("--api", default="http://localhost:8000/api/v1")
    parser.add_argument("--limit", type=int, default=0, help="Chỉ chạy N câu đầu")
    parser.add_argument(
        "--samples-in", default="",
        help="Dung lai file mau da thu thap (bo qua toan bo buoc goi /chat). "
             "Moi lan hoi lai 28 cau ton ~56 luot embedding Google, ma han "
             "muc la 1000/ngay tinh theo project va dung chung ca nhom - "
             "cham lai bang mau cu thi khong ton luot nao.",
    )
    parser.add_argument(
        "--judge", default=JUDGE_MODEL,
        help=f"Model giam khao qua OpenRouter (mac dinh {JUDGE_MODEL}, giong "
             "run_eval.py). Doi duoc vi RAGAS goi LLM gap nhieu lan run_eval "
             "cho moi cau; bat buoc van phai khac model sinh cau tra loi.",
    )
    parser.add_argument(
        "--pause", type=float, default=2.0,
        help="Giãn cách giữa hai câu hỏi, giây (tránh chạm hạn mức tần suất "
             "của OpenRouter ngay từ đầu thay vì phải thử lại)",
    )
    parser.add_argument(
        "--workers", type=int, default=3,
        help="Số phép chấm chạy song song (mặc định RAGAS là 16 — quá cao, "
             "vượt hạn mức đồng thời của OpenRouter và làm hỏng phép đo)",
    )
    args = parser.parse_args()

    from ragas import EvaluationDataset, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.run_config import RunConfig

    from src.services.llm import get_embeddings

    questions = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    # Chỉ câu hỏi đi qua RAG — xem docstring đầu file để biết vì sao loại
    # `refuse` và hai câu FG.
    answerable = [q for q in questions if q["expect"] == "answer"]
    if args.limit:
        answerable = answerable[: args.limit]

    print(f"Chấm {len(answerable)} câu (bỏ {len(questions) - len(answerable)} câu "
          f"từ chối / luồng form — không đi qua RAG)")
    print(f"Giám khảo: {args.judge}\n")

    headers = {"Authorization": f"Bearer {_access_token()}"}
    samples: list[dict[str, Any]] = []
    skipped: list[str] = []

    if args.samples_in:
        cached = json.loads(Path(args.samples_in).read_text(encoding="utf-8"))
        samples = cached["samples"]
        skipped = cached.get("skipped", [])
        if args.limit:
            samples = samples[: args.limit]
        print(f"Dung lai {len(samples)} mau tu {args.samples_in} "
              f"(khong goi /chat, khong ton luot embedding)\n")
        answerable = answerable[: len(samples) + len(skipped)]

    for question in [] if args.samples_in else answerable:
        payload = _ask(args.api, headers, question["question"])
        answer = payload.get("answer", "")
        contexts = _fetch_contexts(question["question"])

        if payload.get("answer_source") == "error" or not contexts:
            # Không có ngữ cảnh thì cả ba chỉ số đều vô nghĩa — loại hẳn khỏi
            # mẫu thay vì để RAGAS trả NaN rồi lẫn vào trung bình.
            #
            # Ghi RÕ LÝ DO, không gộp thành một dòng chung: lần chạy 05/09 bỏ
            # 8 câu mà báo cáo chỉ ghi mã câu, không ai biết là lỗi mạng, hết
            # quota, hay KB thật sự không có tài liệu — ba nguyên nhân đòi ba
            # cách xử lý khác hẳn nhau.
            reason = (
                f"API loi: {answer[:60]}"
                if payload.get("answer_source") == "error"
                else "khong truy xuat duoc ngu canh (quota embedding?)"
            )
            skipped.append({"id": question["id"], "reason": reason})
            print(f"  BO   {question['id']}  {reason}")
            continue

        samples.append(
            {
                "user_input": question["question"],
                "response": answer,
                "retrieved_contexts": contexts,
            }
        )
        print(f"  OK   {question['id']}  {len(contexts)} chunk  {question['question'][:44]}")
        if args.pause:
            time.sleep(args.pause)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if samples and not args.samples_in:
        # Ghi mau NGAY, truoc khi cham. Buoc cham hay chet giua chung (het
        # credit, timeout) - khong luu thi lan sau phai hoi lai ca 28 cau va
        # dot them mot luot quota embedding cho cung mot bo du lieu.
        samples_path = OUT_DIR / f"ragas-{datetime.now(UTC).strftime('%Y%m%d-%H%M')}-samples.json"
        samples_path.write_text(
            json.dumps({"samples": samples, "skipped": skipped},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nDa luu mau: {samples_path}")

    if not samples:
        print("\nKhong co mau nao cham duoc — dung.")
        return

    # 8192 token: du cho phep cham dai nhat (faithfulness tach cau tra loi
    # thanh tung menh de roi doi chieu tung cai voi 4 chunk ngu canh), ma muc
    # giu cho credit van chi bang 1/8 tran mac dinh 65_536. Da thu 2048 va bi
    # `LLMDidNotFinishException`: giam khao bi cat giua chung nen RAGAS bo mau
    # do — cat qua tay thi mat mau, y het loi 402.
    llm = LangchainLLMWrapper(_get_judge_llm(args.judge, max_tokens=8192))
    embeddings = LangchainEmbeddingsWrapper(get_embeddings())

    print(f"\n{'='*54}")
    print(f"Chay RAGAS tren {len(samples)} mau (max_workers={args.workers})...")
    result = evaluate(
        dataset=EvaluationDataset.from_list(samples),
        metrics=_build_metrics(llm, embeddings),
        llm=llm,
        embeddings=embeddings,
        # Mặc định của RAGAS là 16 luồng song song — đủ để vượt hạn mức
        # "in-flight budget" của OpenRouter và làm hàng loạt phép chấm trả 402.
        # Lần chạy 05/09: 17/60 phép chấm chết vì lý do này, RAGAS lặng lẽ bỏ
        # chúng ra khỏi trung bình và in `faithfulness 1.000` — số đẹp vì thất
        # bại bị giấu, không phải vì hệ thống tốt.
        #
        # `timeout` mac dinh 180s: lan chay 05/09 co job chet vi TimeoutError
        # ngay ca khi mang van thong - giam khao manh tra loi cham hon the.
        run_config=RunConfig(
            max_workers=args.workers, timeout=300, max_retries=6, max_wait=120
        ),
    )

    # Đếm mẫu thật sự chấm được cho TỪNG chỉ số. Không có bước này thì một chỉ
    # số trung bình trên 12/20 mẫu trông y hệt chỉ số trung bình trên 20/20.
    df = result.to_pandas()
    print(f"\n{'='*54}")
    scores: dict[str, dict[str, Any]] = {}
    for name in result._repr_dict:
        column = df[name] if name in df.columns else None
        scored_n = int(column.notna().sum()) if column is not None else 0
        failed_n = len(samples) - scored_n
        value = float(column.mean()) if scored_n else float("nan")
        scores[name] = {
            "score": round(value, 4) if scored_n else None,
            "scored_samples": scored_n,
            "failed_samples": failed_n,
        }
        flag = "" if failed_n == 0 else f"  <-- {failed_n} mau LOI, so nay khong day du"
        print(f"  {name:42} {value:.3f}   (n={scored_n}/{len(samples)}){flag}")

    if skipped:
        print(f"\nBo qua {len(skipped)} cau truoc khi cham:")
        for item in skipped:
            print(f"  {item['id']}: {item['reason']}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    path = OUT_DIR / f"ragas-{stamp}.json"
    path.write_text(
        json.dumps(
            {
                "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "api": args.api,
                "judge_model": args.judge,
                "embedding_model": get_settings().embedding_model,
                "total_answerable": len(answerable),
                "samples_built": len(samples),
                "max_workers": args.workers,
                "skipped": skipped,
                "scores": scores,
                "note": (
                    "Chỉ chấm câu expect=answer. Không chạy context_recall / "
                    "answer_correctness vì questions.yaml không có ground_truth. "
                    "Mỗi chỉ số kèm `scored_samples`/`failed_samples` — chỉ số "
                    "có `failed_samples` > 0 là trung bình KHÔNG đầy đủ, đừng "
                    "đem lên slide."
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nKet qua: {path}")


if __name__ == "__main__":
    main()
