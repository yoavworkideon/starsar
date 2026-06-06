---
name: write-tests
description: Write pytest tests for a STARDAR function, module, or service. Use when the user types /write-tests, asks to add/write tests for something, or after adding a new function/service that lacks coverage.
---

# /write-tests — generate pytest coverage for a target

The target (file, function, or module) is in the arguments. If absent, ask what to test, or offer
to scan `simulation/`, `rag/`, `agents/`, `orchestrator/` for public functions lacking tests.

## Approach
1. **Read the target** and understand its contract: inputs, outputs, units, edge cases, and any
   physics/math it implements.
2. **Place the test mirroring the source path** under `tests/` — e.g.
   `simulation/geometry/bistatic.py` → `tests/simulation/geometry/test_bistatic.py`.
   Create `__init__.py` files / dirs as needed.
3. **Write `pytest` tests** that cover:
   - Nominal cases with **known physical values** (e.g. `range_resolution(250e6) ≈ 0.6 m`, within tol).
     Anchor expected numbers to CLAUDE.md / ARCHITECTURE.md, not to whatever the code happens to return.
   - Edge cases: zero/negative inputs, boundary geometry, empty inputs.
   - For async code (`rag/`, `agents/`, `orchestrator/`): use `pytest.mark.asyncio`.
   - For code touching the DB / Anthropic / Ollama: **mock the external call** — tests must run
     offline and deterministically. Do not hit the live DB or API in unit tests.
4. Use `pytest.approx` / `math.isclose` for floats with explicit tolerances.

## Run and report
```bash
.venv/bin/python3 -m pytest tests/ -q
```
If `pytest`/`pytest-asyncio` aren't installed, add them to `requirements-agents.txt` and install.
Report pass/fail honestly with the output. If a test fails because the **code** is wrong (not the
test), say so and propose the fix — don't bend the test to pass.

## Definition of done
A new function/service is "done" only when it has a matching test here that passes offline.
