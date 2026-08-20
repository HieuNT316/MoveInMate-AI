# Handover — AI Form Generation: Phần FE

**Từ:** Claude (implementation)
**Cho:** Nguyễn Minh Thu — Frontend
**Ngày:** 2026-08-20
**Nguồn:** `docs/superpowers/specs/2026-08-20-ai-form-generation-design.md`
**Plan:** `docs/superpowers/plans/2026-08-20-ai-form-generation-plan.md`

---

## Tổng quan feature

Thay thế form cố định bằng **AI dẫn dắt cư dân** qua hội thoại để thu thập thông tin, sinh hồ sơ có cấu trúc, cư dân review và submit.

```
Checklist bấm/trigger → AI hỏi → extract form_data → [FormReviewDialog] → resident review + sửa → submit
```

---

## Phần của bạn (Frontend)

### 1. Đã làm sẵn

**`web/lib/api.ts`** — Task 6
- Types: `FormField`, `FormSchema`, `ApplicationFormData`, `AttachmentSpec`
- `api.getFormSchema(itemId, token)` — gọi `GET /checklist/{id}/form-schema`
- `api.submitApplicationWithFormData(userId, itemId, formData, token)` — POST /applications với `{ checklist_item_id, form_data }`

**`web/app/components/FormReviewDialog.tsx`** — Tasks 6 + fix
- Dialog hiển thị form fields từ AI đã extract
- 2-phase flow: (1) fill form → submit → (2) upload attachments
- Submit button disabled đến khi tất cả attachments required được upload
- Error highlighting từ 422 backend validation

**`SubmitApplicationDialog.tsx`** — Task 6
- Tích hợp FormReviewDialog khi có schema
- Fallback về form cũ khi schema null

### 2. Cần bạn làm

#### 2a. Chat-driven trigger (Phase 2)

Hiện tại chỉ có **checklist-driven** (bấm vào item → mở dialog).

Cần thêm: resident chat "Tôi muốn đăng ký thẻ xe" → AI detect intent → mở FormReviewDialog.

Xem spec Section 3b và Section 7.2.

#### 2b. Disambiguation UI

Khi AI trả về `intent="disambiguation"`, FE cần hiển thị buttons để resident chọn:

```typescript
// Trong ChatSessionDialog:
if (response.intent === "disambiguation") {
  return (
    <div>
      <p>{response.answer}</p>
      {response.options?.map((opt, i) => (
        <button key={i} onClick={() => handleSelect(opt.task_name)}>
          {i+1}. {opt.task_name}
        </button>
      ))}
    </div>
  );
}
```

#### 2c. FormReviewDialog inline trong chat (Phase 2)

Thay vì mở dialog riêng, có thể hiển thị form review trực tiếp trong chat.

---

## Interface cần biết

### API Response — form generation

```typescript
// POST /chat response khi intent = "form_generation"
{
  answer: "...",           // text response
  intent: "form_generation",
  checklist_item_id: 42,
  form_schema: FormSchema,
  form_data: Record<string, string>
}

// POST /chat response khi intent = "disambiguation"
{
  answer: "Có nhiều thủ tục...",
  intent: "disambiguation",
  options: [{ task_name: "...", id: 42 }, ...]
}
```

### API Response — checklist item

```typescript
// GET /checklist/{id}/form-schema
{
  fields: [
    {
      key: "vehicle_type",
      label: "Loại phương tiện",
      type: "select",
      options: ["Ô tô", "Xe máy"],
      required: true,
      question: "Bạn đăng ký thẻ xe gì?"
    },
    ...
  ],
  attachments: [
    { code: "cccd", label: "Ảnh CCCD", required: true },
    ...
  ]
}
```

### Submit payload

```typescript
// POST /applications
{
  checklist_item_id: 42,
  form_data: {
    vehicle_type: "Ô tô",
    plate: "30A-123.45",
    quantity: "1"
  }
}
```

---

## Backend endpoints đã có

| Endpoint | Method | Body |
|---|---|---|
| `/checklist/{id}/form-schema` | GET | — |
| `/applications` | POST | `{ checklist_item_id, form_data }` |
| `/applications/{id}/attachments` | POST | FormData (file upload) |

---

## Spec + Plan

- **Spec:** `docs/superpowers/specs/2026-08-20-ai-form-generation-design.md`
- **Plan:** `docs/superpowers/plans/2026-08-20-ai-form-generation-plan.md`

Đọc spec Section 7 (FE — Resident Review UI) và Section 7.2 (Intent detection) để hiểu luồng đầy đủ.

---

## Câu hỏi?

Liên hệ Hiếu (backend) nếu cần thay đổi API contracts.
