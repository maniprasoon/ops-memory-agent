import asyncio
import re
import time
import uuid
from functools import lru_cache
from typing import Any

from hindsight_client import Hindsight as HindsightClient

from app.core.config import get_settings


def get_hindsight_client() -> HindsightClient:
    """Initialize a Hindsight client from HINDSIGHT_API_KEY.

    The SDK owns an aiohttp session internally, so each worker/thread should use
    a fresh client instead of sharing a cached instance across event loops.
    """

    settings = get_settings()
    return HindsightClient(
        base_url=settings.hindsight_base_url,
        api_key=settings.hindsight_api_key.get_secret_value(),
    )


def _bank_id(session_id: str) -> str:
    safe_session_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", session_id.strip()).strip("-").lower()
    return f"session-{safe_session_id or 'default'}"


def _extract_memory_text(memory: Any) -> str | None:
    text = getattr(memory, "text", None)
    if isinstance(text, str):
        return text

    if isinstance(memory, dict):
        value = memory.get("text") or memory.get("content")
        return value if isinstance(value, str) else None

    value = str(memory).strip()
    return value or None


def _ensure_bank(session_id: str) -> None:
    bank_id = _bank_id(session_id)

    try:
        get_hindsight_client().create_bank(bank_id=bank_id, name=f"Session {session_id}")
    except Exception:
        # Hindsight returns an error when the bank already exists. Retain/recall below
        # will surface genuine connectivity or auth failures.
        return


def _with_retries(operation: str, fn: Any, *, attempts: int = 3) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - provider failures need retry context.
            last_error = exc
            if attempt < attempts:
                time.sleep(1.5 * attempt)
    raise RuntimeError(f"Hindsight {operation} failed after {attempts} attempts: {last_error}") from last_error


def _retain_error_may_have_committed(exc: Exception) -> bool:
    message = str(exc).lower()
    return "out of shared memory" in message and "max_locks_per_transaction" in message


async def save_memory(session_id: str, content: str) -> str:
    """Persist an exchange or fact to Hindsight for the given session and return its ID."""

    bank_id = _bank_id(session_id)
    memory_id = f"mem-{uuid.uuid4().hex[:12]}"
    memory_content = f"memory_id: {memory_id}\n{content}"

    def retain() -> None:
        _ensure_bank(session_id)
        try:
            _with_retries(
                "retain",
                lambda: get_hindsight_client().retain(
                    bank_id=bank_id,
                    content=memory_content,
                    context="ops-memory-agent chat exchange",
                ),
                attempts=1,
            )
        except Exception as exc:
            if _retain_error_may_have_committed(exc):
                return
            raise

    await asyncio.to_thread(retain)
    return memory_id


async def recall_memories(query: str, top_k: int = 5, *, session_id: str = "default") -> list[str]:
    """Recall relevant Hindsight memories for a query."""

    bank_id = _bank_id(session_id)

    def recall() -> list[str]:
        def parse_result(result: Any) -> list[str]:
            raw_results = getattr(result, "results", result)
            if raw_results is None:
                return []

            parsed: list[str] = []
            for item in list(raw_results)[:top_k]:
                text = _extract_memory_text(item)
                if text:
                    parsed.append(text)
            return parsed

        try:
            result = _with_retries(
                "recall",
                lambda: get_hindsight_client().recall(bank_id=bank_id, query=query),
            )
            memories = parse_result(result)
        except Exception:
            memories = []

        if not memories and session_id != "incident-response":
            # Fall back to the incident-response bank so general chat can use the
            # seeded runbook memories when the session-specific bank is empty.
            try:
                result = _with_retries(
                    "recall",
                    lambda: get_hindsight_client().recall(
                        bank_id="incident-response",
                        query=query,
                    ),
                )
                memories = parse_result(result)
            except Exception:
                return []

        return memories

    return await asyncio.to_thread(recall)
