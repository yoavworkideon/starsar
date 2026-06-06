---
name: ingest
description: Ingest documents (PDFs, markdown, code, notes) into the STARDAR RAG knowledge base. Use when the user types /ingest or asks to add papers/notes/docs to the knowledge base or "ingest into RAG".
---

# /ingest — add content to the RAG knowledge base

Arguments may contain a source path and/or a target collection. Resolve both before running.

## Decide the target collection
Map the content to the right collection so vector search stays clean:
- `papers` — research PDFs, formulas, theory notes
- `notes` — hand-written markdown domain notes
- `textbooks` — full textbooks (kept separate so they don't dominate `papers` in search)
- `architecture` — ARCHITECTURE.md / README / design docs
- `simulation_code` — source under `simulation/`

If the collection is ambiguous, ask. **Never** dump a textbook into `papers`.

## Preflight
```bash
docker compose up -d db
```

## Run
```bash
.venv/bin/python3 -m rag.ingest --source <path> --collection <collection>
```
Add `--reset` ONLY to wipe-and-rebuild that collection — confirm with the user first, since it
deletes all existing chunks in that collection.

## After
Report how many chunks were inserted (the command prints `Done. N chunks in collection '...'`).
Suggest running `/kb-status` to confirm the new totals, and `/rag-eval` if a lot was added.
