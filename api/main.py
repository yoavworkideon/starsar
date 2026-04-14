"""
STARDAR API — FastAPI entry point.

Endpoints:
  POST /roundtable       Run full multi-agent roundtable, returns review card
  POST /roundtable/approve  Approve plan → trigger implementation
  POST /agent/{name}     Direct single-agent query
  POST /rag/ingest       Trigger document ingestion
  GET  /health           Health check
"""

import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agents import GeometryAgent, SignalAgent, SNRAgent, LiteratureAgent, CodeAgent
from orchestrator.roundtable import Roundtable

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="STARDAR Agent API", version="0.1.0")

_roundtable_results: dict[str, object] = {}  # session_id → RoundtableResult

_AGENT_MAP = {
    "geometry":   GeometryAgent,
    "signal":     SignalAgent,
    "snr":        SNRAgent,
    "literature": LiteratureAgent,
    "code":       CodeAgent,
}


# ── Request / Response models ──────────────────────────────────────────

class TaskRequest(BaseModel):
    task: str
    session_id: str | None = None

class AgentRequest(BaseModel):
    task: str
    use_rag: bool = True

class ApprovalRequest(BaseModel):
    session_id: str
    decision: str   # "yes" | "modify" | "abort"
    modifications: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "stardar-agents"}


@app.post("/roundtable")
async def roundtable(req: TaskRequest):
    """
    Run full roundtable pipeline.
    Returns the review card — does NOT implement until /roundtable/approve is called.
    """
    rt = Roundtable()
    result = await rt.run(req.task)
    review_card = rt.format_review_card(result)

    session_id = req.session_id or f"rt_{id(result)}"
    _roundtable_results[session_id] = result

    return {
        "session_id":    session_id,
        "review_card":   review_card,
        "ready":         result.synthesis.ready_to_implement,
        "open_questions": [],
    }


@app.post("/roundtable/approve")
async def approve(req: ApprovalRequest):
    """
    Approve a roundtable plan → execute implementation via CodeAgent.
    """
    result = _roundtable_results.get(req.session_id)
    if not result:
        raise HTTPException(404, "Session not found")

    if req.decision == "abort":
        return {"status": "aborted"}

    if req.decision == "modify" and req.modifications:
        # Re-run roundtable with modifications appended
        modified_task = f"{result.task}\n\nUser modifications: {req.modifications}"
        rt = Roundtable()
        new_result = await rt.run(modified_task)
        _roundtable_results[req.session_id] = new_result
        return {
            "status":      "modified",
            "review_card": rt.format_review_card(new_result),
        }

    # Approved → implement
    code_agent = CodeAgent()
    implementation = await code_agent.implement(
        task=result.synthesis.plan,
        context=result.task,
    )
    return {
        "status":         "implemented",
        "implementation": implementation,
    }


@app.post("/agent/{name}")
async def run_agent(name: str, req: AgentRequest):
    """Direct single-agent query — bypasses roundtable."""
    cls = _AGENT_MAP.get(name)
    if not cls:
        raise HTTPException(404, f"Agent '{name}' not found. Available: {list(_AGENT_MAP)}")

    agent    = cls()
    response = await agent.run(req.task, use_rag=req.use_rag)
    return {
        "agent":      response.agent,
        "complexity": response.complexity,
        "model":      response.model_used,
        "response":   response.raw,
    }
