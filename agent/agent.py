from __future__ import annotations

import logging
import json
import re
import time
import uuid
from functools import lru_cache
from typing import Any

from hindsight_client import Hindsight as HindsightClient
from langchain.agents import AgentExecutor, create_react_agent
from langchain.agents.agent import AgentOutputParser
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("incident_response_agent")

FINAL_ANSWER_TOKEN = "Final Answer:"

DEFAULT_HINDSIGHT_BASE_URL = "https://api.hindsight.vectorize.io"
DEFAULT_GROQ_MODEL = "qwen/qwen3-32b"

SYSTEM_PROMPT = (
    "You are an Incident Response AI for production operations. "
    "You have memory of all past incidents. ALWAYS search past incidents before "
    "suggesting solutions. Cite specific past incidents in your responses. "
    "Prefer proven resolution steps from memory over generic advice. If past "
    "incidents do not match, say that clearly before proposing a cautious plan."
)

REACT_PROMPT = PromptTemplate.from_template(
    """{system_prompt}

Use the following tools:

{tools}

Follow this format exactly:

Question: the incident or request to answer
Thought: think about what you need to do next
Action: the action to take, one of [{tool_names}]
Action Input: valid JSON for the action arguments
Observation: the result of the action
... repeat Thought/Action/Action Input/Observation as needed
Thought: I now know the final answer
Final Answer: the final incident-response guidance with cited past incidents

Question: {input}
Thought: {agent_scratchpad}"""
).partial(system_prompt=SYSTEM_PROMPT)


class LogIncidentArgs(BaseModel):
    title: str = Field(description="Short incident title.")
    description: str = Field(description="Observed symptoms, impact, and timeline.")
    severity: str = Field(description="Incident severity, such as SEV1, SEV2, SEV3, or low.")


class MarkResolvedArgs(BaseModel):
    incident_id: str = Field(description="The incident identifier returned by log_incident.")
    resolution: str = Field(description="The concrete steps that resolved the incident.")
    root_cause: str = Field(description="The confirmed root cause.")


