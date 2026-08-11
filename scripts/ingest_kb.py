"""Nạp toàn bộ tài liệu `data/kb/**/*.md` vào Chroma.

Chạy:  python -m scripts.ingest_kb

Chạy lại được nhiều lần — xem docstring của `src/services/ingest.py`.
"""

from __future__ import annotations

from src.database import SessionLocal
from src.services.ingest import KB_DIR, ingest_file


def main() -> None:
    db = SessionLocal()
    results: list[tuple[str, int]] = []
    try:
        for path in sorted(KB_DIR.rglob("*.md")):
            print(f"-> {path.name} ...")
            count = ingest_file(db, path)
            results.append((path.name, count))
            print(f"OK  {path.name:<45} {count:>3} chunk")
    finally:
        db.close()

    total = sum(count for _, count in results)
    print(f"\nTong: {total} chunk tu {len(results)} file")


if __name__ == "__main__":
    main()
