from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

from backend.agents.state import AgentState, GrantData

load_dotenv()

_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

_EXTRACT_GRANT_DATA_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "extract_grant_data",
        "description": "Extract all equity grant fields from the provided document text.",
        "parameters": {
            "type": "object",
            "properties": {
                "grant_type": {
                    "type": "string",
                    "enum": ["ISO", "NSO", "RSU", "ESPP"],
                    "description": "The type of equity grant.",
                },
                "grant_date": {
                    "type": "string",
                    "description": "The date the grant was issued (YYYY-MM-DD).",
                },
                "expiration_date": {
                    "type": "string",
                    "description": "The date the grant expires (YYYY-MM-DD).",
                },
                "total_shares": {
                    "type": "integer",
                    "description": "Total number of shares in the grant.",
                },
                "vested_shares": {
                    "type": "integer",
                    "description": "Number of shares that have vested.",
                },
                "strike_price": {
                    "type": "number",
                    "description": "Exercise price per share in USD.",
                },
                "current_fmv": {
                    "type": "number",
                    "description": "Current fair market value per share in USD.",
                },
                "company_name": {
                    "type": "string",
                    "description": "Name of the company issuing the grant.",
                },
                "confidence_per_field": {
                    "type": "object",
                    "description": (
                        "Confidence score (0.0–1.0) for each extracted field. "
                        "Keys must match the other parameter names."
                    ),
                    "additionalProperties": {"type": "number"},
                },
            },
            "required": [
                "grant_type",
                "grant_date",
                "expiration_date",
                "total_shares",
                "vested_shares",
                "strike_price",
                "current_fmv",
                "company_name",
                "confidence_per_field",
            ],
        },
    },
}

_SYSTEM_PROMPT = (
    "You are a precise financial document parser. "
    "Extract equity grant information from the provided document text. "
    "For each field assign a confidence score between 0.0 and 1.0 in confidence_per_field "
    "reflecting how certain you are the value is correct. "
    "Use 1.0 only when the value is stated explicitly and unambiguously."
)


def ingestion_agent(state: AgentState) -> AgentState:
    """LangGraph node: extract GrantData from raw PDF text via GPT-4o tool use."""
    pdf_text = state["grant_document_raw"]
    if not pdf_text or not pdf_text.strip():
        raise ValueError("ingestion_agent: grant_document_raw is empty.")

    response = _client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": pdf_text},
        ],
        tools=[_EXTRACT_GRANT_DATA_TOOL],
        tool_choice={"type": "function", "function": {"name": "extract_grant_data"}},
    )

    message = response.choices[0].message
    if not message.tool_calls:
        raise RuntimeError("ingestion_agent: model did not return a tool call.")

    tool_call = message.tool_calls[0]
    try:
        arguments = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ingestion_agent: failed to parse tool arguments — {exc}") from exc

    try:
        grant_data = GrantData(**arguments)
    except Exception as exc:
        raise RuntimeError(f"ingestion_agent: GrantData validation failed — {exc}") from exc

    confidence_values = list(grant_data.confidence_per_field.values())
    avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0

    log_entry = (
        f"[{datetime.now(timezone.utc).isoformat()}] ingestion_agent: "
        f"extracted {grant_data.grant_type} grant for {grant_data.company_name}, "
        f"avg_confidence={avg_confidence:.2f}"
    )

    return {
        **state,
        "grant_data": grant_data,
        "extraction_confidence": avg_confidence,
        "agent_log": state["agent_log"] + [log_entry],
    }
