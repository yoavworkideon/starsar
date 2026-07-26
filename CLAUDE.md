# STARDAR — Claude Code Project Guide

Passive **bistatic SAR** using Starlink LEO satellites as an uncooperative illuminator of
opportunity (Ku-band, ~12 GHz, up to 250 MHz BW). The system only receives — no RF emission.
Primary application: terrain mapping from elevated ground positions.

Full system design lives in [ARCHITECTURE.md](./ARCHITECTURE.md). This file is the operating
manual for working in the repo.

## ⚠️ Critical conventions (read first)

- **Always use `.venv/bin/python3`** — never the system `python3`. The project runs on Python 3.14.
- **The pgvector DB runs in Docker on host port `5433`** (mapped to container 5432) to avoid a
  conflict with a local `postgres@14`. Connection string in `.env` as `DATABASE_URL`.
- **The agent/RAG system uses `requirements-agents.txt`**, not `requirements.txt`. The README's
  `pip install -r requirements.txt` covers only the simulation code.
- **Ollama runs locally on the host** (not in Docker): models `llama3.2:3b` and `deepseek-r1:14b`
  must be pulled and `ollama serve` running before the roundtable will work.
- Secrets live in `.env` (gitignored): `DATABASE_URL`, `ANTHROPIC_API_KEY`, `OLLAMA_HOST`.
- **Optional LiteLLM gateway (cost-router):** set `STARDAR_GATEWAY_URL` (gateway base URL — with or
  without a trailing `/anthropic`), `STARDAR_GATEWAY_KEY` (LiteLLM virtual key — a secret), and
  `STARDAR_CLIENT_TAG` (Langfuse tag, default `stardar`) to route Claude calls **and** the difficulty
  classifier (`router` alias) through the gateway for centralized routing + Langfuse cost logging.
  Unset = call Anthropic/Ollama directly (unchanged behavior). See `agents/model_router.py`.

## Setup / run

```bash
# 1. Start the database
docker compose up -d db                 # pgvector on localhost:5433

# 2. Install agent deps (once)
.venv/bin/python3 -m pip install -r requirements-agents.txt

# 3. Build the knowledge base (once, after DB is up)
bash scripts/build_knowledge_base.sh

# 4. Run the roundtable
.venv/bin/python3 scripts/run_roundtable_verbose.py "your question here"
```

`run_roundtable_verbose.py` is the runner to use for debugging (full trace). `run_roundtable.py`
is the quiet version. `scripts/test_stack.py` is the integration smoke test.

## Architecture — three layers

1. **Knowledge (`rag/`)** — pgvector store; vector search + CrossEncoder rerank.
   - `embeddings.py` — sentence-transformers `all-MiniLM-L6-v2` (384-dim), `embed_one()`.
   - `ingest.py` — `python -m rag.ingest --source <path> --collection <name> [--reset]`.
   - `retrieve.py` — `RAGRetriever.retrieve(query, collections: list[str], top_k=5) -> str`
     (returns a formatted, context-ready string; module-level asyncpg pool + reranker singletons).

2. **Expertise (`agents/`)** — 5 domain agents, all subclass `BaseAgent` (each defines a
   `name` + `SYSTEM_PROMPT`, pulls its own RAG context):
   - `GeometryAgent` (`geometry`), `SignalAgent` (`signal`), `SNRAgent` (`snr`),
     `LiteratureAgent` (`literature`, RAG-backed), `CodeAgent` (`code`, forces ≥ COMPLEX).
   - `model_router.py` — cross-cutting infra. Routes each call by assessed complexity:
     `TRIVIAL → llama3.2:3b`, `STANDARD → deepseek-r1:14b`, `COMPLEX → claude-sonnet-5`,
     `CRITICAL → claude-opus-5`. Assessor (`complexity.py`) classifies via llama3.2:3b at temp 0.
     Anthropic client is a singleton with prompt caching enabled.

3. **Orchestration (`orchestrator/`)** — the roundtable pipeline:
   `decomposer.py` (split question into tasks) → agents emit stances → deliberate (Sonnet) →
   `synthesizer.py` (always Opus / CRITICAL) → final answer.

## RAG collections

Created by `scripts/build_knowledge_base.sh`: **`architecture`**, **`simulation_code`**, **`papers`**.
Additional collections may exist in the live DB (e.g. `textbooks`, `notes`) created manually —
the Cumming & Wong SAR textbook was split into its own `textbooks` collection so it doesn't
dominate vector search over `papers`. When in doubt, list distinct collections from the DB rather
than assuming.

Add research PDFs: `.venv/bin/python3 -m rag.ingest --source data/papers/ --collection papers`

## Key physics / numbers

- Range resolution: `c / 2B ≈ 0.6 m` at 250 MHz.
- Bistatic Doppler: `f_d = -(1/λ) · d(R_T + R_R)/dt`.
- Active dwell per Starlink pass is **~1.7–7 s** (Warsaw 2024), *not* the ~480 s orbital visibility.
- GPSDO alone is insufficient for 250 MHz sync — signal-level sync (SLS) is mandatory.

## Current state (2026-06-06)

- Repo has **uncommitted changes** across `agents/`, `orchestrator/`, `rag/` plus untracked
  scripts (`run_roundtable*.py`, `test_stack.py`) and `data/papers/`. Commit before large refactors.
- **`tests/` is effectively empty** (only `__init__.py`) — there is no automated test coverage yet.
  Treat any refactor of the physics/simulation modules as unverified until tests exist.

## Conventions for changes

- Keep model IDs centralized in `agents/model_router.py` (constants `_SONNET`, `_OPUS`, etc.).
- New blocking calls (DB, ML inference, ollama) must be wrapped in `asyncio.to_thread()` — the
  event loop must stay alive during inference (see notes in `rag/retrieve.py`).
- After adding a new function or service, add a matching test under `tests/` (mirroring the module
  path) before considering the work done.
