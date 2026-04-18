# 🧠 Ops Memory Agent

**Ops Memory Agent** is an advanced, memory-backed AI operations assistant designed specifically for DevOps and Site Reliability Engineering (SRE) teams. 

Unlike traditional chat assistants that "forget" previous incidents as soon as you close the browser, this agent is deeply integrated with the **Hindsight Memory Database**. It continuously retains critical context, decisions, and root causes from production outages, making it an invaluable teammate during high-stress operational events.

---

## 🛠️ Technology Stack
This application is designed as a highly scalable monorepo comprising three core pillars:

1. **Frontend (Next.js 14 & Turbopack):** A lightning-fast React application built with Tailwind CSS and `shadcn/ui`. It provides an immersive "Ops Room" UI, including active incident routing, real-time memory bank status, and similarity clusters.
2. **Backend Engine (FastAPI & Python 3.11):** An asynchronous API wrapper that bridges the gap between the user interface, the memory database, and the LLM inference engine. 
3. **Agent Loop (LangChain & Groq):** Powered by the incredibly fast `qwen/qwen3-32b` model running on Groq hardware. This LangChain ReAct agent orchestrates tool calls to query the Hindsight DB before it even answers your prompt!

---

## 🚀 Key Features

* **Persistent Shared Memory:** Every "Aha!" moment, root-cause discovery, or architectural decision made in the chat is securely saved to the backing Hindsight vector database.
* **Context Injection:** When an engineer queries the agent about a new outage (e.g., "The user-db is timing out"), the backend autonomously scrapes the `incident-response` memory bank for conceptually similar historical events and seamlessly injects them into the prompt.
* **Automated Data Pipeline:** Eliminates manual data entry. Production telemetry, chat logs, and incident post-mortems can be dumped via API and ingested instantly.
* **Aggressive Caching:** We heavily utilize Python `@lru_cache` and automated socket optimizations to ensure sub-second response times during catastrophic network events.

---

## 💡 Primary Use Cases

### 1. On-Call Triaging System
When a P1 alert triggers at 3:00 AM, engineers are often groggy and overwhelmed. By pasting the raw alert into the Ops Memory Agent, it instantly contextualizes the error against the company's historical footprint. It moves the team past the "What is happening?" phase directly to the "How do we fix this?" phase.

### 2. Elimination of Siloed Knowledge 
Senior engineers often act as walking encyclopedias for fragile, legacy systems. Ops Memory Agent democratizes this knowledge. If a senior engineer resolves a weird database pool exhaustion error, their fix is permanently captured. Next month, a junior engineer encountering the same error will be instantly handed the exact resolution steps.

### 3. Automated Post-Mortem Generation
Because the agent "remembers" the entire lifecycle of an incident discussion—from initial confusion to eventual database migration—teams can recall full conversation histories to draft rigorous SOC-2 compliant post-mortems with zero manual tracing.

### 4. Interactive Standard Operating Procedures (SOPs)
Static Wiki pages decay instantly. Instead of maintaining dusty Runbooks, teams "talk" to the memory agent. It acts as a highly dynamic, living handbook that actively reasons over the company's past scaling issues and third-party failures.

##Production-oriented monorepo for a memory-backed operations assistant.

- `frontend`: Next.js 14 App Router, Tailwind CSS, shadcn/ui-style components
- `backend`: FastAPI on Python 3.11 with async endpoints
- `agent`: LangChain agent loop and memory tool definitions
- Memory: Hindsight via `HINDSIGHT_API_KEY`
- Chat model: Groq OpenAI-compatible API using `qwen/qwen3-32b`

## Prerequisites

- Docker and Docker Compose
- Hindsight Cloud API key, or a self-hosted Hindsight API URL
- Groq API key

## Setup

1. Copy environment variables:

```bash
cp .env.example .env
```

The Python services also read `.env.example` as a fallback for local demos, but
`.env` should be used for real secrets and overrides.

2. Fill in:

```bash
HINDSIGHT_API_KEY=...
GROQ_API_KEY=...
```

`HINDSIGHT_BASE_URL` defaults to `https://api.hindsight.vectorize.io`. For a local Hindsight server, set it to `http://localhost:8888` outside Docker or to a reachable container hostname inside Docker.

3. Start the stack:

```bash
docker compose up --build
```

4. Open the app:

```text
http://localhost:3000
```

The backend is available at `http://localhost:8000`.

## API

### `POST /api/chat`

Request:

```json
{
  "session_id": "ops-room-1",
  "message": "What did we decide about the database migration?"
}
```

Response:

```json
{
  "session_id": "ops-room-1",
  "response": "..."
}
```

The endpoint recalls relevant Hindsight memories for the session, injects them into the system prompt, calls Groq, saves the exchange back to Hindsight, and returns the assistant response.

### `POST /api/memory`

Stores a memory for a session.

### `POST /api/memory/recall`

Recalls memories for `{ "session_id": "...", "query": "...", "top_k": 5 }`.

## Local Development & Execution

**1. Virtual Environment Setup (Root Directory)**
Create and activate a single virtual environment at the root of the repository, then install all project dependencies from `requirements.txt`:

```bash
cd ops-memory-agent
py -m venv .venv
.\.venv\Scripts\activate   # (On Windows)
# source .venv/bin/activate # (On Mac/Linux)
pip install -r requirements.txt
```

**2. Start the Backend API (Terminal 1)**
With the virtual environment activated:
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**3. Start the Frontend & Auto-Seed Memory (Terminal 2)**
Open a new terminal, activate the same `.venv`, and start the Next.js app. Our package scripts will automatically seed exactly 50 incidents into your Hindsight memory under the hood!

```bash
cd frontend
..\.venv\Scripts\activate  # (On Windows)
npm install
npm run dev
```

The app will be available at `http://localhost:3000`.

Incident Response AI (CLI Agent):

```bash
cd agent
python agent.py
```

The incident agent uses `INCIDENT_MEMORY_BANK=incident-response` by default. Its tools log every Hindsight recall and retain operation so demos show when memory is being used.

## Demo Testing Scenarios
You can use these exact prompts in the `/chat` route to demonstrate the agent's incident recall capabilities successfully.

**Scenario 1: Database Pool Exhaustion**
> "We are getting P1 alerts right now. The `orders-service` and `api-gateway` are timing out across us-east-1. The Postgres logs are saying `remaining connection slots are reserved for non-replication superuser`. Have we seen this before and what was the fix?"

**Scenario 2: Redis Eviction Error**
> "Users are complaining about duplicate payment charges. We checked the logs and found `IdempotencyKeyMissingError: key checkout:idem:pay_7781 not found`. Redis memory is sitting at 97%. What happened last time this occurred?"

**Scenario 3: Complex Outage**
> "The `inventory-service` is returning completely frozen, stale stock numbers. I am seeing `SQLSTATE[HY000] [2006] MySQL server has gone away` in the logs. How do we mitigate this rapidly?"

## Notes

- Each `session_id` maps to a Hindsight memory bank.
- Memory calls are wrapped in `backend/app/services/memory.py` so application code does not depend directly on SDK response shapes.
- The LangChain agent in `/agent` uses backend HTTP tools by default, keeping Hindsight and Groq credentials centralized in `/backend`.
