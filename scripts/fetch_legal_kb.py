"""Tải Quy chế quản lý, sử dụng nhà chung cư (kèm Thông tư 05/2024/TT-BXD).

Chạy:  python scripts/fetch_legal_kb.py
Đầu ra: data/kb/legal/tt-05-2024-quy-che-nha-chung-cu.md

VÌ SAO KHÔNG DÙNG THÔNG TƯ 02/2016/TT-BXD như charter đề xuất:
02/2016 đã HẾT HIỆU LỰC từ 01/08/2024, bị thay bởi 05/2024/TT-BXD (ban hành
31/07/2024 theo Luật Nhà ở 2023). Nạp văn bản hết hiệu lực vào một hệ thống
có trích nguồn = trả lời sai kèm trích dẫn trông đáng tin. Xem docs/PROJECT_CHARTER.md.

VÌ SAO KHÔNG DÙNG PDF CỦA CỔNG CHÍNH PHỦ:
datafiles.chinhphu.vn/cpp/files/vbpq/2024/8/05-bxd.pdf là bản SCAN 37MB,
142 trang, không có lớp text — pypdf trích ra 0 ký tự. Cần OCR mới dùng được.
Nguồn HTML của VCCI có toàn văn dạng <p> sạch nên dùng nguồn này.

PHẠM VI CẮT: chỉ lấy phần Quy chế (Điều 1-50). Bỏ thân Thông tư (nhà ở xã hội,
chương trình phát triển nhà ở) và Phụ lục I-VII (mẫu hợp đồng mua bán/thuê mua)
— khoảng 155k ký tự không liên quan đến thủ tục cư dân nhận nhà.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "kb" / "legal"

SOURCE_URL = "https://vcci.com.vn/legal-document/05-2024-tt-bxd"
SLUG = "tt-05-2024-quy-che-nha-chung-cu"

# Ranh giới cắt — dò theo nội dung <p>, không hardcode chỉ số.
START_MARKER = "QUY CHẾ"
END_MARKER = "PHỤ LỤC I"


def paragraphs(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.extract()
    return [p for p in (x.get_text(" ", strip=True) for x in soup.find_all("p")) if p]


def slice_quy_che(paras: list[str]) -> list[str]:
    """Cắt lấy đúng phần Quy chế: từ tiêu đề 'QUY CHẾ' tới trước 'PHỤ LỤC I'."""
    start = next(
        (
            i
            for i, p in enumerate(paras)
            if p == START_MARKER and "NHÀ CHUNG CƯ" in paras[i + 1].upper()
        ),
        None,
    )
    end = next((i for i, p in enumerate(paras) if p == END_MARKER), None)
    if start is None or end is None or end <= start:
        raise RuntimeError(
            "Không xác định được ranh giới Quy chế — trang nguồn có thể đã đổi cấu trúc."
        )
    return paras[start:end]


def to_markdown(paras: list[str]) -> tuple[str, dict[str, int]]:
    """Đánh dấu phân cấp Chương / Mục / Điều để chunk theo đơn vị pháp lý."""
    lines: list[str] = []
    counts = {"chuong": 0, "muc": 0, "dieu": 0}
    skip_next = False

    for i, para in enumerate(paras):
        if skip_next:
            skip_next = False
            continue

        if re.fullmatch(r"Chương [IVXLC]+", para):
            title = paras[i + 1] if i + 1 < len(paras) else ""
            lines.append(f"\n# {para}. {title}")
            counts["chuong"] += 1
            skip_next = True
        elif re.match(r"^Mục \d+\.", para):
            lines.append(f"\n### {para}")
            counts["muc"] += 1
        elif re.match(r"^Điều \d+\.", para):
            lines.append(f"\n## {para}")
            counts["dieu"] += 1
        else:
            lines.append(para)

    return "\n".join(lines).strip(), counts


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    response = httpx.get(
        SOURCE_URL,
        timeout=60,
        follow_redirects=True,
        headers={"User-Agent": "MoveInMate-KB-Scraper/0.1 (VinUni AI20K student project)"},
    )
    response.raise_for_status()

    quy_che = slice_quy_che(paragraphs(response.text))
    body, counts = to_markdown(quy_che)

    fetched_at = datetime.now(UTC).isoformat(timespec="seconds")
    title = "Quy chế quản lý, sử dụng nhà chung cư (kèm Thông tư 05/2024/TT-BXD)"
    frontmatter = "\n".join(
        [
            "---",
            f'title: "{title}"',
            f"source_url: {SOURCE_URL}",
            "source_type: public_regulation",
            "publisher: Bộ Xây dựng",
            "is_official: true",
            "van_ban: 05/2024/TT-BXD",
            "ngay_ban_hanh: 2024-07-31",
            "ngay_hieu_luc: 2024-08-01",
            "thay_the: 02/2016/TT-BXD (hết hiệu lực 01/08/2024)",
            f"fetched_at: {fetched_at}",
            "---",
        ]
    )

    path = OUT_DIR / f"{SLUG}.md"
    path.write_text(f"{frontmatter}\n\n# {title}\n\n{body}\n", encoding="utf-8")

    (OUT_DIR / "sources.json").write_text(
        json.dumps(
            [
                {
                    "slug": SLUG,
                    "url": SOURCE_URL,
                    "title": title,
                    "van_ban": "05/2024/TT-BXD",
                    "file": f"data/kb/legal/{SLUG}.md",
                    "chars": len(body),
                    **counts,
                    "fetched_at": fetched_at,
                }
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"OK  {SLUG}")
    print(f"    {len(body)} ky tu | {counts['chuong']} chuong, {counts['muc']} muc, {counts['dieu']} dieu")
    print(f"    -> {path}")


if __name__ == "__main__":
    main()
