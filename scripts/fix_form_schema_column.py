"""Fix: add missing columns after migration state mismatch.

Chạy: python -m scripts.fix_form_schema_column

DATABASE_URL được đọc tự động từ .env (qua pydantic-settings trong config.py).

Sau nhiều merge migration, có thể alembic_version = head nhưng một số cột
chưa thực sự được tạo (vì migration gốc là NO-OP hoặc đã ALTER tay).

Script này an toàn:
- Kiểm tra cột đã tồn tại chưa trước khi thêm
- Chỉ chạy ALTER nếu cần
- Không ảnh hưởng dữ liệu hiện có
"""

from __future__ import annotations

import sys

from src.config import get_settings, safe_database_url


def main() -> None:
    settings = get_settings()
    db_url = settings.database_url
    print(f"DATABASE_URL: {safe_database_url()}")

    from sqlalchemy import create_engine, inspect, text

    engine = create_engine(db_url)

    with engine.connect() as conn:
        inspector = inspect(engine)

        # Các cột cần kiểm tra: (table, column, sql_to_add)
        columns_to_fix = [
            ("checklist_items", "form_schema", "ALTER TABLE checklist_items ADD COLUMN form_schema JSONB"),
            ("applications", "form_data", "ALTER TABLE applications ADD COLUMN form_data JSONB NOT NULL DEFAULT '{}'"),
        ]

        for table, col, sql in columns_to_fix:
            existing = {c["name"] for c in inspector.get_columns(table)}
            print(f"\n[{table}] Cột hiện tại: {sorted(existing)}")

            if col in existing:
                print(f"  OK: {col} đã tồn tại.")
            else:
                print(f"  WARNING: {col} KHÔNG tồn tại. Đang thêm...")
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"  SUCCESS: Đã thêm {col} vào {table}.")
                except Exception as e:
                    print(f"  ERROR: {e}")
                    sys.exit(1)

    engine.dispose()
    print("\nFix hoàn tất! Redeploy Railway backend.")


if __name__ == "__main__":
    main()
