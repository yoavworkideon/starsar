"""
BaseAgent — all domain agents inherit from this.
Each agent only needs to define:
  - SYSTEM_PROMPT  : domain expertise + output format
  - RAG_COLLECTIONS: which pgvector collections to search
  - name           : agent identifier
"""

from __future__ import annotations
import re
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
======================================================
ROUNDTABLE OUTPUT FORMAT — YOU MUST FOLLOW THIS EXACTLY
======================================================
Your response MUST use this exact structure. No prose before it, no code blocks.

STANCE: <SUPPORT | OPPOSE | NEUTRAL | FLAG_RISK>
KEY_POINT: <one sentence — the most important thing you want the team to know>
REASONING: <2–4 sentences of technical reasoning>
RISK: <the biggest risk or open question you see>
======================================================
"""

# Regex to strip question framing from task for better vector search
_QUESTION_PREFIX = re.compile(
    r"(?i)^(what|how|which|does|is|are|can|describe|explain|identify|"
    r"summarize|find|list|retrieve|cite|assess|evaluate|determine|"
    r"are there|does the|what (existing|prior|relevant|published))\b.*?\b"
    r"(research|papers?|studies|literature|work|results?|findings?)?\s+",
)


class BaseAgent:
    name: ClassVar[str] = "base"
    SYSTEM_PROMPT: ClassVar[str] = ""
    RAG_COLLECTIONS: ClassVar[list[str]] = []
    # Agents can override to use a different format in roundtable mode
    ROUNDTABLE_FORMAT: ClassVar[str] = STANCE_FORMAT

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
                query=self._rag_query(task),
                collections=self.RAG_COLLECTIONS,
                top_k=5,
            )

        # Prepend roundtable format so it takes priority over domain instructions
        system = self.SYSTEM_PROMPT
        if roundtable_mode:
            system = self.ROUNDTABLE_FORMAT + "\n\n" + system

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

    def _rag_query(self, task: str) -> str:
        """
        Extract a clean search query from the task for vector retrieval.
        Default: strip question framing so noun phrases dominate the embedding.
        Override in agents where better domain-specific extraction is needed.
        """
        clean = _QUESTION_PREFIX.sub("", task.strip())
        return (clean or task)[:200]

    @staticmethod
    def _parse_stance(text: str) -> dict:
        """
        Parse STANCE/KEY_POINT/REASONING/RISK from model output.
        Handles multi-line values: collects all text from a key until the next key.
        """
        keys = ("STANCE", "KEY_POINT", "REASONING", "RISK")
        result: dict[str, str] = {}
        current_key: str | None = None
        current_lines: list[str] = []

        for line in text.splitlines():
            matched = False
            for key in keys:
                if line.upper().startswith(key + ":"):
                    # Save previous key
                    if current_key:
                        result[current_key.lower()] = " ".join(current_lines).strip()
                    current_key = key
                    current_lines = [line.split(":", 1)[1].strip()]
                    matched = True
                    break
            if not matched and current_key:
                stripped = line.strip()
                if stripped:
                    current_lines.append(stripped)

        if current_key:
            result[current_key.lower()] = " ".join(current_lines).strip()

        return result
