from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.groq import GroqChatMessage, complete_chat
from app.services.memory import recall_memories, save_memory

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    session_id: str
    response: str
    memories_recalled: list[str]
    saved_memory_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Answer a chat message using recalled session memories as durable context."""

    memories = await recall_memories(request.message, session_id=request.session_id, top_k=5)
    memory_context = "\n".join(f"- {memory}" for memory in memories) or "No prior memories found."

    system_prompt = (
        "You are Ops Memory Agent, a precise operations assistant. Use recalled memories "
        "when they are relevant, but do not invent facts. If memory conflicts with the "
        "latest user message, prefer the latest user message and mention the conflict.\n\n"
        f"Recalled memories for session {request.session_id}:\n{memory_context}"
    )

    try:
        response = await complete_chat(
            [
                GroqChatMessage(role="system", content=system_prompt),
                GroqChatMessage(role="user", content=request.message),
            ]
        )
    except Exception as exc:  # noqa: BLE001 - convert provider failures into an API error.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq completion failed: {exc}",
        ) from exc

    try:
        saved_memory_id = await save_memory(
            request.session_id,
            f"User: {request.message}\nAssistant: {response}",
        )
    except Exception as exc:  # noqa: BLE001 - do not fail a completed chat response.
        saved_memory_id = f"save_failed: {exc}"
    return ChatResponse(
        session_id=request.session_id,
        response=response,
        memories_recalled=memories,
        saved_memory_id=saved_memory_id,
    )
