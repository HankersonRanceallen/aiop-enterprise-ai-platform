"""
Planner Agent
==============
The first agent in the workflow. Given the user's task, it:
  1. Analyzes what kind of task this is
  2. Breaks it into concrete steps
  3. Sets the strategy for the downstream agents

In V3, this will use more sophisticated task decomposition and
decide whether to invoke additional tools or APIs.
"""
import time
from app.services.agents.state import AgentState
from app.services.llm.base import BaseLLMService

PLANNER_SYSTEM = """You are a planning agent for an enterprise AI platform.
Your job is to analyze a user's task and break it into clear, concrete steps.

Output ONLY a JSON array of step strings. No explanation, no markdown, no preamble.
Example: ["Search documents for X", "Analyze findings", "Generate report"]

Keep steps concise (under 15 words each). Maximum 5 steps."""


async def planner_node(state: AgentState, llm: BaseLLMService) -> dict:
    """
    LangGraph node: Planner Agent
    Reads: state["task"]
    Writes: state["plan"], state["step_log"], state["total_tokens"]
    """
    import json

    start = time.monotonic()

    try:
        response = await llm.generate(
            messages=[{"role": "user", "content": f"Task: {state['task']}"}],
            system_prompt=PLANNER_SYSTEM,
            temperature=0.2,
            max_tokens=512,
        )

        # Parse the plan JSON
        raw = response.content.strip()
        # Strip any accidental markdown
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        plan = json.loads(raw)

    except Exception:
        # Fallback plan if JSON parsing fails
        plan = [
            "Search relevant documents",
            "Analyze retrieved content",
            "Generate comprehensive report",
        ]

    latency = (time.monotonic() - start) * 1000

    log_entry = {
        "agent": "planner",
        "status": "done",
        "message": f"Created a {len(plan)}-step plan",
        "output": plan,
        "latency_ms": round(latency, 1),
        "tokens": response.total_tokens if "response" in dir() else 0,
    }

    return {
        "plan": plan,
        "step_log": [log_entry],
        "total_tokens": state.get("total_tokens", 0) + (response.total_tokens if "response" in dir() else 0),
        "error": None,
    }
