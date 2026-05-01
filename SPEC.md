# SPEC: Equity Grant Multi-Agent Advisor

## Problem being solved

Financial advisors spend 3+ hours per client manually reading grant PDFs, calculating AMT exposure, and writing exercise strategies. This system automates the full pipeline in seconds.

## Agent graph topology

START
|
ingestion_agent [reads PDF -> extracts GrantData]
|
|-- confidence < 0.8 --> INTERRUPT [human reviews fields]
| |
|<----- resume ----------------
|
rag_research_agent [retrieves relevant tax rules]
|
risk_analyst_agent [calculates AMT, concentration, priority]
|
strategy_agent [generates prioritised exercise plan]
|
report_agent [writes client-ready markdown report]
|
END

## Data models

### GrantData

grant_type: "ISO" | "NSO" | "RSU" | "ESPP"
grant_date: date
expiration_date: date
total_shares: int
vested_shares: int
strike_price: float
current_fmv: float
company_name: str
confidence_per_field: dict[str, float]

### RiskScores

amt_exposure_usd: float
concentration_pct: float
days_to_expiry: int
priority_score: int # 0-100, higher means act sooner
top_risks: list[str] # 3 human-readable risk bullets

### AgentState

grant_document_raw: str
grant_data: GrantData | None
extraction_confidence: float
human_corrections: dict
tax_research: list[str]
risk_scores: RiskScores | None
strategy: str | None
report_markdown: str | None
agent_log: list[str]

## API contracts

POST /api/run
body: { pdf_text: str, portfolio_value: float }
returns: { run_id: str }

GET /api/stream/{run_id}
returns: SSE stream of AgentEvent
AgentEvent: {
agent: str,
status: "running" | "done" | "interrupt",
output: list[str],
timestamp: str
}

POST /api/review/{run_id}
body: { corrections: dict }
returns: { resumed: true }

GET /api/report/{run_id}
returns: { markdown: str, risk_scores: RiskScores }

strategy_agent → consumes grant_data + risk_scores + tax_research,
calls GPT-4o, returns prioritised exercise plan
with citations, minimum 3 action items

## Acceptance criteria

[ ] All GrantData fields extracted from a sample PDF text
[ ] interrupt() fires when any field confidence < 0.8
[ ] RAG retrieves >= 3 relevant chunks per query
[ ] AMT calculation correct for a known ISO test fixture
[ ] Strategy contains >= 3 prioritised actions with reasoning
[ ] Report renders in React with citations
[ ] LangSmith shows full trace for every run
[ ] RAGAs faithfulness >= 0.85 on 10 golden Q&A pairs
