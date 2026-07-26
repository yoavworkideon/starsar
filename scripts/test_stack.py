"""
STARDAR Stack Integration Test
Runs sequentially through all system layers:
  1. DB connectivity
  2. RAG retrieval
  3. Complexity assessor (llama3.2:3b)
  4. Model routing — TRIVIAL (llama3.2:3b)
  5. Model routing — STANDARD (deepseek-r1:14b)
  6. Model routing — COMPLEX (Sonnet) *requires API key*
  7. Full roundtable pipeline *requires API key*
"""

import signal
signal.signal(signal.SIGURG, signal.SIG_IGN)  # Prevent exit 144 on TCP urgent data

import asyncio
import os
import sys
import logging
import time

try:
    import uvloop
    _loop_factory = uvloop.new_event_loop
except ImportError:
    _loop_factory = None

# Make project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

logging.basicConfig(level=logging.WARNING)  # Suppress noisy logs during tests

PASS = "✅"
FAIL = "❌"
SKIP = "⏭ "
SEP  = "─" * 60


def section(title: str):
    print(f"\n{SEP}\n  {title}\n{SEP}")


def ok(msg: str):
    print(f"  {PASS}  {msg}")


def fail(msg: str):
    print(f"  {FAIL}  {msg}")


def skip(msg: str):
    print(f"  {SKIP}  {msg}")


# ── 1. DB connectivity ─────────────────────────────────────────────────────────

async def test_db():
    section("1. DB CONNECTIVITY")
    try:
        import asyncpg
        url = os.environ.get("DATABASE_URL", "postgresql://stardar:stardar@localhost:5433/stardar")
        conn = await asyncpg.connect(url)
        row = await conn.fetchrow("SELECT COUNT(*) AS n FROM documents")
        await conn.close()
        count = row["n"]
        ok(f"Connected to PostgreSQL — {count} documents in DB")
        return True
    except Exception as e:
        fail(f"DB connection failed: {e}")
        return False


# ── 2. RAG retrieval ───────────────────────────────────────────────────────────

async def test_rag():
    section("2. RAG RETRIEVAL (pgvector + CrossEncoder)")
    try:
        from rag.retrieve import RAGRetriever
        retriever = RAGRetriever()

        t0 = time.time()
        result = await retriever.retrieve(
            query="bistatic SAR range resolution Starlink",
            collections=["papers", "notes"],
            top_k=3,
        )
        elapsed = time.time() - t0

        if result:
            preview = result[:200].replace("\n", " ")
            ok(f"Retrieved context ({elapsed:.1f}s): {preview}...")
            return True
        else:
            fail("RAG returned empty result")
            return False
    except Exception as e:
        fail(f"RAG failed: {e}")
        return False


# ── 3. Complexity assessor ─────────────────────────────────────────────────────

async def test_assessor():
    section("3. COMPLEXITY ASSESSOR (llama3.2:3b)")
    from agents.model_router import ModelRouter
    from agents.complexity import ComplexityLevel

    # Temporarily patch API key if missing (assessor doesn't use Anthropic)
    os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-for-assessor-test")
    router = ModelRouter()

    # (expected_min, expected_max) — assessor may conservatively upgrade tier
    cases = [
        ("What is the range resolution for 250 MHz bandwidth?",
         ComplexityLevel.TRIVIAL, ComplexityLevel.STANDARD),
        ("Compare coherent vs non-coherent SAR focusing approaches for bistatic geometry",
         ComplexityLevel.STANDARD, ComplexityLevel.COMPLEX),
        ("Implement a range-Doppler algorithm for passive bistatic SAR processing",
         ComplexityLevel.COMPLEX, ComplexityLevel.CRITICAL),
    ]

    _order = list(ComplexityLevel)

    all_ok = True
    for task, min_level, max_level in cases:
        try:
            t0 = time.time()
            level = await router.assess(task)
            elapsed = time.time() - t0
            in_range = _order.index(min_level) <= _order.index(level) <= _order.index(max_level)
            status = PASS if in_range else FAIL
            print(f"  {status}  [{elapsed:.1f}s] '{task[:55]}...' → {level} (expected {min_level}–{max_level})")
            if not in_range:
                all_ok = False
        except Exception as e:
            fail(f"Assessor error: {e}")
            all_ok = False

    return all_ok


# ── 4. TRIVIAL routing (llama3.2:3b) ──────────────────────────────────────────

async def test_trivial_route():
    section("4. MODEL ROUTING — TRIVIAL (llama3.2:3b)")
    try:
        from agents.model_router import ModelRouter
        from agents.complexity import ComplexityLevel
        os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
        router = ModelRouter()

        t0 = time.time()
        response = await router.run(
            task="What is the speed of light in m/s?",
            system_prompt="You are a physics expert. Answer in one sentence.",
            force_level=ComplexityLevel.TRIVIAL,
        )
        elapsed = time.time() - t0
        preview = response[:120].replace("\n", " ")
        ok(f"llama3.2:3b responded ({elapsed:.1f}s): {preview}...")
        return True
    except Exception as e:
        fail(f"TRIVIAL route failed: {e}")
        return False


# ── 5. STANDARD routing (deepseek-r1:14b) ─────────────────────────────────────

