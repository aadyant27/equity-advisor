from __future__ import annotations

import os
from datetime import datetime, timezone

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI

from backend.agents.state import AgentState, GrantData

load_dotenv()

_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
_EMBEDDING_MODEL = "text-embedding-3-small"
_CHUNKS_PER_QUERY = 3


def _build_queries(grant_data: GrantData) -> list[str]:
    """Return 3 targeted query strings derived from the grant's key attributes."""
    return [
        f"{grant_data.grant_type} equity grant tax treatment rules",
        f"{grant_data.grant_type} stock option exercise timing strategy",
        f"equity grant expiration concentration risk {grant_data.grant_type}",
    ]


def _embed(text: str) -> list[float]:
    """Return an embedding vector for the given text using text-embedding-3-small."""
    response = _client.embeddings.create(model=_EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def _vector_literal(embedding: list[float]) -> str:
    """Format an embedding list as a pgvector literal string."""
    return "[" + ",".join(str(v) for v in embedding) + "]"


def _retrieve_chunks(cursor: psycopg2.extensions.cursor, embedding: list[float]) -> list[str]:
    """Query the knowledge_base table and return the top-3 most similar chunks."""
    cursor.execute(
        """
        SELECT content
        FROM knowledge_base
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (_vector_literal(embedding), _CHUNKS_PER_QUERY),
    )
    return [row[0] for row in cursor.fetchall()]


def rag_research_agent(state: AgentState) -> AgentState:
    """LangGraph node: embed grant-specific queries and retrieve relevant tax rules from pgvector."""
    grant_data = state["grant_data"]
    if grant_data is None:
        raise ValueError("rag_research_agent: grant_data is None — ingestion_agent must run first.")

    queries = _build_queries(grant_data)

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cursor:
            seen: set[str] = set()
            chunks: list[str] = []
            for query in queries:
                embedding = _embed(query)
                for chunk in _retrieve_chunks(cursor, embedding):
                    if chunk not in seen:
                        seen.add(chunk)
                        chunks.append(chunk)
    finally:
        conn.close()

    if len(chunks) < 3:
        raise RuntimeError(
            f"rag_research_agent: retrieved only {len(chunks)} unique chunk(s) — "
            "at least 3 are required. Check that the knowledge_base table is populated."
        )

    log_entry = (
        f"[{datetime.now(timezone.utc).isoformat()}] rag_research_agent: "
        f"retrieved {len(chunks)} unique chunks for {grant_data.grant_type} grant "
        f"({grant_data.company_name})"
    )

    return {
        **state,
        "tax_research": chunks,
        "agent_log": state["agent_log"] + [log_entry],
    }
