"""Cào các trang hướng dẫn thủ tục cư dân về Markdown cho knowledge base.

Chạy:  python scripts/scrape_kb.py

Đầu ra: data/kb/web/<slug>.md  (có frontmatter) + data/kb/web/sources.json

Đây là bước LẤY dữ liệu (role Data), tách khỏi bước nạp vào Chroma
(src/services/ingest.py). Chạy lại được nhiều lần, ghi đè file cũ.

LƯU Ý VỀ NGUỒN: vinhomessmartcitytaymo.com KHÔNG phải trang chính thức của
Ban quản lý. Nội dung để tham khảo/đối chiếu, mọi con số (lệ phí, thời gian
xử lý) phải xác nhận lại với BQL trước khi đưa vào câu trả lời chính thức.
Vì vậy source_type được đánh dấu riêng là "unofficial_web".
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "kb" / "web"

USER_AGENT = "MoveInMate-KB-Scraper/0.1 (VinUni AI20K student project)"

SOURCES = [
    {
        "slug": "vsc-the-cu-dan",
        "url": "https://vinhomessmartcitytaymo.com/cu-dan/the-cu-dan/",
        "topic": "Thẻ cư dân",
    },
    {
        "slug": "vsc-tam-tru-luu-tru",
        "url": "https://vinhomessmartcitytaymo.com/cu-dan/khai-bao-tam-tru-thong-bao-luu-tru/",
        "topic": "Khai báo tạm trú / thông báo lưu trú",
    },
]

CONTENT_SELECTOR = "div.space-page-content"

# Điều hướng, mục lục, script, ảnh, khối CTA Facebook — không phải nội dung thủ tục.
DROP_SELECTORS = [
    "nav",
    "script",
    "style",
    "figure",
    "div.wp-block-rank-math-toc-block",
    "div.vsc-scope",
]


def fetch(url: str) -> str:
    response = httpx.get(
        url,
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response.text


def inline_text(node: Tag, base_url: str) -> str:
    """Gộp nội dung inline thành một dòng, giữ link ngoài dưới dạng markdown."""
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag):
            if child.name == "a" and child.get("href"):
                href = urljoin(base_url, child["href"])
                label = child.get_text(" ", strip=True)
                parts.append(f"[{label}]({href})" if label else "")
            elif child.name == "br":
                parts.append(" ")
            elif child.name in {"li", "p"}:
                # Trong ô bảng, nhiều <li> nằm cạnh nhau — không có dấu ngăn
                # thì các mục dính liền thành một chuỗi vô nghĩa.
                parts.append(inline_text(child, base_url) + "; ")
            else:
                parts.append(inline_text(child, base_url))
    text = re.sub(r"\s+", " ", "".join(parts)).strip()
    return re.sub(r"[;\s]+$", "", text)


def render_list(node: Tag, base_url: str, depth: int = 0) -> list[str]:
    lines: list[str] = []
    ordered = node.name == "ol"
    indent = "  " * depth
    index = 1
    for item in node.find_all("li", recursive=False):
        nested = [c for c in item.find_all(["ul", "ol"], recursive=False)]
        for sub in nested:
            sub.extract()
        text = inline_text(item, base_url)
        if text:
            marker = f"{index}." if ordered else "-"
            lines.append(f"{indent}{marker} {text}")
            index += 1
        for sub in nested:
            lines.extend(render_list(sub, base_url, depth + 1))
    return lines


def render(node: Tag, base_url: str) -> list[str]:
    """Duyệt đệ quy container nội dung, trả về các khối markdown."""
    blocks: list[str] = []

    for child in node.children:
        if not isinstance(child, Tag):
            continue

        name = child.name
        classes = child.get("class") or []

        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            text = inline_text(child, base_url)
            if text:
                blocks.append(f"{'#' * int(name[1])} {text}")

        elif name == "p":
            text = inline_text(child, base_url)
            if text:
                blocks.append(text)

        elif name in {"ul", "ol"}:
            lines = render_list(child, base_url)
            if lines:
                blocks.append("\n".join(lines))

        elif name == "table":
            blocks.append(render_table(child, base_url))

        elif "faq-item" in classes:
            question = child.select_one(".faq-question")
            answer = child.select_one(".faq-answer")
            if question:
                # Bỏ mũi tên ▼ của nút accordion.
                for arrow in question.select(".arrow"):
                    arrow.extract()
                blocks.append(f"#### {inline_text(question, base_url)}")
            if answer:
                blocks.extend(render(answer, base_url))

        else:
            # section, div bọc ngoài — đi tiếp vào trong.
            blocks.extend(render(child, base_url))

    return [b for b in blocks if b]


def render_table(table: Tag, base_url: str) -> str:
    rows = []
    for tr in table.find_all("tr"):
        cells = [inline_text(td, base_url) for td in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(out)


def scrape(source: dict) -> dict:
    html = fetch(source["url"])
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.get_text(strip=True) if soup.title else source["topic"]

    content = soup.select_one(CONTENT_SELECTOR)
    if content is None:
        raise RuntimeError(
            f"Không tìm thấy '{CONTENT_SELECTOR}' ở {source['url']} — "
            "trang có thể đã đổi layout, cần sửa CONTENT_SELECTOR."
        )

    for selector in DROP_SELECTORS:
        for node in content.select(selector):
            node.extract()

    blocks = render(content, source["url"])
    body = "\n\n".join(blocks)

    fetched_at = datetime.now(UTC).isoformat(timespec="seconds")
    frontmatter = "\n".join(
        [
            "---",
            f'title: "{title}"',
            f"source_url: {source['url']}",
            "source_type: unofficial_web",
            "publisher: vinhomessmartcitytaymo.com",
            "is_official: false",
            f'topic: "{source["topic"]}"',
            f"fetched_at: {fetched_at}",
            "---",
        ]
    )

    path = OUT_DIR / f"{source['slug']}.md"
    path.write_text(f"{frontmatter}\n\n# {title}\n\n{body}\n", encoding="utf-8")

    return {
        "slug": source["slug"],
        "url": source["url"],
        "topic": source["topic"],
        "title": title,
        "file": str(path.relative_to(OUT_DIR.parent.parent.parent)).replace("\\", "/"),
        "chars": len(body),
        "blocks": len(blocks),
        "fetched_at": fetched_at,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = []
    for source in SOURCES:
        record = scrape(source)
        manifest.append(record)
        print(f"OK  {record['slug']:<24} {record['chars']:>6} ky tu  {record['blocks']:>3} block")

    (OUT_DIR / "sources.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nDa ghi {len(manifest)} file vao {OUT_DIR}")


if __name__ == "__main__":
    main()
