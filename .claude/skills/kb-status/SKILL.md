---
name: kb-status
description: Show the status of the STARDAR RAG knowledge base — which collections exist and how many chunks each holds. Brings the DB up if needed. Use when the user types /kb-status or asks what's in the knowledge base / RAG.
---

# /kb-status — knowledge base health

## Ensure the DB is up
```bash
docker compose up -d db
```
If Docker isn't running, tell the user to start Docker Desktop — don't proceed.

## Report collections + counts
```bash
.venv/bin/python3 - <<'PY'
import asyncio, asyncpg, os
DB = os.environ.get("DATABASE_URL", "postgresql://stardar:stardar@localhost:5433/stardar")
async def main():
    c = await asyncpg.connect(DB)
    rows = await c.fetch("SELECT collection, COUNT(*) n FROM documents GROUP BY collection ORDER BY collection")
    total = sum(r["n"] for r in rows)
    for r in rows:
        print(f"{r['collection']:>16}: {r['n']:>5}  ({100*r['n']/total:.0f}%)")
    print(f"{'TOTAL':>16}: {total:>5}")
    await c.close()
asyncio.run(main())
PY
```

## After
Flag anything unhealthy:
- A single collection holding > ~50% of all chunks (the "drowning" problem — e.g. the textbook
  that was split out of `papers`). Suggest splitting it into its own collection.
- An empty/expected-but-missing collection. Suggest `/ingest` or `scripts/build_knowledge_base.sh`.
