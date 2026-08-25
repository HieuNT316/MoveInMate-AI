"""`chat_graph` — docs/architecture_diagram.md mục 3.4.

```
rewrite_query ──► faq_lookup ──khớp FAQ──────────────────────► END
                       │
                       └──không khớp──► rag_retrieve ──► generate ──► END
```

`rewrite_query` viết lại câu hỏi tiếp nối thành câu độc lập ngữ cảnh; cả
`faq_lookup` lẫn `rag_retrieve` đều dùng bản viết lại đó.

`faq_lookup` (US-09, bật 25/08) đứng trước `rag_retrieve` vì câu đã có người
soạn sẵn đáp án thì không cần tra tài liệu. Khớp rồi thì đi thẳng tới END —
không qua `generate`, vì câu trả lời đã là câu chữ BQL duyệt, đưa cho LLM viết
lại chỉ thêm một cơ hội bịa.

Checklist không đi qua LangGraph — đây là graph duy nhất của hệ thống.
"""

from langgraph.graph import END, StateGraph

from src.agents.nodes.faq_lookup import faq_lookup_node
from src.agents.nodes.generate import generate_node
from src.agents.nodes.rag_retrieve import rag_retrieve_node
from src.agents.nodes.rewrite_query import rewrite_query_node
from src.agents.state import ChatState


def _after_faq(state: ChatState) -> str:
    """Khớp FAQ thì xong; không thì đi tiếp đường RAG như cũ."""
    return "done" if state.get("answer_source") == "faq" else "rag"


def build_chat_graph() -> StateGraph:
    graph = StateGraph(ChatState)
    graph.add_node("rewrite_query", rewrite_query_node)
    graph.add_node("faq_lookup", faq_lookup_node)
    graph.add_node("rag_retrieve", rag_retrieve_node)
    graph.add_node("generate", generate_node)
    graph.set_entry_point("rewrite_query")
    graph.add_edge("rewrite_query", "faq_lookup")
    graph.add_conditional_edges(
        "faq_lookup", _after_faq, {"done": END, "rag": "rag_retrieve"}
    )
    graph.add_edge("rag_retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


chat_graph = build_chat_graph()
