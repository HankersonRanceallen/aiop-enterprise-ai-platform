"""
Analysis Agent
===============
Synthesizes the retrieved document chunks into structured findings.
It reads everything the Retriever found and produces a coherent
analysis that the Report Agent can turn into a polished output.

This is where the "intelligence" of the system lives — it connects
information across multiple documents and identifies patterns.
"""
import time

from app.services.agents.state import AgentState
from app.services.llm.base import BaseLLMService

ANALYSIS_SYSTEM = """You are a senior analyst for an enterprise knowledge platform.
You have been given a task, a plan, and relevant document excerpts.

Your job:
1. Analyze the retrieved content thoroughly
2. Identify key themes, patterns, and insights
3. Note any gaps or inconsistencies in the information
4. Summarize findings in a structured way

Format your analysis with clear sections using markdown headers.
Be specific — cite document names when referencing information.
Focus on what's most relevant to the original task."""


def _format_chunks_for_analysis(chunks: list[dict]) -> str:
    """Format retrieved chunks into a readable block for the LLM."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Source {i}] \"{chunk['document_title']}\" "
            f"(relevance: {chunk['score']:.0%})\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


async def analysis_node(state: AgentState, llm: BaseLLMService) -> dict:
    """
    LangGraph node: Analysis Agent
    Reads: state["task"], state["plan"], state["retrieved_chunks"]
    Writes: state["analysis"], state["step_log"]
    """
    start = time.monotonic()

    chunks = state.get("retrieved_chunks", [])
    if not chunks:
        return {
            "analysis": "No relevant documents were found to analyze.",
            "step_log": [{
                "agent": "analysis",
                "status": "done",
                "message": "No chunks to analyze — skipped",
                "latency_ms": 0,
            }],
        }

    context = _format_chunks_for_analysis(chunks)
    plan_text = "\n".join(f"- {step}" for step in state.get("plan", []))

    user_prompt = f"""Task: {state['task']}

Plan:
{plan_text}

Retrieved document content:
{context}

Please analyze this content in relation to the task."""

    response = await llm.generate(
        messages=[{"role": "user", "content": user_prompt}],
        system_prompt=ANALYSIS_SYSTEM,
        temperature=0.2,
        max_tokens=2048,
    )

    latency = (time.monotonic() - start) * 1000

    log_entry = {
        "agent": "analysis",
        "status": "done",
        "message": f"Analyzed {len(chunks)} chunks across {len(set(c['document_id'] for c in chunks))} documents",
        "output": response.content[:500] + "…" if len(response.content) > 500 else response.content,
        "latency_ms": round(latency, 1),
        "tokens": response.total_tokens,
    }

    return {
        "analysis": response.content,
        "step_log": [log_entry],
        "total_tokens": state.get("total_tokens", 0) + response.total_tokens,
        "error": None,
    }
