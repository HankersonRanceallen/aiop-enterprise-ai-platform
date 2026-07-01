"""
LangGraph Agent Graph
======================
Wires all agents into a directed graph using LangGraph's StateGraph.

Flow:
  START → planner → retriever → analysis → report → END

V3 addition: the completed run is logged to MLflow for experiment tracking.
"""
import json
import time
from typing import AsyncIterator

from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.state import AgentState
from app.services.agents.planner import planner_node
from app.services.agents.retriever_agent import retriever_node
from app.services.agents.analysis_agent import analysis_node
from app.services.agents.report_agent import report_node
from app.services.llm.factory import get_llm_service
from app.services.mlflow_service import log_agent_run


NODE_DISPLAY = {
    "planner":   {"label": "Planner Agent",   "emoji": "🧠"},
    "retriever": {"label": "Retriever Agent",  "emoji": "🔍"},
    "analysis":  {"label": "Analysis Agent",   "emoji": "📊"},
    "report":    {"label": "Report Agent",     "emoji": "📝"},
}


def build_agent_graph(llm, db: AsyncSession):
    async def _planner(state: AgentState) -> dict:
        return await planner_node(state, llm)

    async def _retriever(state: AgentState) -> dict:
        return await retriever_node(state, llm, db)

    async def _analysis(state: AgentState) -> dict:
        return await analysis_node(state, llm)

    async def _report(state: AgentState) -> dict:
        return await report_node(state, llm)

    workflow = StateGraph(AgentState)
    workflow.add_node("planner",   _planner)
    workflow.add_node("retriever", _retriever)
    workflow.add_node("analysis",  _analysis)
    workflow.add_node("report",    _report)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner",   "retriever")
    workflow.add_edge("retriever", "analysis")
    workflow.add_edge("analysis",  "report")
    workflow.add_edge("report",    END)

    return workflow.compile()


async def stream_agent_run(
    task: str,
    organization_id: int,
    db: AsyncSession,
    document_ids: list[int] | None = None,
) -> AsyncIterator[str]:
    """Run the multi-agent graph, yield SSE-formatted events."""
    llm = get_llm_service()
    graph = build_agent_graph(llm, db)

    initial_state: AgentState = {
        "task": task,
        "organization_id": organization_id,
        "document_ids": document_ids,
        "plan": [],
        "retrieved_chunks": [],
        "analysis": "",
        "final_report": "",
        "step_log": [],
        "total_tokens": 0,
        "error": None,
    }

    overall_start = time.monotonic()
    yield _sse({"type": "started", "task": task})

    try:
        async for chunk in graph.astream(initial_state):
            for node_name, state_update in chunk.items():
                if node_name == "__end__":
                    continue
                meta = NODE_DISPLAY.get(node_name, {"label": node_name, "emoji": "🤖"})
                step_logs = state_update.get("step_log", [])
                latest_log = step_logs[-1] if step_logs else {}

                yield _sse({
                    "type":       "step_done",
                    "agent":      node_name,
                    "label":      meta["label"],
                    "emoji":      meta["emoji"],
                    "status":     "done",
                    "message":    latest_log.get("message", f"{meta['label']} completed"),
                    "output":     latest_log.get("output"),
                    "latency_ms": latest_log.get("latency_ms", 0),
                })

        # Get final complete state
        final_state = await graph.ainvoke(initial_state)
        total_latency = (time.monotonic() - overall_start) * 1000

        # V3: Log to MLflow
        log_agent_run(
            task=task,
            llm_provider=llm.provider_name,
            llm_model=llm.model_name,
            total_tokens=final_state.get("total_tokens", 0),
            latency_ms=total_latency,
            step_log=final_state.get("step_log", []),
            organization_id=organization_id,
            succeeded=True,
        )

        yield _sse({
            "type":             "complete",
            "report":           final_state.get("final_report", ""),
            "step_log":         final_state.get("step_log", []),
            "total_tokens":     final_state.get("total_tokens", 0),
            "total_latency_ms": round(total_latency, 1),
        })

    except Exception as e:
        log_agent_run(
            task=task,
            llm_provider=llm.provider_name,
            llm_model=llm.model_name,
            total_tokens=0,
            latency_ms=(time.monotonic() - overall_start) * 1000,
            step_log=[],
            organization_id=organization_id,
            succeeded=False,
        )
        yield _sse({"type": "error", "message": str(e)})


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
