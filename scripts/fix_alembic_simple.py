"""Fix alembic_version - xoá row lệch."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text


def main() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return

    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Check current state
        result = conn.execute(text("SELECT * FROM alembic_version"))
        rows = result.fetchall()
        print(f"alembic_version TRƯỚC: {rows}")

        # Delete bad version
        result = conn.execute(
            text("DELETE FROM alembic_version WHERE version_num = :v"),
            {"v": "8f3a1c2e4b5d"}
        )
        conn.commit()
        print(f"Đã xoá {result.rowcount} row(s)")

        # Verify
        result = conn.execute(text("SELECT * FROM alembic_version"))
        rows = result.fetchall()
        print(f"alembic_version SAU: {rows}")

    engine.dispose()
    print("\nFix hoàn tất! Giờ redeploy Railway backend.")


if __name__ == "__main__":
    main()
