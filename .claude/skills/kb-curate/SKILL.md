---
name: kb-curate
description: Curate and clean the STARDAR RAG knowledge base — find duplicate / near-duplicate chunks, a collection that dominates search, empty or junk chunks, and propose fixes. Use when the user types /kb-curate or asks to clean up / deduplicate / prune the knowledge base.
---

# /kb-curate — clean and rebalance the knowledge base

Improves *reliability* by removing noise the retriever would otherwise surface.

## 1. Preflight
```bash
docker compose up -d db
```

## 2. Scan for problems
```bash
.venv/bin/python3 - <<'PY'
import asyncio, asyncpg, os
DB = os.environ.get("DATABASE_URL", "postgresql://stardar:stardar@localhost:5433/stardar")
async def main():
    c = await asyncpg.connect(DB)
    # collection balance
    rows = await c.fetch("SELECT collection, COUNT(*) n FROM documents GROUP BY collection ORDER BY n DESC")
    total = sum(r["n"] for r in rows)
    print("Balance:")
    for r in rows:
        print(f"  {r['collection']}: {r['n']} ({100*r['n']/total:.0f}%)")
    # exact-duplicate content
    dups = await c.fetch("SELECT content, COUNT(*) n FROM documents GROUP BY content HAVING COUNT(*) > 1 ORDER BY n DESC LIMIT 20")
    print(f"\nExact-duplicate chunks: {len(dups)}")
    for d in dups:
        print(f"  x{d['n']}: {d['content'][:80]!r}")
    # tiny / junk chunks
    junk = await c.fetch("SELECT id, collection, length(content) l FROM documents WHERE length(content) < 40 ORDER BY l LIMIT 20")
    print(f"\nTiny chunks (<40 chars): {len(junk)}")
    await c.close()
asyncio.run(main())
PY
```

## 3. Propose fixes (do NOT delete without confirmation)
- **Dominant collection** (> ~50%): recommend re-ingesting it into its own collection with `--reset`.
- **Exact duplicates**: propose a dedupe `DELETE` keeping one row per identical `content`.
- **Tiny/junk chunks**: usually headers/page numbers from PDF extraction — propose deletion.
- For near-duplicates (high cosine similarity but not identical), optionally embed-compare a sample.

Always show the user the exact SQL before running any destructive change, and back up with
`pg_dump` if the change is large.