async def test_standard_route():
    section("5. MODEL ROUTING — STANDARD (deepseek-r1:14b)")
    try:
        from agents.model_router import ModelRouter
        from agents.complexity import ComplexityLevel
        os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
        router = ModelRouter()

        t0 = time.time()
        response = await router.run(
            task="Calculate the bistatic Doppler frequency for a Starlink satellite at 550 km altitude, "
                 "moving at 7.6 km/s, when the target is at 20 km ground range from the receiver.",
            system_prompt="You are a bistatic radar geometry expert. Show your calculation steps.",
            force_level=ComplexityLevel.STANDARD,
        )
        elapsed = time.time() - t0
        preview = response[:200].replace("\n", " ")
        ok(f"deepseek-r1:14b responded ({elapsed:.1f}s): {preview}...")
        return True
    except Exception as e:
        fail(f"STANDARD route failed: {e}")
        return False


# ── 6. COMPLEX routing (Sonnet) ────────────────────────────────────────────────

async def test_complex_route():
    section("6. MODEL ROUTING — COMPLEX (claude-sonnet-5)")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "dummy" or api_key == "REPLACE_ME":
        skip("No ANTHROPIC_API_KEY — skipping Sonnet/Opus tests")
        return None

    try:
        from agents.model_router import ModelRouter
        from agents.complexity import ComplexityLevel
        router = ModelRouter()

        t0 = time.time()
        response = await router.run(
            task="Explain the key challenge in achieving SAR focusing for a passive bistatic "
                 "system where the transmitter trajectory is only approximately known.",
            system_prompt="You are a SAR signal processing expert. Be concise and technical.",
            force_level=ComplexityLevel.COMPLEX,
        )
        elapsed = time.time() - t0
        preview = response[:200].replace("\n", " ")
        ok(f"Sonnet responded ({elapsed:.1f}s): {preview}...")
        return True
    except Exception as e:
        fail(f"COMPLEX route failed: {e}")
        return False


# ── 7. Geometry agent + RAG (full agent run) ───────────────────────────────────

async def test_geometry_agent():
    section("7. GEOMETRY AGENT — full run (RAG + routing)")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "dummy" or api_key == "REPLACE_ME":
        skip("No ANTHROPIC_API_KEY — skipping agent tests")
        return None

    try:
        from agents import GeometryAgent
        from agents.complexity import ComplexityLevel
        agent = GeometryAgent()

        t0 = time.time()
        response = await agent.run(
            task="For a Starlink satellite pass at 550 km altitude with 250 MHz bandwidth, "
                 "what is the theoretical cross-range resolution at the end of an 8-minute aperture? "
                 "Compare with range resolution.",
            force_level=ComplexityLevel.COMPLEX,
        )
        elapsed = time.time() - t0
        ok(f"GeometryAgent completed ({elapsed:.1f}s), model={response.model_used}, complexity={response.complexity}")
        ok(f"Response preview: {response.raw[:200].replace(chr(10), ' ')}...")
        return True
    except Exception as e:
        fail(f"GeometryAgent failed: {e}")
        return False


# ── 8. Full roundtable ─────────────────────────────────────────────────────────

async def test_roundtable():
    section("8. FULL ROUNDTABLE PIPELINE")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "dummy" or api_key == "REPLACE_ME":
        skip("No ANTHROPIC_API_KEY — skipping roundtable test")
        return None

    try:
        from orchestrator.roundtable import Roundtable
        rt = Roundtable()

        t0 = time.time()
        result = await rt.run(
            "What is the feasibility of achieving sub-meter resolution SAR imaging "
            "of terrain at 20 km range using a single Starlink satellite pass?"
        )
        elapsed = time.time() - t0

        ok(f"Roundtable completed ({elapsed:.1f}s)")
        ok(f"Agents that responded: {[r.agent for r in result.agent_responses]}")
        ok(f"Deliberation rounds: {len(result.deliberation_log)}")
        card = rt.format_review_card(result)
        print("\n" + card[:1000] + "\n  [... truncated ...]")
        return True
    except Exception as e:
        fail(f"Roundtable failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "=" * 60)
    print("  STARDAR STACK INTEGRATION TEST")
    print("=" * 60)

    results = {}

    results["db"]       = await test_db()
    results["rag"]      = await test_rag()
    results["assessor"] = await test_assessor()
    results["trivial"]  = await test_trivial_route()
    results["standard"] = await test_standard_route()
    results["complex"]  = await test_complex_route()
    results["agent"]    = await test_geometry_agent()
    results["roundtable"] = await test_roundtable()

    # Summary
    section("SUMMARY")
    for name, status in results.items():
        if status is True:
            print(f"  {PASS}  {name}")
        elif status is False:
            print(f"  {FAIL}  {name}")
        else:
            print(f"  {SKIP}  {name} (skipped — no API key)")

    failed = [k for k, v in results.items() if v is False]
    skipped = [k for k, v in results.items() if v is None]

    print()
    if not failed:
        if skipped:
            print(f"  All local tests passed. {len(skipped)} Anthropic test(s) skipped — add API key to run full stack.")
        else:
            print("  All tests passed.")
    else:
        print(f"  {len(failed)} test(s) FAILED: {failed}")

    print()


if __name__ == "__main__":
    asyncio.run(main(), **{"loop_factory": _loop_factory} if _loop_factory else {})
