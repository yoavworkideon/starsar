"""
Complexity levels and classification rules for dynamic model routing.
All agents share this ruleset — no per-agent hardcoded tiers.
"""

from enum import Enum


class ComplexityLevel(str, Enum):
    TRIVIAL  = "TRIVIAL"   # llama3.2:3b
    STANDARD = "STANDARD"  # deepseek-r1:14b
    COMPLEX  = "COMPLEX"   # claude-sonnet-4-6
    CRITICAL = "CRITICAL"  # claude-opus-4-6


# Human-readable rules injected into the assessor prompt
COMPLEXITY_RULES = """
TRIVIAL:
  - Simple factual lookup or definition
  - Applying a single known formula (e.g. "what is the range resolution for 250 MHz BW?")
  - Yes/no or binary question
  - Summarizing a short text passage
  - Retrieving a reference value

STANDARD:
  - Multi-step domain calculation (2–4 steps)
  - Analyzing a signal processing scenario with known inputs
  - Comparing two known approaches
  - Interpreting a simulation result
  - Literature retrieval with light synthesis

COMPLEX:
  - Generating or reviewing Python/C++ code
  - Deep technical analysis across multiple domains
  - Mathematical derivation with 5+ steps
  - Debugging a signal processing pipeline
  - Designing a processing chain from requirements

CRITICAL:
  - Novel mathematical derivation (bistatic SAR focusing, ambiguity function analysis)
  - Synthesis across geometry + signal + SNR domains simultaneously
  - Architecture or algorithm decision with long-term consequences
  - Roundtable facilitation and final plan synthesis
  - Research hypothesis generation or feasibility judgment
"""

ASSESSOR_PROMPT = f"""You are a task complexity classifier for a passive bistatic SAR radar simulation system (STARDAR).
Your only job is to read a task and output exactly one word: TRIVIAL, STANDARD, COMPLEX, or CRITICAL.

Classification rules:
{COMPLEXITY_RULES}

Respond with ONLY the complexity level. No explanation. No punctuation.
"""
