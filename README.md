# Project Structure

- CLAUDE.md and SPEC.md — at root level, not in any folder. These are the two files that define the entire project before any code is written. CLAUDE.md is permanent project memory for Claude Code. SPEC.md is the blueprint for what we're building. Root level means they're the first thing anyone sees when they open the project.

- backend/ — everything that runs on the server. The user never touches this directly. It processes data, runs the AI agents, talks to the database, and exposes APIs. We separate backend from frontend because they're independent systems — the backend could serve a mobile app tomorrow without changing a line.

- backend/agents/ — the heart of the project. This is where all 5 LangGraph agents live, plus the shared state definition and the graph assembly. Every AI decision in the system happens inside this folder. Keeping agents isolated in their own folder means each one can be read, tested, and improved independently without touching anything else.

- backend/api/ — the door between the outside world and the agents. FastAPI lives here. It receives HTTP requests from the frontend, hands them to the agent graph, and streams responses back via SSE. It knows nothing about AI — it just routes traffic. That separation is intentional.

- backend/rag/ — RAG stands for Retrieval Augmented Generation. This folder handles the knowledge base — seeding pgvector with tax rules, IRC sections, and AMT thresholds. It's separate from agents because seeding the knowledge base is a one-time setup task, not something that runs on every request. Conceptually different responsibility, so different folder.

- frontend/ — everything the user sees and interacts with. Completely separate from backend. Talks to the backend only through the API contracts defined in SPEC.md. If you swap the backend from Python to Node tomorrow, the frontend doesn't change at all.

- frontend/src/components/ — React UI components. The graph visualiser that lights up as agents run, the human review modal that appears on interrupt, the report renderer. Each component does one visual thing and nothing else.

- frontend/src/hooks/ — React hooks. Custom logic that connects the UI to the backend. The useAgentStream hook lives here — it manages the SSE connection, receives agent events, and gives components the live data they need to render. Hooks are separate from components because logic and presentation should never be mixed.

- tests/ — one test file per agent. Lives at the root level, not inside backend, because tests are not part of the application — they verify it. In the interview, this folder signals that you built this properly. 92% coverage on your resume isn't a coincidence — it's a habit.

- .ai/ — supporting reference material. Research notes, saved prompts that worked well, architectural decisions you made and why. Claude Code doesn't read this automatically — it's for you. During the interview you can open this and say "here's where I documented my architectural decisions while building."

# Markdown file(s)

## Claude.md

- CLAUDE.md is essentially answering one question: "What does Claude Code need to know to work on this project without me explaining anything?"
- Claude Code reads this document at the start of every single session. I structured it in 6 sections, each solving a specific problem:

1. **What this project is**
2. **Tech stack**
3. **Domain glossary** : This is the most important section for this specific project. ISO, NSO, AMT, FMV, strike price — these are domain-specific terms that have very precise meanings in equity compensation. If Claude Code doesn't know that AMT means Alternative Minimum Tax triggered by ISO exercise, it will write vague, incorrect financial logic. The glossary makes Claude Code speak the same language as the domain.
4. **Architecture** : This tells Claude Code the exact shape of the system — 6 agents, in this order, doing these specific jobs. Without this, if you ask it to "implement the risk analyst", it has no idea where that fits in the bigger picture. With this, it knows the risk analyst comes after RAG research and before strategy, and it'll write code that fits that pipeline correctly.
5. **Shared state** : This is a hard constraint. In a LangGraph system, all agents communicate through a single shared AgentState object. If Claude Code doesn't know this rule, it might write an agent that returns a completely different shape — breaking the entire graph. This section prevents that by making the constraint explicit.
6. **Coding conventions**

## Spec.md

- Since it's a greenfield project, we add Data Models & API contracts in Spec.md file.
- Apart from that we add, Acceptance Criteria, Agent graph topology & problem statement.
- SPEC.md is only needed in two situations:

1. Situation 1 — Greenfield project like ours
   Nothing exists yet. No code, no models, no APIs. You need to define the architecture somewhere before Claude Code can build it. That's our current situation. We wrote SPEC.md once, at the start, to define the whole system. We won't keep updating it for every feature.

2. Situation 2 — Complex feature with many moving parts
   A feature so large and interconnected that a ticket description isn't enough context. You write a spec for that one feature, Claude Code implements from it. Done.
   For everything else — normal tickets, bug fixes, small features — you just paste the ticket directly.

# Setting up Python virtual environment

- `python3 -m venv venv`
- `source venv/bin/activate`

* Every time we open a new terminal window to work on this project, we need to run source venv/bin/activate first. The virtual environment only activates for the current terminal session. If we forget, Python won't find any of the packages we're about to install.

## Python dependencies

- langgraph — the core framework for building our multi-agent pipeline. It lets us define agents as nodes in a graph, connect them with edges, and control the flow between them including the **interrupt/resume pattern**.

- langchain and langchain-anthropic/langchain-openai — LangChain is the toolkit that connects LLMs to everything else — vector databases, document loaders, retrievers. langchain-anthropic is specifically the Claude integration.

- openAI/anthropic — the official Anthropic SDK. This is what actually calls the Claude API for tool use inside the ingestion agent.

- langchain-postgres — connects LangChain's RAG retrieval to PostgreSQL with pgvector. This is how we store and search tax rule embeddings.

- fastapi and uvicorn — FastAPI is the web framework for our API. Uvicorn is the server that runs it. FastAPI handles the HTTP requests, Uvicorn handles the actual serving.

- python-multipart — allows FastAPI to accept file uploads. Needed when the advisor uploads a PDF.

- pydantic — data validation library. All our models — GrantData, RiskScores, AgentState — are Pydantic models. It enforces types at runtime so bad data never gets through.

- python-dotenv — reads your .env file and loads the API keys as environment variables. Without this, your code can't access ANTHROPIC_API_KEY.

- psycopg2-binary — PostgreSQL driver for Python. The layer that actually talks to the database.

- pgvector — adds vector similarity search to PostgreSQL. This is what makes RAG retrieval possible — finding the most relevant tax rules for a given query.

- pytest and pytest-asyncio — testing framework. pytest-asyncio specifically handles testing async code which FastAPI and LangGraph use heavily.

- ragas — evaluation framework for RAG systems. Measures faithfulness, answer relevancy, and context recall. This is how we prove the RAG quality in the acceptance criteria.

Our Python code
↓
langchain-postgres ← Python library, speaks LangChain
↓
psycopg2 ← Python library, speaks PostgreSQL
↓
PostgreSQL + pgvector ← database with vector search built in

# Setting up .env file

API_KEY=your_llm-api_key_here
LANGCHAIN_API_KEY=your_langsmith_key_here - Go to `smith.langchain.com`. For agent tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=equity-advisor
DATABASE_URL=postgresql://postgres:password@localhost:5432/equity_advisor

## Setting up Postgres via docker

```docker run -d \
  --name equity-advisor-db \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=equity_advisor \
  -p 5432:5432 \
  pgvector/pgvector:pg15
```

### What each flag does:

- -d — runs the container in the background so it doesn't block your terminal
- --name equity-advisor-db — gives the container a name so you can refer to it easily instead of a random ID
- -e POSTGRES_PASSWORD=password — sets the database password
- -e POSTGRES_DB=equity_advisor — creates a database called equity_advisor automatically on first run
- -p 5432:5432 — maps port 5432 on your machine to port 5432 inside the container. Your Python code connects to localhost:5432 and Docker forwards it to the container
- pgvector/pgvector:pg15 — the image to use, PostgreSQL 15 with pgvector included
