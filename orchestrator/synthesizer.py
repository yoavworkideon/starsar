"""
Synthesizer — Opus-powered. Takes all agent stances + deliberation,
produces the final action plan with full reasoning chain.
"""

from dataclasses import dataclass
from agents.model_router import ModelRouter
from agents.complexity import ComplexityLevel
from agents.base import AgentResponse

SYNTHESIZER_SYSTEM = """You are the lead architect of the STARDAR passive bistatic SAR project.
You have received inputs from domain experts (geometry, signal processing, SNR, literature, code).
Your job is to synthesize their inputs into a clear, actionable plan.

Output format — use this EXACT structure:

## Task
<restate the original task in one sentence>

## Agent Inputs Summary
<for each agent that contributed, one bullet: agent name + their key point + stance>

## Reasoning Chain
<numbered steps showing how you arrived at the plan — connect the agent inputs>

## Decision
<what we will do — be specific>

## Action Plan
<numbered steps to execute the decision>

## Open Questions
<unresolved risks or questions that need user input before proceeding>

## Recommendation
<your honest recommendation — including if you think the task is not yet ready for implementation>
"""


@dataclass
class SynthesisResult:
    task:            str
    agent_responses: list[AgentResponse]
    plan:            str   # full formatted output
    ready_to_implement: bool


class Synthesizer:
    def __init__(self):
        self.router = ModelRouter()

    async def synthesize(
        self,
        task: str,
        agent_responses: list[AgentResponse],
        deliberation_log: list[str] | None = None,
    ) -> SynthesisResult:
        """
        Synthesize agent stances into an actionable plan.
        Always uses Opus — this is the critical synthesis step.
        """
        context = self._format_context(agent_responses, deliberation_log)

        plan = await self.router.run(
            task=f"Synthesize the following agent inputs and produce an action plan for:\n\n{task}",
            system_prompt=SYNTHESIZER_SYSTEM,
            context=context,
            force_level=ComplexityLevel.CRITICAL,  # always Opus
        )

        ready = "OPEN QUESTIONS" not in plan.upper() or "none" in plan.lower()

        return SynthesisResult(
            task=task,
            agent_responses=agent_responses,
            plan=plan,
            ready_to_implement=ready,
        )

    @staticmethod
    def _format_context(responses: list[AgentResponse], deliberation: list[str] | None) -> str:
        lines = ["=== AGENT STANCES ===\n"]
        for r in responses:
            lines.append(f"[{r.agent.upper()}] (complexity: {r.complexity}, model: {r.model_used})")
            if r.stance:
                lines.append(f"  STANCE:     {r.stance}")
                lines.append(f"  KEY_POINT:  {r.key_point}")
                lines.append(f"  REASONING:  {r.reasoning}")
                lines.append(f"  RISK:       {r.risk}")
            else:
                lines.append(f"  {r.raw[:500]}")
            lines.append("")

        if deliberation:
            lines.append("=== DELIBERATION LOG ===\n")
            lines.extend(deliberation)

        return "\n".join(lines)
