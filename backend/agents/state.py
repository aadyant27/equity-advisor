'''
Docstring for backend.agents.state
The 3 classes:

2. GrantData
This is the structured output of the ingestion agent. When the advisor uploads a PDF, the ingestion agent reads it and extracts these exact fields:
pythongrant_type: Literal["ISO", "NSO", "RSU", "ESPP"]  # what kind of grant
grant_date: date                                    # when it was granted
expiration_date: date                               # when it expires
total_shares: int                                   # how many shares total
vested_shares: int                                  # how many have vested
strike_price: float                                 # what the employee pays
current_fmv: float                                  # what the stock is worth now
company_name: str                                   # which company
confidence_per_field: dict[str, float]              # how confident the AI was per field
Literal["ISO", "NSO", "RSU", "ESPP"] means Pydantic will reject any other value at runtime. If the ingestion agent somehow extracts "STOCK_OPTION" instead of "ISO", Pydantic throws an error immediately. You catch bad data at the boundary, not deep inside the pipeline where it causes mysterious failures.
It inherits from BaseModel which is Pydantic. This means every field is validated when the object is created — wrong type, missing field, invalid value — all caught instantly.

3.RiskScores
This is the output of the risk analyst agent. After it runs its calculations it produces:
pythonamt_exposure_usd: float      # how much AMT tax the client could owe
concentration_pct: float     # what % of their net worth is this stock
days_to_expiry: int          # how many days until the grant expires
priority_score: int          # 0-100, how urgently to act
top_risks: list[str]         # 3 plain English risk descriptions
The strategy agent reads this to decide what recommendations to make. The report agent reads this to display the risk summary to the advisor.

AgentState
This is the baton that every agent passes along the pipeline. It contains everything — raw input, intermediate results, final outputs, and a running log.
pythongrant_document_raw: str          # the raw PDF text — input from the advisor
grant_data: GrantData | None     # populated by ingestion_agent
extraction_confidence: float     # populated by ingestion_agent
human_corrections: dict          # populated by human during interrupt
tax_research: list[str]          # populated by rag_research_agent
risk_scores: RiskScores | None   # populated by risk_analyst_agent
strategy: str | None             # populated by strategy_agent
report_markdown: str | None      # populated by report_agent
agent_log: list[str]             # each agent appends a log entry
The | None fields start as None and get filled in as the pipeline progresses. At the start only grant_document_raw has a value. By the end every field is populated.
It uses TypedDict instead of Pydantic BaseModel because LangGraph requires its state to be a TypedDict. It's a Python dictionary with known keys and typed values — LangGraph can merge partial updates from each agent cleanly.
'''


from __future__ import annotations

from datetime import date
from typing import Literal, TypedDict

from pydantic import BaseModel


class GrantData(BaseModel):
    """Structured representation of a client's equity grant extracted from a PDF by the ingestion agent."""

    grant_type: Literal["ISO", "NSO", "RSU", "ESPP"]
    grant_date: date
    expiration_date: date
    total_shares: int
    vested_shares: int
    strike_price: float
    current_fmv: float
    company_name: str
    confidence_per_field: dict[str, float]


class RiskScores(BaseModel):
    """Quantified risk metrics produced by the risk_analyst_agent for a single grant."""

    amt_exposure_usd: float
    concentration_pct: float
    days_to_expiry: int
    priority_score: int  # 0-100, higher means act sooner
    top_risks: list[str]  # 3 human-readable risk bullets


class AgentState(TypedDict):
    """Shared mutable state threaded through every node in the LangGraph pipeline."""

    grant_document_raw: str
    grant_data: GrantData | None
    extraction_confidence: float
    human_corrections: dict
    tax_research: list[str]
    risk_scores: RiskScores | None
    strategy: str | None
    report_markdown: str | None
    agent_log: list[str]
