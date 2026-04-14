"""
Task Decomposer — breaks a high-level task into sub-questions per agent domain.
Uses Sonnet to ensure quality decomposition.
"""

import json
import logging
from agents.model_router import ModelRouter
from agents.complexity import ComplexityLevel

logger = logging.getLogger(__name__)

DECOMPOSER_SYSTEM = """You are the orchestrator for the STARDAR passive bistatic SAR project.
Your job is to decompose a high-level task into specific sub-questions, one per relevant agent domain.

Available agents and their domains:
- geometry:   bistatic range, Doppler, resolution, aperture, orbital geometry
- signal:     DSP, cross-correlation, waveform, SAR image formation algorithms
- snr:        link budget, radar equation, detectability, integration gain
- literature: relevant research papers, prior art, known limitations
- code:       Python implementation, simulation code

Rules:
1. Only include agents whose domain is directly relevant to the task
2. Each sub-question must be specific and answerable by that agent independently
3. Sub-questions should be complementary, not redundant
4. If the task is purely a code request, only include 'code' (and optionally 'signal'/'geometry')

Respond in valid JSON only:
{
  "task_summary": "<one sentence summary of the overall task>",
  "agents": {
    "<agent_name>": "<specific question for this agent>",
    ...
  }
}
"""


class TaskDecomposer:
    def __init__(self):
        self.router = ModelRouter()

    async def decompose(self, task: str) -> dict:
        """
        Decompose a task into per-agent sub-questions.
        Returns dict: { "task_summary": str, "agents": { agent_name: question } }
        """
        raw = await self.router.run(
            task=task,
            system_prompt=DECOMPOSER_SYSTEM,
            force_level=ComplexityLevel.COMPLEX,  # Sonnet — quality decomposition
        )

        try:
            # Extract JSON even if model adds prose around it
            start = raw.find("{")
            end   = raw.rfind("}") + 1
            return json.loads(raw[start:end])
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Decomposer failed to parse JSON: %s\nRaw: %s", e, raw)
            # Fallback: send to all agents
            return {
                "task_summary": task,
                "agents": {
                    "geometry":   task,
                    "signal":     task,
                    "snr":        task,
                    "literature": task,
                },
            }
