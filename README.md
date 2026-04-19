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

-d — runs the container in the background so it doesn't block your terminal
--name equity-advisor-db — gives the container a name so you can refer to it easily instead of a random ID
-e POSTGRES_PASSWORD=password — sets the database password
-e POSTGRES_DB=equity_advisor — creates a database called equity_advisor automatically on first run
-p 5432:5432 — maps port 5432 on your machine to port 5432 inside the container. Your Python code connects to localhost:5432 and Docker forwards it to the container
pgvector/pgvector:pg15 — the image to use, PostgreSQL 15 with pgvector included
