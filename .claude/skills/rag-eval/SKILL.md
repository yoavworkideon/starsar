---
name: rag-eval
description: Evaluate the relevance and quality of the STARDAR RAG retrieval — run probe queries, inspect retrieved chunks and scores, and flag low-relevance, collection-dominance, duplicate, or conflicting content. Use when the user types /rag-eval or asks whether the RAG/knowledge base is "good", "relevant", "reliable", or after a large ingest.
---

# /rag-eval — measure retrieval relevance & quality

Verifies the knowledge base actually answers questions well, not just that it has data.

The arguments may contain probe queries. If none, generate 5–8 representative STARDAR questions
spanning the domains (geometry, signal processing, SNR/link budget, sync, Starlink specs).

## 1. Preflight
```bash
docker compose up -d db
```

## 2. Run probes through the real retriever
For each probe query, retrieve and inspect scores:
```bash
.venv/bin/python3 - <<'PY'
import asyncio
from rag.retrieve import RAGRetriever, _get_pool
PROBES = [
    "range resolution at 250 MHz bandwidth",
    "bistatic Doppler formula for moving illuminator",
    "GPSDO synchronization accuracy for passive radar",
    # ... fill from arguments / generated probes
]
async def main():
    pool = await _get_pool()
    cols = [r["collection"] for r in await pool.fetch("SELECT DISTINCT collection FROM documents")]
    r = RAGRetriever()
    for q in PROBES:
        out = await r.retrieve(q, collections=cols, top_k=3)
        top = out.split("\n", 1)[0] if out else "(no results)"
        print(f"\nQ: {q}\n  top: {top}")
asyncio.run(main())
PY
```
The retriever prints each chunk as `[source] (relevance: X.XX)`. Read the scores.

## 3. Report a quality scorecard
Flag and explain:
- **Low relevance** — top reranker score < ~0.3 for a query the corpus *should* answer → coverage gap.
  Recommend `/kb-research` on that topic.
- **Collection dominance** — if one collection supplies most top hits across unrelated queries,
  it's drowning the rest (the textbook problem). Recommend splitting it out.
- **Duplicates** — near-identical chunks from different sources in the same result set.
- **Conflicts** — chunks giving different numbers for the same quantity → reliability risk; surface both.
- **Stale/contradicts code** — a chunk whose numbers disagree with CLAUDE.md or the simulation modules.

Output a short table: query → top score → verdict (good / weak / gap / conflict), then prioritized fixes.
