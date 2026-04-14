"""
BaseAgent — all domain agents inherit from this.
Each agent only needs to define:
  - SYSTEM_PROMPT  : domain expertise + output format
  - RAG_COLLECTIONS: which pgvector collections to search
  - name           : agent identifier
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import ClassVar

from agents.complexity import ComplexityLevel
from agents.model_router import ModelRouter
from rag.retrieve import RAGRetriever


@dataclass
class AgentResponse:
    agent:      str
    task:       str
    complexity: ComplexityLevel
    model_used: str
    stance:     str   # SUPPORT / OPPOSE / NEUTRAL / FLAG_RISK
    key_point:  str
    reasoning:  str
    risk:       str
    raw:        str   # full model output


STANCE_FORMAT = """
Your response MUST follow this exact structure (used by the roundtable orchestrator):

STANCE: <SUPPORT | OPPOSE | NEUTRAL | FLAG_RISK>
KEY_POINT: <one sentence — the most important thing you want the team to know>
REASONING: <2–4 sentences of technical reasoning>
RISK: <the biggest risk or open question you see>
"""


class BaseAgent:
    name: ClassVar[str] = "base"
    SYSTEM_PROMPT: ClassVar[str] = ""
    RAG_COLLECTIONS: ClassVar[list[str]] = []

    def __init__(self):
        self.router    = ModelRouter()
        self.retriever = RAGRetriever()

    async def run(
        self,
        task: str,
        use_rag: bool = True,
        force_level: ComplexityLevel | None = None,
        roundtable_mode: bool = False,
    ) -> AgentResponse:
        """
        Execute a task. Automatically selects model based on complexity.

        Args:
            task:           Task or question for this agent
            use_rag:        Whether to retrieve relevant context first
            force_level:    Override complexity assessment
            roundtable_mode: Enforce STANCE format in output
        """
        context = ""
        if use_rag and self.RAG_COLLECTIONS:
            context = await self.retriever.retrieve(
                query=task,
                collections=self.RAG_COLLECTIONS,
                top_k=5,
            )

        system = self.SYSTEM_PROMPT
        if roundtable_mode:
            system = system + "\n\n" + STANCE_FORMAT

        level = force_level or await self.router.assess(task)
        raw   = await self.router.run(
            task=task,
            system_prompt=system,
            context=context,
            force_level=level,
        )

        _, model_id = self.router._MODEL_MAP[level]  # for logging
        parsed = self._parse_stance(raw) if roundtable_mode else {}

        return AgentResponse(
            agent=self.name,
            task=task,
            complexity=level,
            model_used=model_id,
            stance=parsed.get("stance",     ""),
            key_point=parsed.get("key_point",""),
            reasoning=parsed.get("reasoning",""),
            risk=parsed.get("risk",          ""),
            raw=raw,
        )

    @staticmethod
    def _parse_stance(text: str) -> dict:
        """Parse STANCE/KEY_POINT/REASONING/RISK from model output."""
        result = {}
        for line in text.splitlines():
            for key in ("STANCE", "KEY_POINT", "REASONING", "RISK"):
                if line.upper().startswith(key + ":"):
                    result[key.lower()] = line.split(":", 1)[1].strip()
        return result
