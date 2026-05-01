from __future__ import annotations

from datetime import datetime, timezone

from dotenv import load_dotenv

from backend.agents.state import AgentState, GrantData, RiskScores

load_dotenv()


def _format_grant_summary(grant_data: GrantData) -> str:
    """Return a markdown table of all GrantData fields excluding confidence_per_field."""
    rows = [
        ("Field", "Value"),
        ("---", "---"),
        ("Grant Type", grant_data.grant_type),
        ("Company", grant_data.company_name),
        ("Grant Date", str(grant_data.grant_date)),
        ("Expiration Date", str(grant_data.expiration_date)),
        ("Total Shares", f"{grant_data.total_shares:,}"),
        ("Vested Shares", f"{grant_data.vested_shares:,}"),
        ("Strike Price", f"${grant_data.strike_price:,.2f}"),
        ("Current FMV", f"${grant_data.current_fmv:,.2f}"),
    ]
    return "\n".join(f"| {r[0]} | {r[1]} |" for r in rows)


def _format_risk_scores(risk_scores: RiskScores) -> str:
    """Return a markdown table of numeric risk fields and a bulleted list of top_risks."""
    table_rows = [
        ("Metric", "Value"),
        ("---", "---"),
        ("AMT Exposure", f"${risk_scores.amt_exposure_usd:,.0f}"),
        ("Concentration", f"{risk_scores.concentration_pct:.1f}%"),
        ("Days to Expiry", str(risk_scores.days_to_expiry)),
        ("Priority Score", f"{risk_scores.priority_score}/100"),
    ]
    table = "\n".join(f"| {r[0]} | {r[1]} |" for r in table_rows)
    bullets = "\n".join(f"- {risk}" for risk in risk_scores.top_risks)
    return f"{table}\n\n{bullets}"


def _format_references(tax_research: list[str]) -> str:
    """Return a numbered reference list with [Research N] labels matching strategy citations."""
    return "\n\n".join(f"**[Research {i + 1}]** {chunk}" for i, chunk in enumerate(tax_research))


def _assemble_report(
    grant_data: GrantData,
    risk_scores: RiskScores,
    strategy: str,
    tax_research: list[str],
) -> str:
    """Compose the full client-ready markdown report from all pipeline outputs."""
    return "\n\n".join([
        "# Equity Grant Exercise Strategy Report",
        f"## Grant Summary\n\n{_format_grant_summary(grant_data)}",
        f"## Risk Assessment\n\n{_format_risk_scores(risk_scores)}",
        f"## Exercise Strategy\n\n{strategy}",
        f"## References\n\n{_format_references(tax_research)}",
    ])


def report_agent(state: AgentState) -> AgentState:
    """LangGraph node: assemble the final client-ready markdown report from all upstream state fields."""
    grant_data: GrantData | None = state["grant_data"]
    risk_scores: RiskScores | None = state["risk_scores"]
    strategy: str | None = state["strategy"]
    tax_research: list[str] = state["tax_research"]

    if grant_data is None:
        raise ValueError("report_agent: grant_data is None — ingestion_agent must run first.")
    if risk_scores is None:
        raise ValueError("report_agent: risk_scores is None — risk_analyst_agent must run first.")
    if not strategy:
        raise ValueError("report_agent: strategy is None — strategy_agent must run first.")

    report_markdown = _assemble_report(grant_data, risk_scores, strategy, tax_research)

    log_entry = (
        f"[{datetime.now(timezone.utc).isoformat()}] report_agent: "
        f"report assembled ({len(report_markdown)} chars)"
    )

    return {
        **state,
        "report_markdown": report_markdown,
        "agent_log": state["agent_log"] + [log_entry],
    }
