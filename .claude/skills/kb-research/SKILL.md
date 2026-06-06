---
name: kb-research
description: Gather new domain knowledge on a STARDAR topic from the web, distill it into a cited note, and ingest it into the RAG knowledge base. Use when the user types /kb-research or asks to "research X and add it to the knowledge base" / "expand the knowledge base on Y".
---

# /kb-research — grow the knowledge base from new sources

This is the *knowledge-gathering* pipeline: research → distill → cite → ingest. The goal is a
curated, trustworthy note — not raw dumps.

The topic is in the arguments. If absent, ask what to research.

## 1. Research
Use the `deep-research` skill (preferred) or web search to gather multiple independent sources on
the topic. Prioritize: peer-reviewed papers, primary technical specs, and reputable measurements
over blogs. For STARDAR, weight passive radar / bistatic SAR / Starlink-signal literature.

## 2. Distill into a cited note
Write `data/notes/<slug>.md` with:
- A short summary of the established facts / numbers (with units).
- **Every non-trivial claim carries an inline citation** (author/title/year or URL).
- A "Confidence / open questions" section — be explicit about what's contested or unverified.
- Cross-references to existing project numbers (compare against CLAUDE.md physics).

## 3. Ingest
```bash
docker compose up -d db
.venv/bin/python3 -m rag.ingest --source data/notes/<slug>.md --collection notes
```
Use `notes` for distilled markdown; `papers` if you also downloaded source PDFs into `data/papers/`.

## 4. Verify it landed cleanly
Run `/rag-eval` with 2–3 probe questions about the new topic to confirm the new content is
retrievable and ranks above noise. Report what was added and its citations.

## Quality bar
Never ingest unsourced claims. If sources conflict, record both and flag it — do not silently pick one.