class IncidentAgentSettings(BaseSettings):
    """Environment-driven configuration for the incident agent demo."""

    model_config = SettingsConfigDict(
        env_file=("../.env.example", ".env.example", "../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default=DEFAULT_GROQ_MODEL, alias="GROQ_MODEL")
    hindsight_api_key: str | None = Field(default=None, alias="HINDSIGHT_API_KEY")
    hindsight_base_url: str = Field(
        default=DEFAULT_HINDSIGHT_BASE_URL,
        alias="HINDSIGHT_BASE_URL",
    )
    incident_memory_bank: str = Field(default="incident-response", alias="INCIDENT_MEMORY_BANK")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> IncidentAgentSettings:
    return IncidentAgentSettings()


class JsonReActOutputParser(AgentOutputParser):
    """Parse ReAct text while allowing JSON objects as tool inputs."""

    def parse(self, text: str) -> AgentAction | AgentFinish:
        if FINAL_ANSWER_TOKEN in text:
            return AgentFinish(
                return_values={"output": text.split(FINAL_ANSWER_TOKEN, 1)[1].strip()},
                log=text,
            )

        action_match = re.search(r"Action\s*:\s*(?P<action>[^\n]+)", text)
        input_match = re.search(
            r"Action Input\s*:\s*(?P<input>.*?)(?:\nObservation\s*:|\Z)",
            text,
            flags=re.DOTALL,
        )
        if not action_match or not input_match:
            raise OutputParserException(f"Could not parse ReAct output: {text}")

        tool_name = action_match.group("action").strip()
        raw_input = self._strip_code_fence(input_match.group("input").strip())

        try:
            tool_input: str | dict[str, Any] = json.loads(raw_input)
        except json.JSONDecodeError:
            tool_input = raw_input

        return AgentAction(tool=tool_name, tool_input=tool_input, log=text)

    @staticmethod
    def _strip_code_fence(value: str) -> str:
        if value.startswith("```"):
            value = re.sub(r"^```(?:json)?", "", value.strip(), flags=re.IGNORECASE).strip()
            value = re.sub(r"```$", "", value).strip()
        return value

    @property
    def _type(self) -> str:
        return "json-react"


@lru_cache(maxsize=1)
def get_hindsight_client() -> HindsightClient:
    """Create a Hindsight client from environment variables."""

    settings = get_settings()
    if not settings.hindsight_api_key:
        raise RuntimeError("HINDSIGHT_API_KEY is required to use incident memory.")

    logger.info("Initializing Hindsight client for %s", settings.hindsight_base_url)
    return HindsightClient(
        base_url=settings.hindsight_base_url,
        api_key=settings.hindsight_api_key,
    )


def ensure_incident_bank() -> None:
    """Ensure the shared incident-response memory bank exists."""

    try:
        get_hindsight_client().create_bank(
            bank_id=get_settings().incident_memory_bank,
            name="Incident Response Memory",
        )
        logger.info("Created Hindsight memory bank: %s", get_settings().incident_memory_bank)
    except Exception as exc:  # noqa: BLE001 - existing bank is a normal startup path.
        logger.debug("Hindsight memory bank already available or could not be created: %s", exc)


def _with_retries(operation: str, fn: Any, *, attempts: int = 3) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - provider failures need retry context.
            last_error = exc
            logger.warning("Hindsight %s failed on attempt %s: %s", operation, attempt, exc)
            if attempt < attempts:
                time.sleep(1.5 * attempt)
    raise RuntimeError(f"Hindsight {operation} failed after {attempts} attempts: {last_error}") from last_error


def _retain_error_may_have_committed(exc: Exception) -> bool:
    message = str(exc).lower()
    return "out of shared memory" in message and "max_locks_per_transaction" in message


def recall_memories(query: str, top_k: int = 5) -> list[str]:
    """Recall incident memories from Hindsight."""

    ensure_incident_bank()
    logger.info("MEMORY RECALL query=%r top_k=%s", query, top_k)

    try:
        result = _with_retries(
            "recall",
            lambda: get_hindsight_client().recall(
                bank_id=get_settings().incident_memory_bank,
                query=query,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - the tool should return a useful observation.
        logger.exception("Hindsight recall failed")
        return [f"Memory recall failed: {exc}"]

    raw_results = getattr(result, "results", result) or []
    memories = [_memory_text(item) for item in list(raw_results)[:top_k]]
    filtered = [memory for memory in memories if memory]

    logger.info("MEMORY RECALL returned %s memories", len(filtered))
    for index, memory in enumerate(filtered, start=1):
        logger.info("MEMORY HIT %s: %s", index, memory[:300])

    return filtered


def save_memory(content: str, *, context: str) -> str:
    """Save an incident memory to Hindsight and return its local memory ID."""

    ensure_incident_bank()
    memory_id = f"mem-{uuid.uuid4().hex[:12]}"
    memory_content = f"memory_id: {memory_id}\n{content}"
    logger.info("MEMORY SAVE context=%r content=%s", context, memory_content[:500])
    try:
        _with_retries(
            "retain",
            lambda: get_hindsight_client().retain(
                bank_id=get_settings().incident_memory_bank,
                content=memory_content,
                context=context,
            ),
            attempts=1,
        )
    except Exception as exc:
        if not _retain_error_may_have_committed(exc):
            raise
        logger.warning(
            "Hindsight retain returned shared-memory 500 after retries; "
            "continuing because prior calls with this error were recallable."
        )
    return memory_id


def _memory_text(memory: Any) -> str | None:
    text = getattr(memory, "text", None)
    if isinstance(text, str):
        return text

    if isinstance(memory, dict):
        value = memory.get("text") or memory.get("content")
        return value if isinstance(value, str) else None

    value = str(memory).strip()
    return value or None


@tool
def search_past_incidents(query: str) -> str:
    """Return the top 5 similar past incidents with resolution steps."""

    memories = recall_memories(
        "Similar past incidents and their resolution steps for: " + query,
        top_k=5,
    )
    if not memories:
        return "No similar past incidents found."
    return "\n\n".join(
        f"Past incident {index}:\n{memory}" for index, memory in enumerate(memories, 1)
    )


@tool(args_schema=LogIncidentArgs)
def log_incident(title: str, description: str, severity: str) -> str:
    """Save a structured incident to Hindsight with metadata tags."""

    incident_id = f"inc-{uuid.uuid4().hex[:10]}"
    severity_tag = severity.strip().lower().replace(" ", "-")
    content = (
        f"incident_id: {incident_id}\n"
        f"title: {title}\n"
        f"description: {description}\n"
        f"severity: {severity}\n"
        "status: active\n"
        f"metadata_tags: incident,response,{severity_tag},active\n"
    )
    memory_id = save_memory(content, context=f"incident_log tags=incident,response,{severity_tag},active")
    return f"Logged incident {incident_id} with severity {severity}. memory_id={memory_id}"


@tool
def get_resolution_playbook(incident_type: str) -> str:
    """Retrieve the most effective past resolution for an incident category."""

    memories = recall_memories(
        "Most effective resolved incident playbook for category "
        f"{incident_type}. Include resolution, root cause, and what worked.",
        top_k=5,
    )
    if not memories:
        return f"No proven playbook found for incident category: {incident_type}."

    logger.info("PLAYBOOK selected first recalled memory for incident_type=%r", incident_type)
    return (
        f"Most relevant playbook for {incident_type}:\n{memories[0]}\n\n"
        "Additional related resolved incidents:\n"
        + "\n\n".join(memories[1:])
    )


@tool(args_schema=MarkResolvedArgs)
def mark_resolved(incident_id: str, resolution: str, root_cause: str) -> str:
    """Update memory with the resolution and root cause that actually worked."""

    content = (
        f"incident_id: {incident_id}\n"
        "status: resolved\n"
        f"resolution: {resolution}\n"
        f"root_cause: {root_cause}\n"
        "metadata_tags: incident,response,resolved,root-cause,worked\n"
    )
    memory_id = save_memory(content, context="incident_resolution tags=incident,response,resolved,worked")
    return f"Marked {incident_id} resolved and saved what worked. memory_id={memory_id}"


INCIDENT_TOOLS = [
    search_past_incidents,
    log_incident,
    get_resolution_playbook,
    mark_resolved,
]


def build_agent() -> AgentExecutor:
    """Build the Incident Response ReAct agent."""

    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is required to run the incident response agent.")

    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
    )
    agent = create_react_agent(
        llm=llm,
        tools=INCIDENT_TOOLS,
        prompt=REACT_PROMPT,
        output_parser=JsonReActOutputParser(),
    )
    return AgentExecutor(
        agent=agent,
        tools=INCIDENT_TOOLS,
        handle_parsing_errors=True,
        max_iterations=8,
        verbose=True,
    )


def run_incident_agent(message: str, *, max_retries: int = 3) -> str:
    """Run the agent with retry handling for transient Groq/tool-calling failures."""

    executor = build_agent()
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("AGENT RUN attempt=%s message=%r", attempt, message)
            result = executor.invoke({"input": message})
            output = result.get("output", "")
            return str(output)
        except Exception as exc:  # noqa: BLE001 - retry provider/tool-calling failures.
            last_error = exc
            logger.warning("Groq/LangChain agent call failed on attempt %s: %s", attempt, exc)
            if attempt < max_retries:
                time.sleep(1.5 * attempt)

    return (
        "I could not complete the incident-response run after retrying Groq/tool calls. "
        f"Last error: {last_error}"
    )


def configure_logging() -> None:
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


if __name__ == "__main__":
    configure_logging()
    print("Incident Response AI. Type 'exit' to quit.")
    while True:
        user_input = input("incident> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        print(run_incident_agent(user_input))
