---
name: verify-claim
description: Verify a physics/engineering claim or number used in STARDAR by cross-checking it against the RAG corpus AND recomputing it from first principles. Use when the user types /verify-claim, doubts a number, or before relying on a figure in code/docs/an answer.
---

# /verify-claim — triangulate a claim against corpus + computation

The claim/number to verify is in the arguments (e.g. "range resolution is 0.6 m at 250 MHz",
"active dwell per Starlink pass is ~5 s"). If absent, ask for the specific claim.

This skill defends *reliability*: a number must agree across three independent checks before it's
trusted. Surface disagreement loudly — do not paper over it.

## 1. Recompute from first principles
Identify the governing formula (see CLAUDE.md "Key physics" and `simulation/`), then compute the
value yourself. Prefer running the actual project code so the check matches what ships:
```bash
.venv/bin/python3 - <<'PY'
from simulation.geometry.bistatic import range_resolution
print("range_resolution(250e6) =", range_resolution(250e6), "m")
PY
```
Show the formula, inputs (with units), and the computed result.

## 2. Cross-check against the knowledge base
Query the RAG corpus for what the literature says about the same quantity:
```bash
.venv/bin/python3 - <<'PY'
import asyncio
from rag.retrieve import RAGRetriever, _get_pool
async def main():
    pool = await _get_pool()
    cols = [r["collection"] for r in await pool.fetch("SELECT DISTINCT collection FROM documents")]
    print(await RAGRetriever().retrieve("<the quantity, e.g. range resolution Starlink 250 MHz>", collections=cols, top_k=4))
asyncio.run(main())
PY
```
(Requires `docker compose up -d db`.) Read the retrieved chunks and their relevance scores.

## 3. Verdict
Compare the three sources — the **stated claim**, the **recomputed value**, and the **corpus**:
- ✅ **Confirmed** — all three agree within tolerance. State the value + the formula + the citation.
- ⚠️ **Discrepancy** — they disagree. Show each value side by side, identify the likely cause
  (wrong formula, unit error, different assumptions like dwell vs. visibility, outdated source),
  and recommend the correct value. Do NOT silently pick one.
- ❓ **Unsupported** — corpus has nothing on it. Flag as compute-only and suggest `/kb-research`.

If the claim lives in code or docs and is wrong, propose the fix and offer to add a `/write-tests`
test that pins the correct value so it can't regress.
