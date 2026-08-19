r"""Che thông tin định danh cá nhân (PII) trước khi ghi `chat_history` (V8).

Bảo đảm này đứng ở CODE, không phải ở prompt: `store.add_chat`
(`src/services/store.py`) — nơi ghi DUY NHẤT vào `chat_history`, gọi qua
`src/api/routes.py` — gọi hai hàm thuần ở đây trước khi insert. Không tin LLM
tự chừa lại số CCCD hay số điện thoại của cư dân; một câu dặn trong prompt
không phải bảo đảm kỹ thuật, và sản phẩm giờ còn nhận ảnh CCCD nên rủi ro càng
rõ hơn khi bản ghi này nằm trong DB vô thời hạn.

Vì sao `question` và `answer` bị che KHÁC NHAU
------------------------------------------------
`question` là cư dân tự gõ — số điện thoại xuất hiện ở đó nhiều khả năng là
của chính họ, che luôn cho an toàn.

`answer` được sinh từ tri thức trong KB (`rag_retrieve`), và KB có số điện
thoại CÔNG KHAI — hotline BQL `0827 001 090` / `0946 982 323`
(`data/kb/bql/bql-co-cau-va-quy-trinh.md`). Đây là thông tin hữu ích nhất mà
trợ lý đưa ra; một regex số điện thoại áp lên `answer` sẽ xoá mất nó — và
không chỉ mất thẩm mỹ: `rewrite_query` đọc lại lịch sử hội thoại để viết lại
câu hỏi mơ hồ ("còn phí thì sao?") thành độc lập ngữ cảnh, và các endpoint xem
lại hội thoại (US-07) phát lại nguyên `answer` cho cư dân — hotline bị che ở
cả hai chỗ đó thì hỏng.

Vậy: CCCD và email bị che ở CẢ HAI trường. Số điện thoại chỉ bị che ở
`question`.

Ranh giới của từng regex
-------------------------
- **CCCD/CMND**: đúng 9 hoặc đúng 12 chữ số liên tiếp, cho phép cách nhau
  bằng dấu cách hoặc dấu chấm (cách viết phổ biến khi gõ tay). Chặn hai đầu
  bằng `(?<!\d)` / `(?!\d)` — không khớp một phần của chuỗi số dài/ngắn hơn.
  Nhờ vậy: số điện thoại 10 chữ số không rơi vào (9 hay 12 đều không khớp,
  và biên `(?!\d)`/`(?<!\d)` chặn khớp một phần); mã căn hộ kiểu "S2.03-1512"
  không rơi vào (dấu gạch ngang không nằm trong tập ký tự phân cách được
  chấp nhận, và các cụm số quá ngắn); ngày tháng viết bằng "/" không rơi vào.
  Giới hạn đã biết: một số tiền viết bằng dấu chấm phân cách hàng nghìn mà
  TÌNH CỜ có đúng 9 hoặc 12 chữ số (ví dụ "100.000.000" — 100 triệu) sẽ bị
  nhận nhầm là CCCD. Không xảy ra với số liệu phí hiện có trong
  `data/kb/` (đều 7 chữ số, ví dụ "1.250.000đ") nên chấp nhận đánh đổi này
  thay vì thêm rule đoán ngữ cảnh "đây là tiền hay là CCCD".
  Giới hạn thứ hai, cùng gốc: một số điện thoại +84 viết cách nhóm 3 chữ số
  (ví dụ "+84 901 234 567") có phần sau mã nước vừa đúng 9 chữ số đứng sau
  một dấu cách — bị regex CCCD này nhận nhầm trong CẢ `answer`, nơi lẽ ra số
  điện thoại phải sống sót. Không xảy ra với hotline BQL thật (`0827 001
  090`, viết cụm 4-3-3, 10 chữ số) nên chấp nhận, cùng lý do với giới hạn
  trên — nhưng nếu KB sau này thêm số dạng "+84 xxx xxx xxx" thì giới hạn
  này sẽ lộ.
- **Email**: dạng thông thường `local@domain.tld`. Che TRƯỚC hai loại kia để
  chữ số nằm trong phần `local@` (nếu có) không bị hai regex sau cắn nham
  nhở trước khi email được che trọn vẹn.
- **Điện thoại di động VN**: bắt đầu bằng `0` hoặc `+84`, theo sau đúng 9 chữ
  số, cho phép cách nhau bằng dấu cách/dấu chấm. Cùng biên chặn số như CCCD.
"""

from __future__ import annotations

import re

MASK = "[ĐÃ ẨN THÔNG TIN CÁ NHÂN]"

# Alt 12 chữ số đứng trước alt 9 chữ số: nếu cả hai đều có thể bắt đầu khớp
# tại cùng vị trí, ưu tiên khớp dài hơn (CCCD mới) thay vì dừng sớm ở 9 số
# rồi bỏ sót phần còn lại.
_CCCD_RE = re.compile(r"(?<!\d)\d(?:[ .]?\d){11}(?!\d)|(?<!\d)\d(?:[ .]?\d){8}(?!\d)")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+84|0)(?:[ .]?\d){9}(?!\d)")


def mask_question(text: str) -> str:
    """Che CCCD, email, và số điện thoại trong câu hỏi cư dân tự gõ."""
    text = _EMAIL_RE.sub(MASK, text)
    text = _CCCD_RE.sub(MASK, text)
    text = _PHONE_RE.sub(MASK, text)
    return text


def mask_answer(text: str) -> str:
    """Che CCCD và email trong câu trả lời — KHÔNG che số điện thoại.

    Số điện thoại trong `answer` đến từ tri thức công khai (hotline BQL);
    lý do đầy đủ ở docstring module.
    """
    text = _EMAIL_RE.sub(MASK, text)
    text = _CCCD_RE.sub(MASK, text)
    return text
