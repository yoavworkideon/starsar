"""
Roundtable Orchestrator — the main entry point for multi-agent deliberation.

Flow:
  1. Decompose task into per-agent sub-questions
  2. Gather initial stances from all relevant agents (parallel)
  3. Deliberation round — agents cross-examine each other (Sonnet-mediated)
  4. Synthesis — Opus produces action plan + reasoning chain
  5. Return review card to user for approval
  6. On approval: hand off to CodeAgent for implementation
"""

import asyncio
import logging
from dataclasses import dataclass, field

from agents import GeometryAgent, SignalAgent, SNRAgent, LiteratureAgent, CodeAgent
from agents.base import AgentResponse
from agents.complexity import ComplexityLevel
from agents.model_router import ModelRouter
from orchestrator.decomposer import TaskDecomposer
from orchestrator.synthesizer import Synthesizer, SynthesisResult

logger = logging.getLogger(__name__)

DELIBERATION_SYSTEM = """You are the STARDAR roundtable moderator.
You have received initial stances from domain agents. Your job is to:
1. Identify the key tensions or disagreements between agents
2. Pose one pointed follow-up question to each agent that challenged another's position
3. Summarize the resulting clarifications into a deliberation log

Be concise. The goal is to surface conflicts and resolve them — not to generate more questions.
"""

_AGENT_REGISTRY = {
    "geometry":   GeometryAgent,
    "signal":     SignalAgent,
    "snr":        SNRAgent,
    "literature": LiteratureAgent,
    "code":       CodeAgent,
}


@dataclass
class RoundtableResult:
    task:             str
    decomposition:    dict
    agent_responses:  list[AgentResponse]
    deliberation_log: list[str]
    synthesis:        SynthesisResult
    awaiting_approval: bool = True


class Roundtable:
    def __init__(self):
        self.decomposer  = TaskDecomposer()
        self.synthesizer = Synthesizer()
        self.router      = ModelRouter()

    async def run(self, task: str) -> RoundtableResult:
        """Full roundtable pipeline. Returns review card — does NOT implement."""

        # ── Step 1: Decompose ──────────────────────────────────────────
        logger.info("Step 1: Decomposing task")
        decomp = await self.decomposer.decompose(task)
        agent_questions: dict[str, str] = decomp.get("agents", {})

        # ── Step 2: Gather initial stances (parallel) ──────────────────
        logger.info("Step 2: Gathering stances from %s", list(agent_questions.keys()))
        stances = await self._gather_stances(agent_questions)

        # ── Step 3: Deliberation round ─────────────────────────────────
        logger.info("Step 3: Deliberation")
        deliberation = await self._deliberate(task, stances)

        # ── Step 4: Synthesis (Opus) ───────────────────────────────────
        logger.info("Step 4: Synthesis")
        synthesis = await self.synthesizer.synthesize(task, stances, deliberation)

        return RoundtableResult(
            task=task,
            decomposition=decomp,
            agent_responses=stances,
            deliberation_log=deliberation,
            synthesis=synthesis,
            awaiting_approval=True,
        )

    def format_review_card(self, result: RoundtableResult) -> str:
        """Format the review card shown to the user before implementation."""
        lines = [
            "=" * 70,
            "STARDAR ROUNDTABLE — REVIEW CARD",
            "=" * 70,
            f"\nTASK: {result.task}\n",
            "── AGENT CONTRIBUTIONS ──────────────────────────────────────────",
        ]
        for r in result.agent_responses:
            model_short = r.model_used.split("/")[-1] if "/" in r.model_used else r.model_used
            lines.append(f"\n[{r.agent.upper()}] via {model_short} ({r.complexity})")
            if r.stance:
                lines.append(f"  Stance:    {r.stance}")
                lines.append(f"  Key point: {r.key_point}")
                lines.append(f"  Risk:      {r.risk}")
            else:
                lines.append(f"  {r.raw[:300]}...")

        if result.deliberation_log:
            lines.append("\n── DELIBERATION ─────────────────────────────────────────────────")
            lines.extend(result.deliberation_log)

        lines.append("\n── SYNTHESIS (Opus) ─────────────────────────────────────────────")
        lines.append(result.synthesis.plan)
        lines.append("\n" + "=" * 70)
        lines.append("Approve to proceed to implementation? [yes / modify / abort]")
        lines.append("=" * 70)

        return "\n".join(lines)

    # ── Internal ───────────────────────────────────────────────────────

    async def _gather_stances(self, agent_questions: dict[str, str]) -> list[AgentResponse]:
        tasks = []
        for agent_name, question in agent_questions.items():
            cls = _AGENT_REGISTRY.get(agent_name)
            if not cls:
                logger.warning("Unknown agent '%s', skipping", agent_name)
                continue
            agent = cls()
            tasks.append(agent.run(question, roundtable_mode=True))

        return list(await asyncio.gather(*tasks))

    async def _deliberate(self, task: str, stances: list[AgentResponse]) -> list[str]:
        """One deliberation round — Sonnet identifies tensions and resolves them."""
        context = "\n\n".join(
            f"[{r.agent}] STANCE={r.stance} | KEY={r.key_point} | RISK={r.risk}"
            for r in stances
        )
        raw = await self.router.run(
            task=f"Identify and resolve key tensions in the agent stances for task: {task}",
            system_prompt=DELIBERATION_SYSTEM,
            context=context,
            force_level=ComplexityLevel.COMPLEX,  # Sonnet
        )
        return [raw]
