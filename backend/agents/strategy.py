from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

from backend.agents.state import AgentState, GrantData, RiskScores

load_dotenv()

_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
_ACTION_ITEM_RE = re.compile(r"^\s*(\d+[.)]\s*|[-*]\s*)", re.MULTILINE)


def _build_system_prompt() -> str:
    """Return the system prompt that frames the model as a senior equity compensation advisor."""
    return (
        "You are a senior equity compensation advisor. "
        "Given a client's grant details, risk scores, and relevant tax research, "
        "produce a prioritised exercise strategy. "
        "You MUST format your response as a numbered list starting with 1., 2., 3. "
        "Each item must have a clear rationale. "
        "Example format:\n"
        "1. Exercise 25% of vested ISOs before December 31 to stay within the AMT exemption threshold. "
        "[Research 1] confirms the 2024 exemption is $85,700 for single filers.\n"
        "2. Sell RSU shares immediately at vest to reduce concentration below the 15% threshold. "
        "[Research 3] outlines the risks of single-stock concentration above this level.\n"
        "3. Establish a 10b5-1 plan during the next open trading window to automate future sales.\n"
        "Your response will be rejected if it does not contain at least 3 numbered action items. "
        "Cite the provided research chunks using their [Research N] labels where relevant. "
        "Be specific about timing, tax implications, and dollar amounts. "
        "Do not include any personally identifiable information."
    )


def _build_user_message(
    grant_data: GrantData,
    risk_scores: RiskScores,
    tax_research: list[str],
) -> str:
    """Assemble the user message from grant data, risk scores, and numbered research chunks."""
    grant_lines = "\n".join(f"  {k}: {v}" for k, v in grant_data.model_dump().items())
    risk_lines = "\n".join(f"  {k}: {v}" for k, v in risk_scores.model_dump().items())
    research_lines = "\n".join(f"[Research {i + 1}] {chunk}" for i, chunk in enumerate(tax_research))

    return (
        f"## Grant Details\n{grant_lines}\n\n"
        f"## Risk Scores\n{risk_lines}\n\n"
        f"## Tax Research\n{research_lines}\n\n"
        "Please produce a prioritised exercise strategy with cited reasoning."
    )


def _count_action_items(text: str) -> int:
    """Return the number of numbered or bulleted action items found in the text."""
    return len(_ACTION_ITEM_RE.findall(text))


def strategy_agent(state: AgentState) -> AgentState:
    """LangGraph node: generate a prioritised exercise strategy from grant data, risk scores, and tax research."""
    grant_data: GrantData | None = state["grant_data"]
    risk_scores: RiskScores | None = state["risk_scores"]
    tax_research: list[str] = state["tax_research"]

    if grant_data is None:
        raise ValueError("strategy_agent: grant_data is None — ingestion_agent must run first.")
    if risk_scores is None:
        raise ValueError("strategy_agent: risk_scores is None — risk_analyst_agent must run first.")
    if not tax_research:
        raise ValueError("strategy_agent: tax_research is empty — rag_research_agent must run first.")

    response = _client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": _build_user_message(grant_data, risk_scores, tax_research)},
        ],
        max_tokens=1024,
    )

    strategy = response.choices[0].message.content or ""

    action_count = _count_action_items(strategy)
    if action_count < 3:
        raise RuntimeError(
            "strategy_agent: response contains fewer than 3 action items — "
            "the model did not produce a valid prioritised exercise plan."
        )

    log_entry = (
        f"[{datetime.now(timezone.utc).isoformat()}] strategy_agent: "
        f"strategy produced ({len(strategy)} chars, {action_count} action items)"
    )

    return {
        **state,
        "strategy": strategy,
        "agent_log": state["agent_log"] + [log_entry],
    }
