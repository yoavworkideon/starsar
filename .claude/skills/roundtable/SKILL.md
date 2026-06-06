---
name: roundtable
description: Run the STARDAR multi-agent roundtable to get a deliberated, multi-expert answer to a hard domain question (bistatic geometry, signal processing, link budget / SNR, literature, or code). Use when the user types /roundtable or asks for a "roundtable", "deliberated", or "multi-agent" answer on a STARDAR question.
---

# /roundtable — run the multi-agent deliberation

The question to answer is in the skill arguments. If none was given, ask the user for it.

## Preflight (verify the stack is up)
Run these and fix/notify before launching:
```bash
docker compose up -d db                       # pgvector on :5433
curl -s http://localhost:11434/api/tags >/dev/null && echo "ollama: up" || echo "ollama: DOWN — run 'ollama serve'"
```
The roundtable needs: pgvector DB (port 5433), Ollama serving `llama3.2:3b` + `deepseek-r1:14b`,
and `ANTHROPIC_API_KEY` in `.env`. If any is missing, tell the user instead of failing silently.

## Run
```bash
.venv/bin/python3 scripts/run_roundtable_verbose.py "<the question>"
```
Use the verbose runner so the user can see the decomposition, each agent's stance, and the synthesis.

## After
Summarize the final synthesis in 3–6 bullets. Note which complexity tier each step ran at
(TRIVIAL/STANDARD → local Ollama, COMPLEX → Sonnet, CRITICAL → Opus) if it's relevant to cost/quality.
Do NOT re-answer the question yourself — report what the roundtable produced.
