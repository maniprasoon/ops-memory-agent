import httpx
from pydantic import BaseModel

from app.core.config import get_settings


class GroqChatMessage(BaseModel):
    role: str
    content: str


async def complete_chat(messages: list[GroqChatMessage]) -> str:
    """Call Groq's OpenAI-compatible chat completions endpoint."""

    settings = get_settings()
    payload = {
        "model": settings.groq_model,
        "messages": [message.model_dump() for message in messages],
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key.get_secret_value()}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Groq returned an empty response")
    return content.strip()

