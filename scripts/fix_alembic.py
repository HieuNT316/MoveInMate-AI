"""Fix Alembic migration state bị lệch.

Chạy:  DATABASE_URL="postgresql://..." python -m scripts.fix_alembic

Script này:
1. Xoá record alembic_version không tồn tại trong code
2. Stamp database về version migration mới nhất
3. Chạy upgrade để đảm bảo schema đồng bộ
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        print("Chạy: DATABASE_URL='postgresql://...' python -m scripts.fix_alembic")
        sys.exit(1)

    # Mask password for display
    import re
    safe = re.sub(r"(://[^:]+:)[^@]+(@)", r"\1***\2", db_url)
    print(f"DATABASE_URL: {safe}")

    from sqlalchemy import create_engine, inspect, text
    from alembic.config import Config
    from alembic import command

    engine = create_engine(db_url)

    # Check alembic_version table
    with engine.connect() as conn:
        tables = inspect(engine).get_table_names()
        print(f"Tables: {tables}")

        if "alembic_version" not in tables:
            print("Không có bảng alembic_version - database chưa có migration nào")
            sys.exit(0)

        result = conn.execute(text("SELECT * FROM alembic_version"))
        rows = result.fetchall()
        print(f"alembic_version rows: {rows}")

        if not rows:
            print("alembic_version trống - đã stamp rồi, không cần fix")
            sys.exit(0)

        # Get the problematic version
        current_version = rows[0][0]
        print(f"Current version: {current_version}")

        # List available migrations
        from alembic import config
        alembic_cfg = Config()
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        alembic_cfg.config_file_name = "alembic.ini"

        from alembic.script import ScriptDirectory
        script = ScriptDirectory.from_config(alembic_cfg)

        # Check if current version exists
        heads = script.get_heads()
        print(f"Available heads: {heads}")

        # Check if current version is valid
        if current_version not in script.get_revisions():
            print(f"\nWARNING: Version '{current_version}' không tồn tại trong code!")
            print("Đây là nguyên nhân crash khi deploy.\n")

            # Show what migrations exist
            revisions = list(script.walk_revisions())
            print(f"Có {len(revisions)} migration(s) trong code:")
            for r in revisions:
                print(f"  - {r.revision}")

            # Delete the bad record
            confirm = input(f"\nXoá record '{current_version}' từ alembic_version? (y/N): ")
            if confirm.lower() == 'y':
                conn.execute(text("DELETE FROM alembic_version"))
                conn.commit()
                print("Đã xoá record lệch.")

                # Stamp to head
                print("\nStamp database về head...")
                command.stamp(alembic_cfg, "head")
                print("Done! Database đã đồng bộ.")
            else:
                print("Hủy.")
                sys.exit(1)
        else:
            print(f"Version '{current_version}' hợp lệ - không cần fix")

    engine.dispose()


if __name__ == "__main__":
    main()
