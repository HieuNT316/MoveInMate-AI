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
  thay vì thêm rule đoán ngữ cảnh "đây là tiền hay là CCCD". Không đổi ở
  round 2 — brief yêu cầu giữ nguyên đánh đổi này.
- **Email**: dạng thông thường `local@domain.tld`. Che TRƯỚC hai loại kia để
  chữ số nằm trong phần `local@` (nếu có) không bị hai regex sau cắn nham
  nhở trước khi email được che trọn vẹn.
- **Điện thoại di động VN**: bắt đầu bằng `0` hoặc `+84`, theo sau đúng 9 chữ
  số, cho phép cách nhau bằng dấu cách/dấu chấm. Cùng biên chặn số như CCCD.

Vì sao thứ tự CCCD/điện thoại đổi ở round 2 — và guard round 1 bị BỎ HẲN
-------------------------------------------------------------------------
Round 1 vá một lỗ hổng khác (`+84 123 456 789` bị CCCD nhận nhầm trong
`answer`) bằng bốn lookbehind cố định đoán "đứng ngay sau tiền tố điện
thoại thì không phải CCCD". Cách đó có lỗi cấu trúc, không phải lỗi độ
chính xác: `(?<!\d)` (và bất kỳ lookbehind cố định nào) chỉ nhìn được một
số ký tự CỐ ĐỊNH ngay trước vị trí khớp — không thể biểu diễn "đứng sau một
số `0` mà bản thân số `0` đó cũng đứng ở ranh giới từ". Hệ quả: trong
"phòng 10 123456789", cụm "0 " của chính chữ số cuối trong "10" (không
liên quan gì tới điện thoại) trùng khớp y hệt lookbehind `(?<!0 )`, chặn
luôn CCCD thật ngay sau nó — kể cả trong `question`, nơi che PII không được
phép có ngoại lệ (fix round 2, task 19).

Sửa bằng cách xử lý thứ tự thay vì đoán ngữ cảnh bằng lookbehind:

- `mask_question`: che email, rồi **điện thoại TRƯỚC**, rồi CCCD. Điện
  thoại trong `question` đằng nào cũng bị che, nên quét nó trước sẽ dọn
  sạch mọi dãy số thuộc về số điện thoại (kèм tiền tố) trước khi CCCD kịp
  chạy — không còn gì để CCCD hiểu lầm, không cần đoán tiền tố bằng
  lookbehind nữa, và đúng cho MỌI cách viết `_PHONE_RE` nhận ra, không chỉ
  4 dạng cố định như guard round 1.
- `mask_answer`: điện thoại không bị che ở đây, nên không thể áp dụng mẹo
  "che trước" — CHE là xoá mất nó. Thay vào đó: che email, rồi **bảo vệ**
  các khớp điện thoại bằng cách thế chỗ tạm bằng `_PHONE_PLACEHOLDER` (giữ
  nguyên vị trí, giấu khỏi mắt CCCD), rồi cho CCCD chạy trên phần còn lại,
  rồi **khôi phục** placeholder về đúng văn bản gốc theo đúng thứ tự đã gặp.
  `_PHONE_PLACEHOLDER` dùng ký tự Private Use Area (`U+E000`) bao quanh một
  nhãn chữ cái — không chứa chữ số nên `_CCCD_RE` (chỉ khớp dãy chữ số)
  không thể bắt nhầm nó, và `U+E000` gần như chắc chắn không xuất hiện
  trong văn bản người dùng/KB thật (không phải ký tự bàn phím thường gõ).
"""

from __future__ import annotations

import re

MASK = "[ĐÃ ẨN THÔNG TIN CÁ NHÂN]"

# Placeholder tạm dùng trong `mask_answer` để giấu số điện thoại khỏi
# `_CCCD_RE` — xem đoạn "Vì sao thứ tự... round 2" ở docstring module.
_PHONE_PLACEHOLDER = "\uE000PHONEPLACEHOLDER\uE000"

# Alt 12 chữ số đứng trước alt 9 chữ số: nếu cả hai đều có thể bắt đầu khớp
# tại cùng vị trí, ưu tiên khớp dài hơn (CCCD mới) thay vì dừng sớm ở 9 số
# rồi bỏ sót phần còn lại. KHÔNG còn lookbehind đoán tiền tố điện thoại
# (guard round 1 đã bỏ — xem docstring module, mục round 2): bảo đảm
# "điện thoại không bị hiểu nhầm là CCCD" nay nằm ở THỨ TỰ gọi trong
# `mask_question`/`mask_answer`, không nằm trong bản thân regex này.
_CCCD_RE = re.compile(r"(?<!\d)\d(?:[ .]?\d){11}(?!\d)|(?<!\d)\d(?:[ .]?\d){8}(?!\d)")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+84|0)(?:[ .]?\d){9}(?!\d)")


def mask_question(text: str) -> str:
    """Che email, điện thoại, rồi CCCD trong câu hỏi cư dân tự gõ.

    Điện thoại chạy TRƯỚC CCCD — dọn sạch mọi dãy số thuộc số điện thoại
    trước khi CCCD kịp hiểu lầm phần đuôi của nó (lý do đầy đủ ở docstring
    module, mục round 2).
    """
    text = _EMAIL_RE.sub(MASK, text)
    text = _PHONE_RE.sub(MASK, text)
    text = _CCCD_RE.sub(MASK, text)
    return text


def mask_answer(text: str) -> str:
    """Che CCCD và email trong câu trả lời — KHÔNG che số điện thoại.

    Số điện thoại trong `answer` đến từ tri thức công khai (hotline BQL);
    lý do đầy đủ ở docstring module. Vì không thể "che trước để dọn đường"
    như `mask_question` (che ở đây nghĩa là xoá mất), số điện thoại được
    BẢO VỆ bằng placeholder tạm trong lúc CCCD chạy, rồi khôi phục nguyên
    văn — xem docstring module, mục round 2.
    """
    text = _EMAIL_RE.sub(MASK, text)

    phones: list[str] = []

    def _protect(match: re.Match[str]) -> str:
        phones.append(match.group(0))
        return _PHONE_PLACEHOLDER

    text = _PHONE_RE.sub(_protect, text)
    text = _CCCD_RE.sub(MASK, text)

    # Khôi phục lần lượt, TRÁI SANG PHẢI — re.sub duyệt các khớp theo
    # đúng thứ tự xuất hiện, khớp với thứ tự `phones` đã thu thập ở bước bảo vệ.
    phones_iter = iter(phones)
    return re.sub(re.escape(_PHONE_PLACEHOLDER), lambda _m: next(phones_iter), text)
