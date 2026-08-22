"""Extract structured fields from conversation history — regex + heuristic, no LLM."""

from __future__ import annotations

from src.models.schemas import FormSchemaPayload


def extract_form_fields(
    schema: FormSchemaPayload,
    history: list[dict],
) -> dict[str, str]:
    """Extract structured fields from conversation history.

    Regex + heuristic. Khong goi LLM.
    """
    result = {}
    user_messages = [m["content"] for m in history if m.get("role") == "user"]

    for field in schema.fields:
        found = False
        for msg in reversed(user_messages):
            if field.type == "select" and field.options:
                for opt in field.options:
                    msg_norm = _normalize(msg)
                    opt_norm = _normalize(opt)
                    if opt_norm in msg_norm or msg_norm in opt_norm:
                        result[field.key] = opt
                        found = True
                        break
            elif field.type == "number":
                # Only extract if message is numeric (or the word "một" etc.)
                stripped = msg.strip()
                if stripped.isdigit() or stripped.replace(",", "").replace(".", "").isdigit():
                    result[field.key] = stripped
                    found = True
                    break
            else:
                result[field.key] = msg.strip()
                found = True
                break
        if not found and field.default:
            result[field.key] = field.default

    return result


def _normalize(text: str) -> str:
    import unicodedata

    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(
        c for c in decomposed if unicodedata.category(c) != "Mn"
    ).replace("đ", "d")
