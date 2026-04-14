"""
Literature Agent — retrieves and synthesizes relevant research papers,
always grounded in the RAG knowledge base.
"""

from agents.base import BaseAgent
from agents.complexity import ComplexityLevel


class LiteratureAgent(BaseAgent):
    name = "literature"
    RAG_COLLECTIONS = ["papers"]

    SYSTEM_PROMPT = """You are a research assistant specializing in passive radar, bistatic SAR,
and radar signal processing literature.

Your job is to:
1. Retrieve the most relevant papers from the knowledge base for a given topic
2. Summarize key findings concisely
3. Identify which results are directly applicable to STARDAR
4. Flag papers that contradict each other or suggest our approach has known limitations

STARDAR context: passive bistatic SAR using Starlink Ku-band LEO signals, fixed ground array,
direct-path blind reference, GPS-disciplined synchronization.

Important: never fabricate paper titles, authors, or results.
If the knowledge base does not contain relevant material, say so explicitly.
"""

    async def search(self, query: str) -> str:
        """Convenience method — always RAG-grounded, TRIVIAL→STANDARD complexity."""
        response = await self.run(
            task=query,
            use_rag=True,
            force_level=ComplexityLevel.STANDARD,
        )
        return response.raw
