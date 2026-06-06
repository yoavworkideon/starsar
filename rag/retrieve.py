"""
RAG Retriever — vector search via pgvector + CrossEncoder reranking.
"""

import asyncio
import json
import os
import logging
import signal
from typing import Any

import asyncpg
from sentence_transformers import CrossEncoder

from rag.embeddings import embed_one

logger = logging.getLogger(__name__)

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DB_URL = os.environ.get("DATABASE_URL", "postgresql://stardar:stardar@localhost:5433/stardar")

# Module-level singletons — loaded/created once, shared across all RAGRetriever instances
_reranker_singleton: CrossEncoder | None = None
_pool_singleton: asyncpg.Pool | None = None


def _get_reranker() -> CrossEncoder:
    global _reranker_singleton
    if _reranker_singleton is None:
        _reranker_singleton = CrossEncoder(RERANKER_MODEL)
    return _reranker_singleton


async def _get_pool() -> asyncpg.Pool:
    global _pool_singleton
    if _pool_singleton is None:
        _pool_singleton = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10)
    return _pool_singleton


class RAGRetriever:
    def __init__(self, top_k_fetch: int = 20):
        self.top_k_fetch = top_k_fetch

    async def retrieve(
        self,
        query: str,
        collections: list[str],
        top_k: int = 5,
    ) -> str:
        """
        Retrieve top_k most relevant chunks for the query.
        Returns formatted string ready to inject into model context.
        """
        try:
            # embed_one and reranker.predict are CPU-bound synchronous calls.
            # Run them in a thread so the event loop stays alive during ML inference —
            # preventing stale HTTP connections on the shared Anthropic client singleton.
            embedding = str(await asyncio.to_thread(embed_one, query))
            pool = await _get_pool()

            placeholders = ", ".join(f"${i+2}" for i in range(len(collections)))
            sql = f"""
                SELECT id, collection, content, metadata,
                       1 - (embedding <=> $1::vector) AS score
                FROM documents
                WHERE collection IN ({placeholders})
                ORDER BY embedding <=> $1::vector
                LIMIT ${ len(collections) + 2 }
            """

            rows = await pool.fetch(sql, embedding, *collections, self.top_k_fetch)
            if not rows:
                return ""

            # Rerank — also off the event loop thread
            reranker = _get_reranker()
            pairs    = [[query, r["content"]] for r in rows]
            scores   = await asyncio.to_thread(reranker.predict, pairs)

            # PyTorch/MPS (loaded on first predict) resets SIGURG to SIG_DFL via sigaction.
            # Reinstall SIG_IGN here — we're back on the main (event loop) thread,
            # PyTorch init is done, and the next operation is an Anthropic API call.
            signal.signal(signal.SIGURG, signal.SIG_IGN)

            ranked   = sorted(zip(scores, rows), key=lambda x: x[0], reverse=True)

            # Format top_k results
            chunks = []
            for score, row in ranked[:top_k]:
                raw_meta = row["metadata"] or {}
                meta = json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta
                source = meta.get("source", row["collection"])
                chunks.append(f"[{source}] (relevance: {score:.2f})\n{row['content']}")

            return "\n\n---\n\n".join(chunks)

        except Exception as e:
            logger.error("RAG retrieval failed: %s", e)
            return ""
