from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from dotenv import load_dotenv

from backend.agents.state import AgentState, GrantData, RiskScores

load_dotenv()

_AMT_RATE = 0.28
_EXPIRY_HORIZON_DAYS = 365
_CONCENTRATION_DANGER_PCT = 15.0
_AMT_NORMALISER = 100_000.0
_INTRINSIC_NORMALISER = 100_000.0


def calc_amt_exposure(
    grant_type: Literal["ISO", "NSO", "RSU", "ESPP"],
    strike_price: float,
    current_fmv: float,
    vested_shares: int,
) -> float:
    """Return AMT exposure in USD for ISO grants: spread × shares × 28% rate. All other grant types owe no AMT."""
    if grant_type != "ISO":
        return 0.0
    spread = max(0.0, current_fmv - strike_price)
    return spread * vested_shares * _AMT_RATE


def calc_concentration_pct(
    vested_shares: int,
    current_fmv: float,
    portfolio_value: float,
) -> float:
    """Return the percentage of net worth represented by the vested position. Returns 0.0 if portfolio_value is zero."""
    if portfolio_value == 0.0:
        return 0.0
    return (vested_shares * current_fmv) / portfolio_value * 100.0


def calc_days_to_expiry(expiration_date: date) -> int:
    """Return calendar days until the grant expires, using UTC today as the reference date."""
    today = datetime.now(timezone.utc).date()
    return (expiration_date - today).days


def calc_priority_score(
    amt_exposure: float,
    concentration_pct: float,
    days_to_expiry: int,
    intrinsic_value: float,
) -> int:
    """
    Return a 0–100 urgency score.

    Weights:
      40% expiry urgency  — normalised over a 365-day horizon
      30% concentration   — danger threshold is 15% of net worth
      20% AMT exposure    — normalised against $100k reference
      10% intrinsic value — normalised against $100k reference
    """
    expiry_score = max(0.0, min(1.0, (_EXPIRY_HORIZON_DAYS - days_to_expiry) / _EXPIRY_HORIZON_DAYS))
    concentration_score = min(1.0, concentration_pct / _CONCENTRATION_DANGER_PCT)
    amt_score = min(1.0, amt_exposure / _AMT_NORMALISER)
    intrinsic_score = max(0.0, min(1.0, intrinsic_value / _INTRINSIC_NORMALISER))

    raw = (
        0.40 * expiry_score
        + 0.30 * concentration_score
        + 0.20 * amt_score
        + 0.10 * intrinsic_score
    ) * 100.0

    return max(0, min(100, round(raw)))


def build_top_risks(
    amt_exposure: float,
    concentration_pct: float,
    days_to_expiry: int,
) -> list[str]:
    """Return exactly 3 plain-English risk bullets covering expiry, AMT, and concentration."""
    if days_to_expiry <= 0:
        expiry_risk = "Grant has already expired — no exercise is possible."
    elif days_to_expiry <= 90:
        expiry_risk = f"Grant expires in {days_to_expiry} days — immediate action required."
    elif days_to_expiry <= 365:
        expiry_risk = f"Grant expires in {days_to_expiry} days — exercise window is closing."
    else:
        expiry_risk = f"Grant expires in {days_to_expiry} days — monitor as expiry approaches."

    if amt_exposure > 0:
        amt_risk = f"ISO exercise would trigger an estimated ${amt_exposure:,.0f} AMT liability."
    else:
        amt_risk = "No AMT exposure — grant type does not trigger Alternative Minimum Tax."

    if concentration_pct >= _CONCENTRATION_DANGER_PCT:
        concentration_risk = (
            f"Vested position is {concentration_pct:.1f}% of net worth — "
            f"above the {_CONCENTRATION_DANGER_PCT:.0f}% concentration danger threshold."
        )
    else:
        concentration_risk = (
            f"Vested position is {concentration_pct:.1f}% of net worth — "
            f"within the {_CONCENTRATION_DANGER_PCT:.0f}% safe concentration limit."
        )

    return [expiry_risk, amt_risk, concentration_risk]


def risk_analyst_agent(state: AgentState) -> AgentState:
    """LangGraph node: compute AMT exposure, concentration, and priority score from GrantData."""
    grant_data: GrantData | None = state["grant_data"]
    if grant_data is None:
        raise ValueError("risk_analyst_agent: grant_data is None — ingestion_agent must run first.")

    portfolio_value: float = float(state["human_corrections"].get("portfolio_value", 0.0))

    amt_exposure = calc_amt_exposure(
        grant_data.grant_type,
        grant_data.strike_price,
        grant_data.current_fmv,
        grant_data.vested_shares,
    )
    concentration_pct = calc_concentration_pct(
        grant_data.vested_shares,
        grant_data.current_fmv,
        portfolio_value,
    )
    days_to_expiry = calc_days_to_expiry(grant_data.expiration_date)
    total_intrinsic = max(0.0, grant_data.current_fmv - grant_data.strike_price) * grant_data.vested_shares
    priority_score = calc_priority_score(amt_exposure, concentration_pct, days_to_expiry, total_intrinsic)
    top_risks = build_top_risks(amt_exposure, concentration_pct, days_to_expiry)

    risk_scores = RiskScores(
        amt_exposure_usd=amt_exposure,
        concentration_pct=concentration_pct,
        days_to_expiry=days_to_expiry,
        priority_score=priority_score,
        top_risks=top_risks,
    )

    log_entry = (
        f"[{datetime.now(timezone.utc).isoformat()}] risk_analyst_agent: "
        f"priority_score={priority_score}, amt_exposure_usd=${amt_exposure:,.0f}"
    )

    return {
        **state,
        "risk_scores": risk_scores,
        "agent_log": state["agent_log"] + [log_entry],
    }
