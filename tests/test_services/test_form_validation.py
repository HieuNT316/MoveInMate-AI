"""Tests for validate_form_data in store.py."""

from src.models.schemas import FormFieldSchema, FormSchemaPayload
from src.services.store import validate_form_data


def test_validate_missing_required():
    schema = FormSchemaPayload(fields=[
        FormFieldSchema(key="plate", label="Biển số", type="text",
                       required=True, pattern=r"^[0-9A-Z\-]{5,15}$",
                       question="Nhập biển số xe"),
    ])
    errors = validate_form_data(schema, {})
    assert any("Thiếu: Biển số" in e for e in errors)


def test_validate_invalid_pattern():
    schema = FormSchemaPayload(fields=[
        FormFieldSchema(key="plate", label="Biển số", type="text",
                       required=True, pattern=r"^[0-9A-Z\-]{5,15}$",
                       question="Nhập biển số xe"),
    ])
    errors = validate_form_data(schema, {"plate": "abc"})
    assert any("sai định dạng" in e for e in errors)


def test_validate_ok():
    schema = FormSchemaPayload(fields=[
        FormFieldSchema(key="plate", label="Biển số", type="text",
                       required=True, pattern=r"^[0-9A-Z\.\-]{5,15}$",
                       question="Nhập biển số xe"),
    ])
    errors = validate_form_data(schema, {"plate": "30A-123.45"})
    assert errors == []


class TestCreateApplicationLuonValidateKhiCoForm:
    """Thủ tục CÓ form thì phải validate, kể cả khi client không gửi gì.

    Bản cũ viết `if form_data:` — falsy với cả `None` LẪN `{}`. Mà
    `ApplicationCreateV2.form_data` mặc định `None`, nên client chỉ cần bỏ
    trường đó là nộp được hồ sơ "Đăng ký thẻ xe" KHÔNG biển số, không loại xe.
    Đo trên DB thật trước khi sửa: `validate_form_data(schema, {})` trả hai lỗi
    "Thiếu", nhưng `create_application(form_data=None)` vẫn tạo thành công.

    Đúng cái mà toàn bộ tính năng AI Form Generation sinh ra để chặn: BQL nhận
    hồ sơ rỗng và lại phải gọi điện hỏi lại từng người.
    """

    def _dung_thu_tuc_co_form(self, db_session):
        from src.models.db import ChecklistItem

        item = ChecklistItem(
            task_name="Đăng ký thẻ xe",
            description="",
            category="Phương tiện",
            item_type="bql_actionable",
            conditions={},
            order_index=1,
            required_documents=[],
            form_schema={
                "fields": [
                    {
                        "key": "plate",
                        "label": "Biển số xe",
                        "type": "text",
                        "required": True,
                        "question": "Biển số xe của bạn?",
                    }
                ],
                "attachments": [],
            },
        )
        db_session.add(item)
        db_session.flush()
        return item.checklist_item_id

    def _dung_cu_dan(self, db_session):
        from src.models.db import User

        u = User(
            full_name="Nguyễn Văn Test",
            email="test.form@moveinmate.demo",
            apartment="S101-0101",
            building="S101",
            role="resident",
            has_car=True,
            amenity_packages=[],
        )
        db_session.add(u)
        db_session.flush()
        return u.user_id

    def test_khong_gui_form_data_thi_bi_chan(self, db_session):
        from src.services.store import ValidationError, create_application

        item_id = self._dung_thu_tuc_co_form(db_session)
        user_id = self._dung_cu_dan(db_session)

        try:
            create_application(
                db_session,
                user_id=user_id,
                checklist_item_id=item_id,
                kind="bql_processing",
                form_data=None,
            )
            raise AssertionError("Phải chặn: thủ tục có form mà không gửi form_data")
        except ValidationError as exc:
            assert "Biển số xe" in str(exc.errors)

    def test_gui_form_data_rong_thi_bi_chan(self, db_session):
        from src.services.store import ValidationError, create_application

        item_id = self._dung_thu_tuc_co_form(db_session)
        user_id = self._dung_cu_dan(db_session)

        try:
            create_application(
                db_session,
                user_id=user_id,
                checklist_item_id=item_id,
                kind="bql_processing",
                form_data={},
            )
            raise AssertionError("Phải chặn: form_data rỗng")
        except ValidationError:
            pass

    def test_thu_tuc_khong_co_form_van_nop_duoc(self, db_session):
        """Đừng chặn nhầm: tạm trú, ký nội quy… không có form."""
        from src.models.db import ChecklistItem
        from src.services.store import create_application

        item = ChecklistItem(
            task_name="Đăng ký tạm trú tại công an phường",
            description="",
            category="Cư trú",
            item_type="third_party_info",
            conditions={},
            order_index=2,
            required_documents=[],
            form_schema=None,
        )
        db_session.add(item)
        db_session.flush()
        user_id = self._dung_cu_dan(db_session)

        app = create_application(
            db_session,
            user_id=user_id,
            checklist_item_id=item.checklist_item_id,
            kind="self_declared",
            form_data=None,
        )
        assert app["application_id"] is not None
