"""
Retriever Agent
================
Uses the plan from the Planner to formulate targeted search queries
and retrieves the most relevant document chunks from pgvector.

In V1, the RAG pipeline used the user's raw question as the query.
In V2, the Retriever Agent is smarter — it uses the plan to construct
multiple targeted queries and merges the results.
"""
import time
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.state import AgentState
from app.services.llm.base import BaseLLMService
from app.services.rag.retriever import retrieve_chunks
from app.core.config import settings

QUERY_SYSTEM = """You are a search query specialist.
Given a task and a plan, generate the SINGLE most effective search query
to retrieve relevant information from a document database.

Output ONLY the search query string. No explanation, no quotes."""


async def retriever_node(state: AgentState, llm: BaseLLMService, db: AsyncSession) -> dict:
    """
    LangGraph node: Retriever Agent
    Reads: state["task"], state["plan"]
    Writes: state["retrieved_chunks"], state["step_log"]
    """
    start = time.monotonic()

    # Build a targeted search query from the task + plan
    plan_text = "\n".join(f"- {step}" for step in state.get("plan", []))
    query_prompt = f"Task: {state['task']}\n\nPlan:\n{plan_text}"

    try:
        query_response = await llm.generate(
            messages=[{"role": "user", "content": query_prompt}],
            system_prompt=QUERY_SYSTEM,
            temperature=0.1,
            max_tokens=100,
        )
        search_query = query_response.content.strip()
    except Exception:
        search_query = state["task"]

    # Embed the query
    embedding_response = await llm.embed(search_query)

    # Retrieve chunks
    chunks = await retrieve_chunks(
        db=db,
        query_embedding=embedding_response.embedding,
        organization_id=state["organization_id"],
        top_k=settings.top_k_retrieval * 2,  # Retrieve more for analysis
        document_ids=state.get("document_ids"),
    )

    latency = (time.monotonic() - start) * 1000

    log_entry = {
        "agent": "retriever",
        "status": "done",
        "message": f"Retrieved {len(chunks)} chunks from {len(set(c['document_id'] for c in chunks))} documents",
        "output": {
            "query_used": search_query,
            "chunks_found": len(chunks),
            "documents_searched": list(set(c["document_title"] for c in chunks)),
        },
        "latency_ms": round(latency, 1),
    }

    return {
        "retrieved_chunks": chunks,
        "step_log": [log_entry],
        "error": None,
    }
