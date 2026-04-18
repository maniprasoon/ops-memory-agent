from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx
import uvicorn

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
AGENT_DIR = REPO_ROOT / "agent"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(AGENT_DIR))

from agent import configure_logging, run_incident_agent, search_past_incidents  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services.memory import get_hindsight_client, recall_memories, save_memory  # noqa: E402
from hindsight_client import Hindsight as HindsightClient  # noqa: E402

logger = logging.getLogger("integration_tests")


@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str


def run_test(name: str, func: Callable[[], str]) -> TestResult:
    try:
        detail = func()
        print(f"PASS {name}: {detail}")
        return TestResult(name=name, passed=True, detail=detail)
    except Exception as exc:  # noqa: BLE001 - integration runner must report exact failures.
        detail = f"{type(exc).__name__}: {exc}"
        print(f"FAIL {name}: {detail}")
        return TestResult(name=name, passed=False, detail=detail)


def test_hindsight_auth() -> str:
    settings = get_settings()
    client = HindsightClient(
        base_url=settings.hindsight_base_url,
        api_key=settings.hindsight_api_key.get_secret_value(),
    )
    bank_id = "integration-auth-check"
    try:
        client.create_bank(bank_id=bank_id, name="Integration Auth Check")
    except Exception as exc:  # noqa: BLE001 - already exists still proves auth reached API.
        if "already" not in str(exc).lower() and "exist" not in str(exc).lower():
            raise
    return f"HindsightClient authenticated; bank probe={bank_id}"


def test_save_memory() -> str:
    memory_id = asyncio.run(
        save_memory(
            "default",
            (
                "Test incident: database connection error from integration check. "
                "Resolution: reduce pool pressure and recycle idle sessions."
            ),
        )
    )
    if not memory_id:
        raise AssertionError("save_memory returned an empty memory ID")
    return f"save_memory returned {memory_id}"


def test_recall_memories() -> str:
    memories = asyncio.run(recall_memories("database connection error", top_k=5))
    if len(memories) < 1:
        raise AssertionError("recall_memories returned 0 results")
    return f"recall_memories returned {len(memories)} result(s)"


def start_server() -> tuple[uvicorn.Server, threading.Thread, str]:
    config = uvicorn.Config(
        "app.main:app",
        host="127.0.0.1",
        port=8765,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = "http://127.0.0.1:8765"
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            response = httpx.get(f"{base_url}/api/health", timeout=2.0)
            if response.status_code == 200:
                return server, thread, base_url
        except httpx.HTTPError:
            time.sleep(0.25)
    raise RuntimeError("FastAPI server did not become ready within 20 seconds")


SERVER_STATE: dict[str, object] = {}


def test_fastapi_health() -> str:
    server, thread, base_url = start_server()
    SERVER_STATE.update({"server": server, "thread": thread, "base_url": base_url})
    response = httpx.get(f"{base_url}/api/health", timeout=5.0)
    if response.status_code != 200:
        raise AssertionError(f"GET /api/health returned {response.status_code}: {response.text}")
    return f"GET /api/health returned {response.status_code}"


def test_chat_endpoint() -> str:
    base_url = str(SERVER_STATE["base_url"])
    response = httpx.post(
        f"{base_url}/api/chat",
        json={"session_id": "test-001", "message": "database connection error"},
        timeout=60.0,
    )
    if response.status_code != 200:
        raise AssertionError(f"POST /api/chat returned {response.status_code}: {response.text}")
    payload = response.json()
    if "memories_recalled" not in payload:
        raise AssertionError(f"response missing memories_recalled: {json.dumps(payload)[:800]}")
    return f"POST /api/chat returned memories_recalled={len(payload['memories_recalled'])}"


def test_seed_script() -> str:
    from scripts.seed_memory import INCIDENTS, seed_incidents, verify_seed

    seed_incidents()
    verify_seed()
    if len(INCIDENTS) != 30:
        raise AssertionError(f"seed script contains {len(INCIDENTS)} incidents instead of 30")
    return "seed script saved and verified 30 incidents"


def test_full_agent() -> str:
    tool_output = search_past_incidents.invoke("API timeout spike")
    if "Past incident" not in str(tool_output):
        raise AssertionError("search_past_incidents did not return past incidents")

    output = run_incident_agent(
        "Production alert: API timeout spike. What have we seen before?",
        max_retries=2,
    )
    if "could not complete" in output.lower():
        raise AssertionError(output)
    if not re.search(r"past incident|inc-[a-z0-9-]+|incident_id", output, re.IGNORECASE):
        raise AssertionError(f"agent response did not cite a past incident: {output[:1000]}")
    return f"agent cited a past incident; response preview={output[:240]}"


def shutdown_server() -> None:
    server = SERVER_STATE.get("server")
    thread = SERVER_STATE.get("thread")
    if isinstance(server, uvicorn.Server):
        server.should_exit = True
    if isinstance(thread, threading.Thread):
        thread.join(timeout=5)


def main() -> int:
    configure_logging()
    tests: list[tuple[str, Callable[[], str]]] = [
        ("1. HindsightClient import/auth", test_hindsight_auth),
        ("2. save_memory returns memory ID", test_save_memory),
        ("3. recall_memories database query", test_recall_memories),
        ("4. FastAPI GET /api/health", test_fastapi_health),
        ("5. FastAPI POST /api/chat memories_recalled", test_chat_endpoint),
        ("6. seed_memory saves 30 incidents", test_seed_script),
        ("7. full agent searches and cites past incident", test_full_agent),
    ]

    results: list[TestResult] = []
    try:
        for name, func in tests:
            results.append(run_test(name, func))
    finally:
        shutdown_server()

    print("\nSUMMARY")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}: {result.detail}")

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
