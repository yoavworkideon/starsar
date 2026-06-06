"""
STARDAR RAG — MCP server.

Exposes the project's pgvector knowledge base to any MCP client (e.g. Claude Code)
so that answers can be grounded in the STARDAR corpus (papers, notes, textbooks,
architecture docs, simulation code) rather than general model knowledge.

Run (stdio transport):
    .venv/bin/python3 -m rag.mcp_server

Registered for Claude Code via the repo's .mcp.json.
"""

import asyncio
import logging

from mcp.server.fastmcp import FastMCP

# Best-effort: pick up DATABASE_URL from .env if python-dotenv is present.
# retrieve.py already has a correct localhost:5433 default, so this is optional.
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from rag.retrieve import RAGRetriever, _get_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stardar-rag-mcp")

mcp = FastMCP("stardar-rag")

_retriever = RAGRetriever()


async def _all_collections() -> list[str]:
    """Distinct collection names currently present in the DB."""
    pool = await _get_pool()
    rows = await pool.fetch("SELECT DISTINCT collection FROM documents ORDER BY collection")
    return [r["collection"] for r in rows]


@mcp.tool()
async def list_collections() -> str:
    """List the RAG knowledge-base collections and how many chunks each holds.

    Call this first to discover which collections exist before searching.
    """
    try:
        pool = await _get_pool()
        rows = await pool.fetch(
            "SELECT collection, COUNT(*) AS n FROM documents "
            "GROUP BY collection ORDER BY collection"
        )
    except Exception as e:
        return f"Could not reach the RAG database: {e}\n(Is `docker compose up -d db` running on port 5433?)"

    if not rows:
        return "No collections found — the knowledge base appears empty. Run scripts/build_knowledge_base.sh."
    return "\n".join(f"- {r['collection']}: {r['n']} chunks" for r in rows)


@mcp.tool()
async def search_knowledge_base(
    query: str,
    collections: list[str] | None = None,
    top_k: int = 5,
) -> str:
    """Search the STARDAR knowledge base for chunks relevant to a query.

    Uses vector search over pgvector + CrossEncoder reranking. Returns the top_k
    most relevant chunks, each prefixed with its source and a relevance score,
    ready to ground an answer.

    Args:
        query: Natural-language search query (a question or topic).
        collections: Which collections to search. Common values: "papers", "notes",
            "textbooks", "architecture", "simulation_code". If omitted, searches ALL
            collections present in the DB.
        top_k: Number of chunks to return (default 5).
    """
    try:
        cols = collections or await _all_collections()
        if not cols:
            return "No collections available to search. Run scripts/build_knowledge_base.sh first."
        result = await _retriever.retrieve(query, collections=cols, top_k=top_k)
    except Exception as e:
        return f"RAG search failed: {e}\n(Is `docker compose up -d db` running on port 5433?)"

    if not result:
        return f"No relevant chunks found for: {query!r} in collections {cols}."
    return result


if __name__ == "__main__":
    mcp.run()
