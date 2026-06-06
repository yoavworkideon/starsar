"""
Verbose roundtable runner — shows full reasoning chain at every step:
  decomposition → per-agent RAG query + retrieved context → stances → deliberation → synthesis
"""
import signal
signal.signal(signal.SIGURG, signal.SIG_IGN)  # Prevent exit 144 on TCP urgent data

import asyncio, os, sys, logging, time

try:
    import uvloop
    _loop_factory = uvloop.new_event_loop  # Python 3.12+ API — no deprecation warning
except ImportError:
    _loop_factory = None

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
logging.basicConfig(level=logging.WARNING)

from agents import GeometryAgent, SignalAgent, SNRAgent, LiteratureAgent, CodeAgent
from agents.base import AgentResponse
from agents.complexity import ComplexityLevel
from agents.model_router import ModelRouter
from orchestrator.decomposer import TaskDecomposer
from orchestrator.synthesizer import Synthesizer
from rag.retrieve import RAGRetriever

SEP  = "─" * 70
SEP2 = "═" * 70

AGENT_REGISTRY = {
    "geometry":   GeometryAgent,
    "signal":     SignalAgent,
    "snr":        SNRAgent,
    "literature": LiteratureAgent,
    "code":       CodeAgent,
}

TASK = sys.argv[1] if len(sys.argv) > 1 else ""


def hr(title=""):
    if title:
        pad = (70 - len(title) - 2) // 2
        print(f"\n{'─'*pad} {title} {'─'*pad}")
    else:
        print(SEP)


async def run_agent_verbose(name: str, question: str) -> AgentResponse:
    cls = AGENT_REGISTRY[name]
    agent = cls()

    rag_query = agent._rag_query(question)
    print(f"\n  Sub-question : {question[:150]}")
    print(f"  RAG query    : {rag_query[:150]}")
    print(f"  Collections  : {agent.RAG_COLLECTIONS}")

    t0 = time.time()
    # agent.run() handles RAG internally — no double retrieval
    response = await agent.run(question, roundtable_mode=True, force_level=ComplexityLevel.COMPLEX)
    elapsed = time.time() - t0

    print(f"\n  Model        : {response.model_used} ({elapsed:.1f}s)")
    print(f"  STANCE       : {response.stance or '[parse failed]'}")
    print(f"  KEY_POINT    : {response.key_point or '[empty]'}")
    print(f"  REASONING    : {(response.reasoning or '[empty]')[:300]}")
    print(f"  RISK         : {(response.risk or '[empty]')[:200]}")

    return response


async def main():
    print(f"\n{SEP2}")
    print("  STARDAR ROUNDTABLE — VERBOSE")
    print(SEP2)
    print(f"\nTASK: {TASK}\n")

    # ── Step 1: Decompose ────────────────────────────────────────────────
    hr("STEP 1 — DECOMPOSE (Sonnet)")
    decomposer = TaskDecomposer()
    t0 = time.time()
    decomp = await decomposer.decompose(TASK)
    print(f"\n  Summary: {decomp.get('task_summary', '—')}")
    print(f"  Agents selected: {list(decomp.get('agents', {}).keys())}")
    print(f"  Decomposition took {time.time()-t0:.1f}s")

    # ── Step 2: Gather stances ───────────────────────────────────────────
    hr("STEP 2 — AGENT STANCES (parallel)")
    agent_questions: dict[str, str] = decomp.get("agents", {})

    stances = []
    for name, question in agent_questions.items():
        if name not in AGENT_REGISTRY:
            continue
        hr(f"  {name.upper()}")
        try:
            response = await run_agent_verbose(name, question)
            stances.append(response)
        except Exception as e:
            print(f"\n  ❌ [{name}] FAILED: {e}")

    # ── Step 3: Deliberation ─────────────────────────────────────────────
    hr("STEP 3 — DELIBERATION (Sonnet)")
    router = ModelRouter()

    DELIBERATION_SYSTEM = """You are the STARDAR roundtable moderator.
You have received initial stances from domain agents. Your job is to:
1. Identify the key tensions or disagreements between agents
2. Pose one pointed follow-up question to each agent that challenged another's position
3. Summarize the resulting clarifications into a deliberation log

Be concise. The goal is to surface conflicts and resolve them — not to generate more questions.
"""
    context = "\n\n".join(
        f"[{r.agent}] STANCE={r.stance} | KEY={r.key_point} | RISK={r.risk}"
        for r in stances
    )
    t0 = time.time()
    deliberation = await router.run(
        task=f"Identify and resolve key tensions in the agent stances for task: {TASK}",
        system_prompt=DELIBERATION_SYSTEM,
        context=context,
        force_level=ComplexityLevel.COMPLEX,
    )
    print(f"\n{deliberation}\n")
    print(f"  Deliberation took {time.time()-t0:.1f}s")

    # ── Step 4: Synthesis ────────────────────────────────────────────────
    hr("STEP 4 — SYNTHESIS (Opus)")
    synthesizer = Synthesizer()
    t0 = time.time()
    synthesis = await synthesizer.synthesize(TASK, stances, [deliberation])
    print(f"\n{synthesis.plan}\n")
    print(f"  Synthesis took {time.time()-t0:.1f}s")

    print(f"\n{SEP2}")
    print("  ROUNDTABLE COMPLETE")
    print(SEP2)


if __name__ == "__main__":
    # Use uvloop's loop_factory (Python 3.12+ API) — avoids deprecated set_event_loop_policy
    asyncio.run(main(), **{"loop_factory": _loop_factory} if _loop_factory else {})
