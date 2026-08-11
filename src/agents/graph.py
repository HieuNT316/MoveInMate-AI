"""`chat_graph` — docs/architecture_diagram.md mục 3.4.

Hình dạng GATE 2: hai node, không nhánh FAQ (`faq_lookup` hoãn sang W4).
Checklist không đi qua LangGraph — đây là graph duy nhất của hệ thống.
"""

from langgraph.graph import END, StateGraph

from src.agents.nodes.generate import generate_node
from src.agents.nodes.rag_retrieve import rag_retrieve_node
from src.agents.state import ChatState


def build_chat_graph() -> StateGraph:
    graph = StateGraph(ChatState)
    graph.add_node("rag_retrieve", rag_retrieve_node)
    graph.add_node("generate", generate_node)
    graph.set_entry_point("rag_retrieve")
    graph.add_edge("rag_retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


chat_graph = build_chat_graph()
