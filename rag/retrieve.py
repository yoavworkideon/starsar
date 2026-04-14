"""
RAG Retriever — vector search via pgvector + CrossEncoder reranking.
"""

import os
import logging
from typing import Any

import asyncpg
from sentence_transformers import CrossEncoder

from rag.embeddings import embed_one

logger = logging.getLogger(__name__)

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DB_URL = os.environ.get("DATABASE_URL", "postgresql://stardar:stardar@localhost:5432/stardar")


class RAGRetriever:
    def __init__(self, top_k_fetch: int = 20):
        self.top_k_fetch = top_k_fetch
        self._reranker: CrossEncoder | None = None
        self._pool: asyncpg.Pool | None = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(DB_URL)
        return self._pool

    def _get_reranker(self) -> CrossEncoder:
        if self._reranker is None:
            self._reranker = CrossEncoder(RERANKER_MODEL)
        return self._reranker

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
            embedding = embed_one(query)
            pool = await self._get_pool()

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

            # Rerank
            reranker = self._get_reranker()
            pairs    = [[query, r["content"]] for r in rows]
            scores   = reranker.predict(pairs)
            ranked   = sorted(zip(scores, rows), key=lambda x: x[0], reverse=True)

            # Format top_k results
            chunks = []
            for score, row in ranked[:top_k]:
                meta = row["metadata"] or {}
                source = meta.get("source", row["collection"])
                chunks.append(f"[{source}] (relevance: {score:.2f})\n{row['content']}")

            return "\n\n---\n\n".join(chunks)

        except Exception as e:
            logger.error("RAG retrieval failed: %s", e)
            return ""
