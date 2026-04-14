"""
Code Agent — Python implementation, simulation code review, debugging.
Always routes to Sonnet minimum (code tasks are never TRIVIAL/STANDARD).
"""

from agents.base import BaseAgent
from agents.complexity import ComplexityLevel


class CodeAgent(BaseAgent):
    name = "code"
    RAG_COLLECTIONS = ["simulation_code", "architecture"]

    SYSTEM_PROMPT = """You are a senior Python engineer specializing in scientific computing
and radar signal processing simulation.

Stack: Python 3.11+, NumPy, SciPy, Matplotlib, skyfield.
Target hardware (production): NVIDIA AGX Orin. Development: Mac.

You are part of the STARDAR project. When writing code:
- Use NumPy vectorized operations — avoid Python loops over large arrays
- Add docstrings only for non-obvious functions
- Prefer explicit variable names (e.g. bistatic_range_m not r)
- Write testable, modular functions
- For SAR processing: back-projection is the reference algorithm; mention if FFT-based methods are more appropriate

When reviewing code: flag numerical precision issues, off-by-one errors in range/Doppler bins,
incorrect coordinate system assumptions, and missing normalization steps.
"""

    async def implement(self, task: str, context: str = "") -> str:
        """Always uses at least Sonnet for code generation."""
        from agents.model_router import ModelRouter
        router = ModelRouter()
        # Code tasks: minimum COMPLEX (Sonnet), escalate to CRITICAL if novel algorithm
        level = await router.assess(task)
        if level in (ComplexityLevel.TRIVIAL, ComplexityLevel.STANDARD):
            level = ComplexityLevel.COMPLEX
        response = await self.run(task=task, use_rag=True, force_level=level)
        return response.raw
