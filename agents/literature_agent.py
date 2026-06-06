"""
Literature Agent — retrieves and synthesizes relevant research papers,
always grounded in the RAG knowledge base.
"""

import re
from agents.base import BaseAgent, _QUESTION_PREFIX
from agents.complexity import ComplexityLevel


class LiteratureAgent(BaseAgent):
    name = "literature"
    RAG_COLLECTIONS = ["papers", "notes"]   # notes holds sync/architecture docs too

    SYSTEM_PROMPT = """You are a research assistant specializing in passive radar, bistatic SAR,
and radar signal processing literature.

Your job is to:
1. Report what the retrieved knowledge base actually contains on the topic
2. Cite specific paper titles or note filenames when you reference a finding
3. Identify which results are directly applicable to STARDAR
4. Flag gaps: topics the knowledge base does not cover, or where papers conflict

STARDAR context: passive bistatic SAR using Starlink Ku-band LEO signals, fixed ground array,
direct-path blind reference, GPS-disciplined synchronization.

Important: never fabricate paper titles, authors, or results.
If retrieved context is only partially relevant, report what IS there and note the gap —
do not simply declare "no relevant material" when context was retrieved.
"""

    ROUNDTABLE_FORMAT = """
======================================================
ROUNDTABLE OUTPUT FORMAT — YOU MUST FOLLOW THIS EXACTLY
======================================================
STANCE: <SUPPORT | OPPOSE | NEUTRAL | FLAG_RISK>
KEY_POINT: <one sentence — the most important finding from the literature>
REASONING: <cite 2–3 specific papers or notes by name with their key results relevant to this task>
RISK: <what the knowledge base does NOT cover, or where findings conflict>
======================================================
"""

    # Words that add no signal for vector search
    _STOP = re.compile(
        r"\b(what|how|which|does|is|are|can|the|a|an|be|to|of|for|"
        r"in|on|at|with|that|this|these|those|about|regarding|related|"
        r"address|cover|exist|provide|give|show|demonstrate|used|using)\b",
        re.IGNORECASE,
    )

    def _rag_query(self, task: str) -> str:
        """Strip question framing and stop words, keep technical noun phrases."""
        clean = _QUESTION_PREFIX.sub("", task.strip())
        clean = self._STOP.sub(" ", clean)
        clean = re.sub(r"\s{2,}", " ", clean).strip()
        return (clean or task)[:200]

    async def search(self, query: str) -> str:
        """Convenience method — always RAG-grounded, TRIVIAL→STANDARD complexity."""
        response = await self.run(
            task=query,
            use_rag=True,
            force_level=ComplexityLevel.STANDARD,
        )
        return response.raw
