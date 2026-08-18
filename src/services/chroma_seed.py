"""Nạp mồi Chroma vào volume rỗng lúc khởi động.

Vì sao cần: từ 18/08 `data/chroma` là một Railway Volume để tài liệu BQL nạp
không mất sau mỗi lần deploy. Volume mới gắn thì RỖNG. Container khởi động với
Chroma rỗng → `rag_retrieve` không trả về gì → guard chống bịa kích hoạt ở mọi
câu hỏi → trợ lý từ chối trả lời toàn bộ, mà không màn hình nào báo lỗi và mọi
chỉ báo vẫn xanh.

Bản mồi KHÔNG thể nằm ở chính đường dẫn volume: mount che khuất nội dung image
ở đấy. Dockerfile chép sang `/app/data/chroma_seed`, module này chép ngược lại.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_seeded(persist_dir: str, seed_dir: str) -> bool:
    """Chép bản mồi vào `persist_dir` nếu nó rỗng. Trả True nếu đã chép."""
    target = Path(persist_dir)
    seed = Path(seed_dir)

    if not seed.is_dir():
        logger.warning("Không có bản mồi Chroma tại %s", seed)
        return False

    if target.is_dir() and any(target.iterdir()):
        # KHÔNG chép đè: sẽ xoá mất tài liệu BQL vừa nạp trên production.
        return False

    try:
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(seed, target, dirs_exist_ok=True)
    except Exception:
        # Chép dở dang trông giống "đã seed" ở lần khởi động sau — dọn sạch để
        # lần sau còn thử lại, thay vì kẹt mãi với dữ liệu chép nửa chừng.
        shutil.rmtree(target, ignore_errors=True)
        logger.error("Chép mồi Chroma thất bại, đã dọn %s", target)
        raise

    logger.info("Đã nạp mồi Chroma từ %s", seed)
    return True
