# Equity Grant Advisor — Project Context

## What this project is

An AI-powered multi-agent system that automates the financial advisor workflow for equity compensation management.
An advisor uploads a client's grant PDF → 5 agents process it
→ a prioritised exercise strategy report is generated.

## Tech stack

- Backend: Python 3.11, FastAPI, LangGraph, LangChain
- LLM: claude-sonnet-4-6 via Anthropic SDK
- Database: PostgreSQL 15 + pgvector extension
- Frontend: React 18 + TypeScript + Vite
- Observability: LangSmith tracing
- Eval: RAGAs

## Domain glossary

- ISO: Incentive Stock Option. Tax-advantaged. Triggers AMT on exercise.
- NSO: Non-qualified Stock Option. Taxed as ordinary income on exercise.
- RSU: Restricted Stock Unit. Taxed as income at vest, no exercise required.
- Strike price: The fixed price the employee pays to exercise an option.
- FMV: Fair Market Value. Current market price of the stock.
- Intrinsic value: FMV minus strike price. Profit per share if exercised now.
- AMT: Alternative Minimum Tax. Triggered by ISO exercise spread.
- Vesting cliff: Minimum period before any shares vest (usually 1 year).
- Concentration risk: Too much net worth in a single stock (>15% is risky).

## Architecture — agents in a LangGraph state graph

1. ingestion_agent → reads PDF, extracts GrantData via Claude tool use
2. INTERRUPT → pauses graph if confidence < 0.8, human reviews
3. rag_research_agent → retrieves tax rules from pgvector knowledge base
4. risk_analyst_agent → calculates AMT exposure, concentration %, priority score
5. strategy_agent → generates prioritised exercise plan with cited reasoning
6. report_agent → outputs client-ready markdown report

## Shared state — AgentState TypedDict

Every agent reads from and writes to AgentState. Never bypass it.
Fields: grant_document_raw, grant_data, extraction_confidence,
human_corrections, tax_research, risk_scores, strategy,
report_markdown, agent_log

## Coding conventions

- All financial math in pure functions with full type hints
- Never log PII (names, SSNs, exact portfolio values)
- Every agent node must return a full AgentState dict
- Pydantic models for all API request/response shapes
- One test per agent node minimum
- Commit after each agent is implemented and tested. Always ask before commiting.
