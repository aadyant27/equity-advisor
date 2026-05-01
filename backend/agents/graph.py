from __future__ import annotations

from datetime import datetime, timezone

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from backend.agents.ingestion import ingestion_agent
from backend.agents.rag_research import rag_research_agent
from backend.agents.report import report_agent
from backend.agents.risk_analyst import risk_analyst_agent
from backend.agents.state import AgentState
from backend.agents.strategy import strategy_agent


def _route_after_ingestion(state: AgentState) -> str:
    """Route to human review if extraction confidence is below threshold, otherwise continue."""
    if state["extraction_confidence"] < 0.8:
        return "human_review"
    return "rag_research_agent"


def human_review_node(state: AgentState) -> AgentState:
    """Pause the graph for human review of low-confidence extractions and merge corrections into state."""
    corrections = interrupt({
        "grant_data": state["grant_data"],
        "extraction_confidence": state["extraction_confidence"],
    })
    log_entry = (
        f"[{datetime.now(timezone.utc).isoformat()}] human_review: "
        "human corrections applied"
    )
    return {
        **state,
        "human_corrections": corrections,
        "agent_log": state["agent_log"] + [log_entry],
    }


def build_graph(checkpointer=None):
    """Build and compile the equity advisor LangGraph pipeline with an optional persistence checkpointer."""
    builder = StateGraph(AgentState)

    builder.add_node("ingestion_agent", ingestion_agent)
    builder.add_node("human_review", human_review_node)
    builder.add_node("rag_research_agent", rag_research_agent)
    builder.add_node("risk_analyst_agent", risk_analyst_agent)
    builder.add_node("strategy_agent", strategy_agent)
    builder.add_node("report_agent", report_agent)

    builder.add_edge(START, "ingestion_agent")
    builder.add_conditional_edges("ingestion_agent", _route_after_ingestion)
    builder.add_edge("human_review", "rag_research_agent")
    builder.add_edge("rag_research_agent", "risk_analyst_agent")
    builder.add_edge("risk_analyst_agent", "strategy_agent")
    builder.add_edge("strategy_agent", "report_agent")
    builder.add_edge("report_agent", END)

    return builder.compile(checkpointer=checkpointer)


graph = build_graph(checkpointer=MemorySaver())
