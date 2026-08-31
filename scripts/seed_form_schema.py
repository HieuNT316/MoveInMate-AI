"""Sinh form_schema JSONB cho checklist_items.

Chay: python -m scripts.seed_form_schema
"""
from src.database import SessionLocal
from src.models.db import ChecklistItem
from src.models.schemas import FormSchemaPayload, FormFieldSchema, AttachmentSpecSchema

PROCEDURES = {
    "Đăng ký thẻ xe": FormSchemaPayload(fields=[
        FormFieldSchema(key="vehicle_type", label="Loại phương tiện",
                       type="select", options=["Ô tô","Xe máy"],
                       required=True, question="Bạn đăng ký thẻ xe gì?"),
        # Dấu CHẤM phải nằm trong tập ký tự cho phép: biển số Việt Nam hiện
        # hành có dạng `29H1-234.56` (xe máy, và ô tô cấp sau 2020). Bản đầu
        # thiếu dấu chấm nên từ chối đúng những biển số thật — cư dân gõ đúng
        # mà bị báo "sai định dạng", không có cách nào đi tiếp.
        FormFieldSchema(key="plate", label="Biển số xe", type="text",
                       required=True, question="Biển số xe của bạn là gì?",
                       pattern=r"^[0-9A-Z.\-]{5,15}$"),
        FormFieldSchema(key="quantity", label="Số lượng thẻ cần làm",
                       type="number", required=False,
                       question="Bạn cần làm bao nhiêu thẻ?", default="1"),
    ], attachments=[
        AttachmentSpecSchema(code="cccd", label="Ảnh CCCD chủ phương tiện", required=True),
        AttachmentSpecSchema(code="dang_ky_xe", label="Ảnh đăng ký xe hoặc hợp đồng", required=True),
        AttachmentSpecSchema(code="the_cu_dan", label="Ảnh thẻ cư dân", required=True),
    ]),
    "Đăng ký chỗ đỗ xe cố định": FormSchemaPayload(fields=[
        FormFieldSchema(key="vehicle_type", label="Loại phương tiện",
                       type="select", options=["Ô tô","Xe máy"],
                       required=True, question="Bạn đăng ký cho loại xe gì?"),
        # Dấu CHẤM phải nằm trong tập ký tự cho phép: biển số Việt Nam hiện
        # hành có dạng `29H1-234.56` (xe máy, và ô tô cấp sau 2020). Bản đầu
        # thiếu dấu chấm nên từ chối đúng những biển số thật — cư dân gõ đúng
        # mà bị báo "sai định dạng", không có cách nào đi tiếp.
        FormFieldSchema(key="plate", label="Biển số xe", type="text",
                       required=True, question="Biển số xe của bạn là gì?",
                       pattern=r"^[0-9A-Z.\-]{5,15}$"),
    ], attachments=[
        AttachmentSpecSchema(code="cccd", label="Ảnh CCCD chủ phương tiện", required=True),
        AttachmentSpecSchema(code="the_xe", label="Ảnh thẻ xe hoặc đăng ký xe", required=True),
        AttachmentSpecSchema(code="don_dang_ky", label="Đơn đăng ký", required=True),
    ]),
    "Làm thẻ cư dân (chủ hộ)": FormSchemaPayload(fields=[
        FormFieldSchema(key="card_count", label="Số lượng thẻ cần làm",
                       type="number", required=True,
                       question="Bạn cần làm bao nhiêu thẻ cư dân?", default="1"),
    ], attachments=[
        AttachmentSpecSchema(code="cccd", label="Ảnh CCCD chủ hộ", required=True),
        AttachmentSpecSchema(code="bien_ban_ban_giao", label="Ảnh biên bản bàn giao", required=True),
    ]),
    "Làm thẻ cư dân (người thuê)": FormSchemaPayload(fields=[
        FormFieldSchema(key="card_count", label="Số lượng thẻ cần làm",
                       type="number", required=True,
                       question="Bạn cần làm bao nhiêu thẻ cư dân?", default="1"),
    ], attachments=[
        AttachmentSpecSchema(code="cccd", label="Ảnh CCCD người thuê", required=True),
        AttachmentSpecSchema(code="hop_dong_thue", label="Ảnh hợp đồng thuê", required=True),
    ]),
    "Kích hoạt thẻ bể bơi": FormSchemaPayload(fields=[
        FormFieldSchema(key="member_count", label="Số thành viên sử dụng",
                       type="number", required=False,
                       question="Có bao nhiêu người trong gia đình sử dụng bể bơi?", default="1"),
    ], attachments=[
        AttachmentSpecSchema(code="the_cu_dan", label="Ảnh thẻ cư dân", required=True),
    ]),
    "Kích hoạt thẻ phòng gym": FormSchemaPayload(fields=[
        FormFieldSchema(key="member_count", label="Số thành viên sử dụng",
                       type="number", required=False,
                       question="Có bao nhiêu người trong gia đình sử dụng gym?", default="1"),
    ], attachments=[
        AttachmentSpecSchema(code="the_cu_dan", label="Ảnh thẻ cư dân", required=True),
    ]),
    "Đăng ký thẻ thang máy": FormSchemaPayload(fields=[
        FormFieldSchema(key="card_count", label="Số lượng thẻ cần cấp",
                       type="number", required=True,
                       question="Bạn cần bao nhiêu thẻ thang máy?", default="1"),
    ], attachments=[
        AttachmentSpecSchema(code="the_cu_dan", label="Ảnh thẻ cư dân", required=True),
    ]),
    "Đăng ký internet và truyền hình": FormSchemaPayload(fields=[
        FormFieldSchema(key="provider", label="Nhà cung cấp mong muốn",
                       type="select", options=["Viettel","VNPT","FPT Telecom"],
                       required=True, question="Bạn muốn lắp đặt qua nhà mạng nào?"),
        FormFieldSchema(key="preferred_date", label="Ngày mong muốn lắp đặt",
                       type="date", required=False,
                       question="Bạn muốn hẹn ngày nào để lắp đặt?"),
    ], attachments=[]),
    "Đăng ký chuyển đồ vào căn hộ": FormSchemaPayload(fields=[
        FormFieldSchema(key="move_date", label="Ngày chuyển đồ",
                       type="date", required=True,
                       question="Bạn dự định chuyển đồ vào ngày nào?"),
        FormFieldSchema(key="time_slot", label="Khung giờ",
                       type="select",
                       options=["8:00–10:00","10:00–12:00","14:00–16:00","16:00–18:00"],
                       required=True,
                       question="Bạn muốn đặt khung giờ nào?"),
        FormFieldSchema(key="mover", label="Đơn vị vận chuyển (nếu có)",
                       type="text", required=False,
                       question="Bạn có thuê đơn vị vận chuyển không?"),
    ], attachments=[
        AttachmentSpecSchema(code="don_dang_ky", label="Đơn đăng ký", required=True),
    ]),
    "Ký nội quy toà nhà": None,  # Chi confirm, khong co form
}


def main() -> None:
    db = SessionLocal()
    try:
        updated = 0
        for task_name, schema_payload in PROCEDURES.items():
            row = db.query(ChecklistItem).filter(
                ChecklistItem.task_name == task_name
            ).first()
            if row:
                row.form_schema = schema_payload.model_dump() if schema_payload else None
                print(f"Updated: {task_name}")
                updated += 1
            else:
                print(f"NOT FOUND: {task_name}")
        db.commit()
        print(f"\nDone. {updated}/{len(PROCEDURES)} rows updated.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
