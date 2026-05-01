from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import NodeInterrupt
from langgraph.types import Command
from pydantic import BaseModel

from backend.agents.graph import build_graph
from backend.agents.state import AgentState, RiskScores

load_dotenv()

app = FastAPI()
_checkpointer = MemorySaver()
_graph = build_graph(checkpointer=_checkpointer)
_runs: dict[str, AgentState] = {}


class RunRequest(BaseModel):
    """Request body for POST /api/run containing the raw PDF text and client portfolio value."""

    pdf_text: str
    portfolio_value: float


class RunResponse(BaseModel):
    """Response body for POST /api/run containing the generated run identifier."""

    run_id: str


class AgentEvent(BaseModel):
    """A single SSE event emitted by GET /api/stream describing one agent's execution status."""

    agent: str
    status: Literal["running", "done", "interrupt"]
    output: list[str]
    timestamp: str


class ReviewRequest(BaseModel):
    """Request body for POST /api/review containing the human corrections to apply after an interrupt."""

    corrections: dict


class ReviewResponse(BaseModel):
    """Response body for POST /api/review confirming the graph has been resumed."""

    resumed: bool


class ReportResponse(BaseModel):
    """Response body for GET /api/report containing the final markdown report and risk scores."""

    markdown: str
    risk_scores: RiskScores


@app.post("/api/run", response_model=RunResponse)
def run(request: RunRequest) -> RunResponse:
    """Accept a PDF text and portfolio value, initialise AgentState, and return a run_id for subsequent streaming."""
    run_id = str(uuid.uuid4())
    _runs[run_id] = AgentState(
        grant_document_raw=request.pdf_text,
        grant_data=None,
        extraction_confidence=0.0,
        human_corrections={"portfolio_value": request.portfolio_value},
        tax_research=[],
        risk_scores=None,
        strategy=None,
        report_markdown=None,
        agent_log=[],
    )
    return RunResponse(run_id=run_id)


@app.get("/api/stream/{run_id}")
def stream(run_id: str) -> StreamingResponse:
    """Stream agent execution events as SSE, emitting one AgentEvent per node completion or on interrupt."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"run_id {run_id!r} not found.")

    state = _runs[run_id]

    def event_generator():
        completed = False
        try:
            for chunk in _graph.stream(
                state,
                config={"configurable": {"thread_id": run_id}},
            ):
                if isinstance(chunk, tuple):
                    node_name, node_output = chunk
                elif isinstance(chunk, dict):
                    for node_name, node_output in chunk.items():
                        pass
                else:
                    continue

                if node_name == "__interrupt__":
                    event = AgentEvent(
                        agent="human_review",
                        status="interrupt",
                        output=[],
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                    yield f"data: {event.model_dump_json()}\n\n"
                    return

                if isinstance(node_output, dict):
                    output = node_output.get("agent_log", [])
                else:
                    output = []

                event = AgentEvent(
                    agent=node_name,
                    status="running",
                    output=output,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                yield f"data: {event.model_dump_json()}\n\n"

            completed = True
        except NodeInterrupt:
            event = AgentEvent(
                agent="human_review",
                status="interrupt",
                output=[],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            yield f"data: {event.model_dump_json()}\n\n"
            return

        if completed:
            event = AgentEvent(
                agent="report_agent",
                status="done",
                output=[],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/review/{run_id}", response_model=ReviewResponse)
def review(run_id: str, request: ReviewRequest) -> ReviewResponse:
    """Resume a graph paused at an interrupt checkpoint by supplying human corrections."""
    _graph.invoke(
        Command(resume=request.corrections),
        config={"configurable": {"thread_id": run_id}},
    )
    return ReviewResponse(resumed=True)


@app.get("/api/report/{run_id}", response_model=ReportResponse)
def report(run_id: str) -> ReportResponse:
    """Return the final markdown report and risk scores for a completed pipeline run."""
    snapshot = _graph.get_state(config={"configurable": {"thread_id": run_id}})
    if not snapshot or snapshot.values.get("report_markdown") is None:
        raise HTTPException(
            status_code=404,
            detail=f"Report for run_id {run_id!r} not found or pipeline not yet complete.",
        )
    return ReportResponse(
        markdown=snapshot.values["report_markdown"],
        risk_scores=snapshot.values["risk_scores"],
    )
