"""
RAG Ingestor — chunks and embeds documents into pgvector.

Supported sources:
  - PDF papers (via pypdf)
  - Python source files (simulation code)
  - Markdown docs (ARCHITECTURE.md etc.)

Usage:
  python -m rag.ingest --source data/papers/ --collection papers
  python -m rag.ingest --source simulation/  --collection simulation_code
  python -m rag.ingest --source ARCHITECTURE.md --collection architecture
"""

import argparse
import asyncio
import json
import os
from pathlib import Path

import asyncpg
from pypdf import PdfReader

from rag.embeddings import embed

DB_URL     = os.environ.get("DATABASE_URL", "postgresql://stardar:stardar@localhost:5433/stardar")
CHUNK_SIZE = 512    # tokens approx (chars / 4)
OVERLAP    = 64


# ── Schema ────────────────────────────────────────────────────────────

CREATE_TABLE = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id          SERIAL PRIMARY KEY,
    collection  TEXT NOT NULL,
    content     TEXT NOT NULL,
    metadata    JSONB,
    embedding   vector(384)
);

CREATE INDEX IF NOT EXISTS documents_embedding_idx
    ON documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
"""


# ── Chunking ──────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    words  = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk.strip())
        i += chunk_size - overlap
    return chunks


def _clean(text: str) -> str:
    """Strip null bytes and other characters that break UTF-8 postgres storage."""
    return text.replace("\x00", "")


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return _clean("\n\n".join(page.extract_text() or "" for page in reader.pages))


def read_file(path: Path) -> str:
    return _clean(path.read_text(encoding="utf-8", errors="ignore"))


def load_documents(source: Path) -> list[tuple[str, dict]]:
    """Returns list of (text, metadata) pairs."""
    docs = []
    paths = list(source.rglob("*")) if source.is_dir() else [source]
    for p in paths:
        if p.suffix == ".pdf":
            docs.append((read_pdf(p), {"source": p.name, "type": "paper"}))
        elif p.suffix in (".py", ".md", ".txt", ".rst"):
            docs.append((read_file(p), {"source": str(p), "type": p.suffix.lstrip(".")}))
    return docs


# ── Ingest ────────────────────────────────────────────────────────────

async def ingest(source: str, collection: str, reset: bool = False):
    pool = await asyncpg.create_pool(DB_URL)

    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE)
        if reset:
            await conn.execute("DELETE FROM documents WHERE collection = $1", collection)
            print(f"Cleared collection '{collection}'")

    docs     = load_documents(Path(source))
    all_chunks: list[tuple[str, dict]] = []

    for text, meta in docs:
        for chunk in chunk_text(text):
            all_chunks.append((chunk, meta))

    print(f"Embedding {len(all_chunks)} chunks from {len(docs)} documents...")

    batch_size = 64
    inserted   = 0
    for i in range(0, len(all_chunks), batch_size):
        batch    = all_chunks[i : i + batch_size]
        texts    = [c[0] for c in batch]
        metas    = [c[1] for c in batch]
        vectors  = embed(texts)

        async with pool.acquire() as conn:
            await conn.executemany(
                "INSERT INTO documents (collection, content, metadata, embedding) "
                "VALUES ($1, $2, $3, $4::vector)",
                [
                    (collection, t, json.dumps(m), str(v))
                    for t, m, v in zip(texts, metas, vectors)
                ],
            )
        inserted += len(batch)
        print(f"  {inserted}/{len(all_chunks)} chunks ingested")

    await pool.close()
    print(f"Done. {inserted} chunks in collection '{collection}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",     required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--reset",      action="store_true")
    args = parser.parse_args()
    asyncio.run(ingest(args.source, args.collection, args.reset))
