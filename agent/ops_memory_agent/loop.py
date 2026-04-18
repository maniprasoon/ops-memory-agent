from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from ops_memory_agent.config import get_agent_settings
from ops_memory_agent.tools import MEMORY_TOOLS


def build_agent() -> AgentExecutor:
    """Build a LangChain agent with memory tools backed by the FastAPI service."""

    settings = get_agent_settings()
    llm = ChatGroq(
        api_key=settings.groq_api_key.get_secret_value(),
        model=settings.groq_model,
        temperature=0.2,
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are Ops Memory Agent. Use memory tools when prior decisions, "
                "preferences, incident context, or durable facts would improve the answer.",
            ),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    agent = create_tool_calling_agent(llm, MEMORY_TOOLS, prompt)
    return AgentExecutor(agent=agent, tools=MEMORY_TOOLS, verbose=True)


def run_once(message: str) -> str:
    result = build_agent().invoke({"input": message})
    return str(result["output"])


if __name__ == "__main__":
    while True:
        user_input = input("ops-memory-agent> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        print(run_once(user_input))

