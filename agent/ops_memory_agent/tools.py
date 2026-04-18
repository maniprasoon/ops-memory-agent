import httpx
from langchain_core.tools import tool

from ops_memory_agent.config import get_agent_settings


@tool
def recall_session_memories(session_id: str, query: str) -> str:
    """Recall useful Hindsight memories for a session."""

    settings = get_agent_settings()
    response = httpx.post(
        f"{settings.backend_url}/api/memory/recall",
        json={"session_id": session_id, "query": query, "top_k": 5},
        timeout=45.0,
    )
    response.raise_for_status()
    memories = response.json()["memories"]
    return "\n".join(f"- {memory}" for memory in memories) or "No memories found."


@tool
def save_session_memory(session_id: str, content: str) -> str:
    """Save an operational fact by sending it through the backend memory pipeline."""

    settings = get_agent_settings()
    response = httpx.post(
        f"{settings.backend_url}/api/memory",
        json={"session_id": session_id, "content": content},
        timeout=45.0,
    )
    response.raise_for_status()
    return "Saved memory through the backend."


MEMORY_TOOLS = [recall_session_memories, save_session_memory]
