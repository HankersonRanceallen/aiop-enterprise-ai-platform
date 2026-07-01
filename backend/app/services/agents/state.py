"""
Agent State
============
The single state object that flows through all nodes in the LangGraph graph.
Each agent reads from it and writes its output back into it.

This is the "memory" of the multi-agent system — every agent can see
what the previous agents produced.
"""
from typing import TypedDict, Annotated
import operator


class AgentState(TypedDict):
    # Input
    task: str                              # The user's original request
    organization_id: int                   # Scopes all retrieval to this org
    document_ids: list[int] | None         # Optional: search only specific docs

    # Planner output
    plan: list[str]                        # Steps the planner decided on

    # Retriever output
    retrieved_chunks: list[dict]           # Relevant document chunks

    # Analysis output
    analysis: str                          # Analysis agent's findings

    # Report output
    final_report: str                      # Final formatted report

    # Step trace — uses operator.add so each agent APPENDS its log entry
    step_log: Annotated[list[dict], operator.add]

    # Token tracking across all agents
    total_tokens: int

    # Error handling
    error: str | None
