"""
Dynamic model router — assesses task complexity and selects the appropriate model.
Used by every agent. No agent hardcodes a model.
"""

import os
import logging
from typing import AsyncIterator

import anthropic
import ollama

from agents.complexity import ComplexityLevel, ASSESSOR_PROMPT

logger = logging.getLogger(__name__)

# Model identifiers
_OLLAMA_ROUTER   = "llama3.2:3b"
_OLLAMA_STANDARD = "deepseek-r1:14b"
_SONNET          = "claude-sonnet-4-6"
_OPUS            = "claude-opus-4-6"

_MODEL_MAP = {
    ComplexityLevel.TRIVIAL:  ("ollama", _OLLAMA_ROUTER),
    ComplexityLevel.STANDARD: ("ollama", _OLLAMA_STANDARD),
    ComplexityLevel.COMPLEX:  ("anthropic", _SONNET),
    ComplexityLevel.CRITICAL: ("anthropic", _OPUS),
}


class ModelRouter:
    """
    Assesses complexity via llama3.2:3b, then dispatches to the appropriate model.
    All agents use this class — domain logic lives in the agent, not the router.
    """

    def __init__(self):
        self._anthropic = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        task: str,
        system_prompt: str,
        context: str = "",
        force_level: ComplexityLevel | None = None,
    ) -> str:
        """
        Assess task complexity, pick model, return response.

        Args:
            task:         The user-facing task/question
            system_prompt: Agent-specific system prompt
            context:      RAG-retrieved context to inject
            force_level:  Override auto-assessment (useful for roundtable steps)
        """
        level = force_level or await self._assess(task)
        logger.info("Task complexity: %s → %s", level, _MODEL_MAP[level][1])

        full_user = self._build_user_message(task, context)

        provider, model = _MODEL_MAP[level]
        if provider == "ollama":
            return await self._run_ollama(model, system_prompt, full_user)
        else:
            return await self._run_anthropic(model, system_prompt, full_user)

    async def assess(self, task: str) -> ComplexityLevel:
        """Public wrapper — useful for logging/testing."""
        return await self._assess(task)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _assess(self, task: str) -> ComplexityLevel:
        """Use llama3.2:3b to classify task complexity. Fast and cheap."""
        try:
            response = ollama.chat(
                model=_OLLAMA_ROUTER,
                messages=[
                    {"role": "system", "content": ASSESSOR_PROMPT},
                    {"role": "user",   "content": task},
                ],
                options={"temperature": 0.0, "num_predict": 5},
            )
            raw = response["message"]["content"].strip().upper()
            # Guard against verbose responses
            for level in ComplexityLevel:
                if level.value in raw:
                    return level
            logger.warning("Assessor returned unexpected '%s', defaulting to COMPLEX", raw)
            return ComplexityLevel.COMPLEX
        except Exception as e:
            logger.error("Assessor failed (%s), defaulting to COMPLEX", e)
            return ComplexityLevel.COMPLEX

    async def _run_ollama(self, model: str, system: str, user: str) -> str:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            options={"temperature": 0.3},
        )
        return response["message"]["content"]

    async def _run_anthropic(self, model: str, system: str, user: str) -> str:
        # Use prompt caching on the (long, static) system prompt
        response = self._anthropic.messages.create(
            model=model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text

    @staticmethod
    def _build_user_message(task: str, context: str) -> str:
        if context:
            return f"<context>\n{context}\n</context>\n\n{task}"
        return task
