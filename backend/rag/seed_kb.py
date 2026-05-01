from __future__ import annotations

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI

load_dotenv()

_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
_EMBEDDING_MODEL = "text-embedding-3-small"
_MIN_CHUNK_LENGTH = 50


def load_docs(docs_dir: Path) -> list[str]:
    """Read every .txt file in docs_dir and return their contents as a list of strings."""
    if not docs_dir.exists():
        raise FileNotFoundError(f"seed_kb: docs directory not found: {docs_dir}")
    texts = [p.read_text(encoding="utf-8") for p in sorted(docs_dir.glob("*.txt"))]
    if not texts:
        raise FileNotFoundError(f"seed_kb: no .txt files found in {docs_dir}")
    return texts


def split_docs(texts: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split documents into chunks using RecursiveCharacterTextSplitter; discard chunks shorter than 50 characters."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = splitter.create_documents(texts)
    return [c.page_content for c in chunks if len(c.page_content) >= _MIN_CHUNK_LENGTH]


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    """Embed all chunks in a single batched OpenAI request using text-embedding-3-small."""
    response = _client.embeddings.create(model=_EMBEDDING_MODEL, input=chunks)
    return [item.embedding for item in response.data]


def _vector_literal(embedding: list[float]) -> str:
    """Format an embedding list as a pgvector literal string."""
    return "[" + ",".join(str(v) for v in embedding) + "]"


def seed(docs_dir: Path, chunk_size: int = 500, chunk_overlap: int = 100) -> None:
    """Load, chunk, embed, and insert all tax rule documents into the knowledge_base table."""
    texts = load_docs(docs_dir)
    chunks = split_docs(texts, chunk_size, chunk_overlap)
    embeddings = embed_chunks(chunks)

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector(1536) NOT NULL
                )
            """)
            cursor.execute("TRUNCATE knowledge_base")
            cursor.executemany(
                "INSERT INTO knowledge_base (content, embedding) VALUES (%s, %s::vector)",
                [
                    (chunk, _vector_literal(embedding))
                    for chunk, embedding in zip(chunks, embeddings)
                ],
            )
        conn.commit()
    finally:
        conn.close()

    print(f"Seeded {len(chunks)} chunks from {len(texts)} documents into knowledge_base")


if __name__ == "__main__":
    seed(docs_dir=Path(__file__).parent / "docs")
