"""
Dynamic model router — assesses task complexity and selects the appropriate model.
Used by every agent. No agent hardcodes a model.
"""

import asyncio
import os
import logging
import signal
from typing import AsyncIterator

import anthropic
from anthropic import AsyncAnthropic
import httpx
import ollama

from agents.complexity import ComplexityLevel, ASSESSOR_PROMPT

logger = logging.getLogger(__name__)

# Fix 1: SIGURG (exit 144) — macOS terminates the process by default on TCP urgent data.
# Install SIG_IGN early (before any network activity) so the kernel can't kill us.
signal.signal(signal.SIGURG, signal.SIG_IGN)

# Fix 4: Semaphore — cap concurrent Anthropic API calls to avoid connection pool races
# under Python 3.14's asyncio. Module-level; lazily bound to the event loop on first await.
_anthropic_semaphore = asyncio.Semaphore(5)

# Shared async client — one connection pool for the entire process
_anthropic_client: AsyncAnthropic | None = None


def _get_anthropic_client() -> AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        # Fix 3: explicit httpx limits + timeouts to prevent cold-start TLS races.
        # max_connections=10 matches our Semaphore(5) with headroom for retries.
        # connect=10.0 gives each TLS handshake a firm deadline (was unbounded).
        http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=10,
                keepalive_expiry=30.0,
            ),
            timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0),
        )
        _anthropic_client = AsyncAnthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            max_retries=3,
            # Pass timeout directly to the SDK — it overrides the httpx client timeout
            # per-request. Without this, the SDK default (600s × 4 attempts = 40 min)
            # causes silent hangs when httpcore reuses a stale connection.
            # read=120s is generous for Opus synthesis; retry opens a fresh connection.
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
            http_client=http_client,
        )
    return _anthropic_client

# Model identifiers
_OLLAMA_ROUTER   = "llama3.2:3b"
_OLLAMA_STANDARD = "deepseek-r1:14b"
_SONNET          = "claude-sonnet-4-6"
_OPUS            = "claude-opus-4-6"

class ModelRouter:
    """
    Assesses complexity via llama3.2:3b, then dispatches to the appropriate model.
    All agents use this class — domain logic lives in the agent, not the router.
    """

    _MODEL_MAP = {
        ComplexityLevel.TRIVIAL:  ("ollama", _OLLAMA_ROUTER),
        ComplexityLevel.STANDARD: ("ollama", _OLLAMA_STANDARD),
        ComplexityLevel.COMPLEX:  ("anthropic", _SONNET),
        ComplexityLevel.CRITICAL: ("anthropic", _OPUS),
    }

    def __init__(self):
        self._anthropic = _get_anthropic_client()

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
        logger.info("Task complexity: %s → %s", level, self._MODEL_MAP[level][1])

        full_user = self._build_user_message(task, context)

        provider, model = self._MODEL_MAP[level]
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
            response = await asyncio.to_thread(
                ollama.chat,
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
        # deepseek-r1 is a thinking model — cap tokens to avoid runaway generation.
        # llama3.2:3b gets a generous limit; it's fast enough not to matter.
        num_predict = 512 if model == _OLLAMA_STANDARD else 256

        def _call():
            return ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                options={"temperature": 0.3, "num_predict": num_predict},
            )

        # Run the blocking ollama call off the event loop thread
        response = await asyncio.to_thread(_call)
        return response["message"]["content"]

    async def _run_anthropic(self, model: str, system: str, user: str) -> str:
        # AsyncAnthropic — non-blocking, safe for asyncio.gather() parallelism.
        # Prompt caching on the static system prompt reduces cost on repeated roundtable calls.
        # Semaphore prevents pool saturation races during parallel cold-start connections.
        async with _anthropic_semaphore:
            response = await self._anthropic.messages.create(
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
