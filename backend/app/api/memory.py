from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.memory import recall_memories, save_memory

router = APIRouter()


class SaveMemoryRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=12000)


class RecallMemoryRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=1, max_length=8000)
    top_k: int = Field(default=5, ge=1, le=20)


class RecallMemoryResponse(BaseModel):
    memories: list[str]


class SaveMemoryResponse(BaseModel):
    memory_id: str


@router.post("/memory", response_model=SaveMemoryResponse)
async def save_memory_endpoint(request: SaveMemoryRequest) -> SaveMemoryResponse:
    memory_id = await save_memory(request.session_id, request.content)
    return SaveMemoryResponse(memory_id=memory_id)


@router.post("/memory/recall", response_model=RecallMemoryResponse)
async def recall_memory_endpoint(request: RecallMemoryRequest) -> RecallMemoryResponse:
    memories = await recall_memories(
        request.query,
        top_k=request.top_k,
        session_id=request.session_id,
    )
    return RecallMemoryResponse(memories=memories)
